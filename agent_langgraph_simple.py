"""
Agente de IA para Atendimento de Supermercado usando LangGraph
Versão simplificada e estável com arquitetura de grafos
"""

from typing import Dict, Any, TypedDict, Sequence, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from pathlib import Path
import json
import os

from config.settings import settings
from config.logger import setup_logger
from tools.http_tools import estoque, pedidos, alterar, ean_lookup, estoque_preco
from tools.redis_tools import set_pedido_ativo, confirme_pedido_ativo
from tools.time_tool import get_current_time, get_time_diff_description, format_timestamp
from memory.limited_postgres_memory import LimitedPostgresChatMessageHistory

logger = setup_logger(__name__)

# ============================================
# Definição das Ferramentas (Tools)
# ============================================

@tool
def estoque_tool(url: str) -> str:
    """
    Consultar estoque e preço atual dos produtos no sistema do supermercado.
    
    A URL completa para a consulta deve ser fornecida, por exemplo:
    'https://wildhub-wildhub-sistema-supermercado.5mos1l.easypanel.host/api/produtos/consulta?nome=arroz'
    
    Use esta ferramenta quando o cliente perguntar sobre disponibilidade ou preço de produtos.
    """
    return estoque(url)


@tool
def pedidos_tool(json_body: str) -> str:
    """
    Enviar o pedido finalizado para o painel dos funcionários (dashboard).
    
    O corpo da requisição deve ser um JSON (em formato string) com os detalhes do pedido.
    Exemplo: '{"cliente": "João Silva", "telefone": "5511999998888", "itens": [{"produto": "Arroz Integral 1kg", "quantidade": 2, "preco": 8.50}], "total": 17.00}'
    
    Use esta ferramenta SOMENTE quando o cliente confirmar que deseja finalizar o pedido.
    """
    return pedidos(json_body)


@tool
def alterar_tool(telefone: str, json_body: str) -> str:
    """
    Atualizar o pedido no painel dos funcionários (dashboard).
    
    O telefone do cliente deve ser fornecido para identificar o pedido.
    O corpo da requisição deve ser um JSON (em formato string) com os dados a serem atualizados.
    
    Exemplo: alterar_tool("5511987654321", '{"status": "cancelado", "motivo": "Cliente desistiu"}')
    
    Use esta ferramenta quando o cliente quiser modificar ou cancelar um pedido existente.
    """
    return alterar(telefone, json_body)


@tool
def set_tool(telefone: str, valor: str = "ativo", ttl: int = 600) -> str:
    """
    Define uma chave no Redis para indicar que um pedido está ativo.
    
    A chave é formada por: {telefone}pedido
    O TTL padrão é de 600 segundos (10 minutos).
    
    Use esta ferramenta APÓS finalizar um pedido com sucesso para marcar que o cliente tem um pedido ativo.
    """
    return set_pedido_ativo(telefone, valor, ttl)


@tool
def confirme_tool(telefone: str) -> str:
    """
    Verifica se um pedido está ativo no Redis.
    
    A chave é formada por: {telefone}pedido
    Retorna o valor da chave ou uma mensagem de que não foi encontrado.
    
    Use esta ferramenta para verificar se o cliente já tem um pedido em andamento antes de criar um novo.
    """
    return confirme_pedido_ativo(telefone)


@tool
def time_tool() -> str:
    """
    Retorna a data e hora atual no fuso horário de São Paulo (America/Sao_Paulo).
    
    Use esta ferramenta quando o cliente perguntar sobre horário de funcionamento,
    horário de entrega, ou qualquer informação relacionada ao tempo.
    """
    return get_current_time()


@tool
def ean_tool(query: str) -> str:
    """
    Buscar EAN/infos do produto via Supabase Functions (smart-responder).
    Envie o argumento conforme decidido pelo LLM e pelo prompt.
    """
    logger.info(f"Ferramenta ean chamada com query: {str(query)[:100]}")
    q = (query or "").strip()
    if q.startswith("{") and q.endswith("}"):
        q = ("" or q)  # Usar query direta
    return ean_lookup(q)

@tool("ean")
def ean_tool_alias(query: str) -> str:
    """
    Alias de ferramenta: `ean`
    Envie o argumento conforme decidido pelo LLM e pelo prompt.
    """
    logger.info(f"Ferramenta ean(alias) chamada com query: {str(query)[:100]}")
    q = (query or "").strip()
    if q.startswith("{") and q.endswith("}"):
        q = ("" or q)  # Usar query direta
    return ean_lookup(q)


@tool
def estoque_preco_tool(ean: str) -> str:
    """
    Consultar preço e disponibilidade pelo EAN.
    Informe apenas os dígitos do código EAN.

    Observações:
    - Retorna somente itens com disponibilidade/estoque positivo.
    - Remove campos de quantidade de estoque da saída.
    - Normaliza o preço no campo "preco" quando possível.
    Use esta ferramenta para montar opções (nome + variação + preço)
    e perguntar tamanho/gramagem quando o pedido for genérico.
    """
    return estoque_preco(ean)

@tool("estoque")
def estoque_preco_alias(ean: str) -> str:
    """
    Alias de ferramenta: `estoque`
    Consulta preço e disponibilidade pelo EAN (apenas dígitos).
    Filtra apenas itens com estoque e normaliza o preço em `preco`.
    """
    return estoque_preco(ean)


@tool
def historico_tool(query: str = "") -> str:
    """
    Consultar histórico de conversas anteriores com informações temporais.
    
    Use esta ferramenta quando o cliente perguntar sobre:
    - "Quando conversamos pela última vez?"
    - "Qual foi nossa última conversa?"
    - "O que discutimos ontem/antes?"
    - "Quando foi que falamos sobre [assunto]?"
    
    Args:
        query: Pergunta específica sobre o histórico (opcional)
    """
    try:
        # Para implementação futura com memória temporal
        return "🕐 Funcionalidade de histórico com marcações temporais está ativa. As mensagens agora incluem informações de horário."
    except Exception as e:
        return f"Erro ao consultar histórico: {e}"


@tool
def audio_info_tool() -> str:
    """
    Informa sobre o suporte a mensagens de áudio e voz.
    
    Use quando o cliente perguntar sobre:
    - "Você aceita áudio?"
    - "Posso mandar mensagem de voz?"
    - "Como funciona o áudio?"
    """
    return """🎤 Suporte a Áudio
✅ Eu aceito mensagens de áudio e voz!
📱 Como funciona:
• Grave um áudio no WhatsApp normalmente
• Envie para mim que eu vou transcrever e responder
• Funciona com mensagens de voz (PTT) e arquivos de áudio
• Suporta: MP3, OGG, WAV, M4A, OPUS, etc."""


# Lista de ferramentas principais
TOOLS = [
    estoque_tool,
    pedidos_tool,
    alterar_tool,
    set_tool,
    confirme_tool,
    time_tool,
    ean_tool,
    ean_tool_alias,
    estoque_preco_tool,
    estoque_preco_alias,
    historico_tool,
    audio_info_tool,
]

# Ferramentas ativas (as principais que o agente usará)
ACTIVE_TOOLS = [
    ean_tool_alias,
    estoque_preco_alias,
    time_tool,
    historico_tool,
    audio_info_tool,
]


# ============================================
# Funções do Grafo
# ============================================

def load_system_prompt() -> str:
    """Carrega o prompt do sistema humanizado para o Supermercado Queiroz"""
    base_dir = Path(__file__).resolve().parent
    
    # Se modo econômico estiver ativado, usar prompt otimizado
    if getattr(settings, "economy_mode", False):
        prompt_path = str((base_dir / "prompts" / "agent_system_optimized.md"))
        logger.info("Modo econômico ativado - usando prompt otimizado")
    else:
        prompt_path = str((base_dir / "prompts" / "agent_queiroz_humanizado.md"))
    
    try:
        text = Path(prompt_path).read_text(encoding="utf-8")
        logger.info(f"Carregado prompt do sistema de: {prompt_path}")
        return text
    except Exception as e:
        logger.error(f"Falha ao carregar prompt específico: {e}")
        # Fallback para o prompt padrão
        logger.info("Tentando carregar prompt padrão como fallback...")
        fallback_path = str((base_dir / "prompts" / "agent_system.md"))
        try:
            text = Path(fallback_path).read_text(encoding="utf-8")
            text = text.replace("{base_url}", settings.supermercado_base_url)
            text = text.replace("{ean_base}", settings.estoque_ean_base_url)
            logger.info(f"Carregado prompt de fallback de: {fallback_path}")
            return text
        except Exception as fallback_error:
            logger.error(f"Falha ao carregar prompt de fallback também: {fallback_error}")
            raise


def _build_llm():
    provider = getattr(settings, "llm_provider", "openai").lower()
    model = getattr(settings, "llm_model", "gpt-4o-mini")
    temp = float(getattr(settings, "llm_temperature", 0.0))
    max_tokens = getattr(settings, "max_response_tokens", 800)
    profile = getattr(settings, "llm_profile", None)
    if profile:
        p = str(profile).lower().strip()
        if p == "quality_openai":
            provider, model, temp = "openai", "gpt-4o", 0.2
        elif p == "fast_openai":
            provider, model, temp = "openai", "gpt-4o-mini", 0.2
        elif p == "economy_openai":
            provider, model, temp = "openai", "gpt-4o-mini", 0.6
        elif p == "quality_kimi":
            provider, model, temp = "moonshot", "kimi-k2-thinking-turbo", 1.0
        elif p == "fast_kimi":
            provider, model, temp = "moonshot", "kimi-k2-turbo-preview", 0.6
        elif p == "economy_kimi":
            provider, model, temp = "moonshot", "kimi-k2-0711-preview", 0.6
    if provider == "moonshot":
        import os as _os
        k = getattr(settings, "moonshot_api_key", None)
        u = getattr(settings, "moonshot_api_url", None)
        if k:
            _os.environ["ANTHROPIC_API_KEY"] = str(k).strip().strip("`")
        if u:
            _u = str(u).strip().strip("`")
            if ("moonshot.ai" in _u or "moonshot.cn" in _u) and "/anthropic" not in _u:
                _u = _u.rstrip("/") + "/anthropic"
            _os.environ["ANTHROPIC_BASE_URL"] = _u
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, temperature=temp, max_tokens=max_tokens)
    
    # OpenAI: usar max_completion_tokens (novo padrão)
    return ChatOpenAI(model=model, openai_api_key=settings.openai_api_key, temperature=temp, max_completion_tokens=max_tokens)

def create_agent_with_history():
    """Cria o agente LangGraph com histórico usando create_react_agent"""
    logger.info("Criando agente LangGraph com create_react_agent...")
    
    # Carregar prompt do sistema
    system_prompt = load_system_prompt()
    
    llm = _build_llm()
    
    # Criar memória com checkpoint
    memory = MemorySaver()
    
    # Criar agente REACT usando a função prebuilt
    agent = create_react_agent(
        llm,
        ACTIVE_TOOLS,
        prompt=system_prompt,
        checkpointer=memory
    )
    
    logger.info("✅ Agente LangGraph REACT criado com sucesso")
    return agent


# ============================================
# Função Principal
# ============================================

_agent_graph = None

def get_agent_graph():
    """Retorna o grafo do agente (singleton)"""
    global _agent_graph
    
    if _agent_graph is None:
        _agent_graph = create_agent_with_history()
        
    return _agent_graph


def run_agent_langgraph(telefone: str, mensagem: str) -> Dict[str, Any]:
    """
    Executa o agente LangGraph com uma mensagem e ID de sessão (telefone).
    
    Args:
        telefone: Telefone do cliente (usado como session_id)
        mensagem: Mensagem do cliente
    
    Returns:
        Dict com 'output' (resposta do agente) e 'error' (se houver)
    """
    logger.info(f"Executando agente LangGraph REACT para telefone: {telefone}")
    logger.debug(f"Mensagem recebida: {mensagem}")
    
    # Removido verificação de expiração de pedido - sistema sem timeout
    
    try:
        agent = get_agent_graph()
        
        # Preparar estado inicial
        initial_state = {
            "messages": [HumanMessage(content=mensagem)],
        }
        
        # Configuração com session_id para checkpoint
        config = {"configurable": {"thread_id": telefone}}
        
        # Executar grafo
        result = agent.invoke(initial_state, config)
        
        # Extrair última mensagem (resposta do agente)
        last_message = result["messages"][-1]
        if isinstance(last_message, AIMessage):
            output = last_message.content
        else:
            output = str(last_message.content)
        
        logger.info("✅ Agente LangGraph REACT executado com sucesso")
        logger.debug(f"Resposta: {output}")
        
        return {"output": output, "error": None}
        
    except Exception as e:
        logger.error(f"Falha ao executar agente LangGraph REACT: {e}", exc_info=True)
        error_msg = f"Erro ao executar o agente: {e}"
        return {
            "output": "Desculpe, não consegui processar sua mensagem agora.",
            "error": error_msg,
        }


def get_session_history(session_id: str) -> LimitedPostgresChatMessageHistory:
    """
    Carrega o histórico de mensagens do Postgres com limite configurado.
    O session_id é o telefone do cliente.
    Mantém todas as mensagens no BD, mas envia apenas as recentes ao agente.
    """
    return LimitedPostgresChatMessageHistory(
        connection_string=settings.postgres_connection_string,
        session_id=session_id,
        table_name=settings.postgres_table_name,
        max_messages=settings.postgres_message_limit  # Limite configurável via ENV
    )


# Manter compatibilidade com o código existente
run_agent = run_agent_langgraph
