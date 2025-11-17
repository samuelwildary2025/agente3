"""
Agente de IA para Atendimento de Supermercado usando LangGraph
Versão moderna e estável com arquitetura de grafos
"""

from typing import Dict, Any, TypedDict, Sequence, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from pathlib import Path
import json
import os

from config.settings import settings
from config.logger import setup_logger
from tools.http_tools import estoque, pedidos, alterar, ean_lookup, estoque_preco
from tools.redis_tools import set_pedido_ativo, confirme_pedido_ativo
from tools.time_tool import get_current_time
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
def audio_info_tool() -> str:
    """
    Informa sobre o suporte a mensagens de áudio e voz.
    
    Use esta ferramenta quando o cliente perguntar sobre:
    - Como enviar áudio
    - Se o assistente entende áudio
    - Problemas com mensagens de voz
    """
    return """🎤 Suporte a Áudio

✅ Eu aceito mensagens de áudio e voz!

📱 Como funciona:
• Grave um áudio no WhatsApp normalmente
• Envie para mim que eu vou transcrever e responder
• Funciona com mensagens de voz (PTT) e arquivos de áudio
• Suporta: MP3, OGG, WAV, M4A, OPUS, etc.

⚡ O que acontece:
1. Você envia o áudio
2. Eu transcrevo para texto automaticamente
3. Processo sua mensagem normalmente
4. Respondo por texto

💡 Dicas:
• Fale claramente para melhor transcrição
• Evite ambientes muito barulhentos
• Áudios curtos (até 1 minuto) funcionam melhor

Está pronto para começar? É só gravar e enviar! 🎙️"""


@tool
def historico_tool(telefone: str, limite: int = 5) -> str:
    """
    Consulta o histórico de mensagens de um cliente com informações de tempo.
    
    Args:
        telefone: Telefone do cliente (session_id)
        limite: Número de mensagens recentes a retornar (padrão: 5)
    
    Returns:
        String formatada com histórico temporal das mensagens
    """
    try:
        from memory.limited_postgres_memory import LimitedPostgresChatMessageHistory
        
        # Criar instância do histórico
        history = LimitedPostgresChatMessageHistory(
            connection_string=settings.postgres_connection_string,
            session_id=telefone,
            table_name=settings.postgres_table_name,
            max_messages=limite
        )
        
        # Obter mensagens com informações de tempo
        messages_with_time = history.get_messages_with_timestamp_info()
        
        if not messages_with_time:
            return f"📋 Nenhuma mensagem encontrada para o telefone {telefone}"
        
        # Pegar as mensagens mais recentes
        recent_messages = messages_with_time[-limite:]
        
        # Formatar histórico
        historico_str = f"📋 Histórico de mensagens para {telefone} (últimas {len(recent_messages)} mensagens):\n\n"
        
        for i, msg_info in enumerate(recent_messages, 1):
            message_data = msg_info['message']
            time_ago = msg_info['time_ago']
            formatted_time = msg_info['formatted_time']
            
            # Determinar tipo de mensagem
            msg_type = message_data.get('type', 'desconhecido')
            content = message_data.get('content', 'conteúdo indisponível')
            
            # Formatar tipo para exibição
            if msg_type == 'human':
                tipo_str = "👤 Cliente"
            elif msg_type == 'ai':
                tipo_str = "🤖 Assistente"
            elif msg_type == 'system':
                tipo_str = "⚙️ Sistema"
            else:
                tipo_str = "❓ Desconhecido"
            
            # Adicionar ao histórico
            historico_str += f"{i}. {tipo_str} - {time_ago} ({formatted_time}):\n"
            historico_str += f"   {content[:100]}{'...' if len(content) > 100 else ''}\n\n"
        
        return historico_str
        
    except Exception as e:
        logger.error(f"Erro ao consultar histórico: {e}")
        return f"❌ Erro ao consultar histórico: {str(e)}"


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


# Lista de ferramentas principais
TOOLS = [
    estoque_tool,
    pedidos_tool,
    alterar_tool,
    set_tool,
    confirme_tool,
    time_tool,
    historico_tool,
    ean_tool,
    ean_tool_alias,
    estoque_preco_tool,
    estoque_preco_alias,
]

# Ferramentas ativas (as principais que o agente usará)
ACTIVE_TOOLS = [
    ean_tool_alias,
    estoque_preco_alias,
    time_tool,
    historico_tool,
]


# ============================================
# Definição do Estado do Grafo
# ============================================

class AgentState(TypedDict):
    """Estado do grafo do agente"""
    messages: List[BaseMessage]
    session_id: str
    telefone: str


# ============================================
# Funções do Grafo
# ============================================

def load_system_prompt() -> str:
    """Carrega o prompt do sistema"""
    base_dir = Path(__file__).resolve().parent
    prompt_path = str((base_dir / "prompts" / "agent_system.md"))
    
    try:
        text = Path(prompt_path).read_text(encoding="utf-8")
        # Substituir variáveis
        text = text.replace("{base_url}", settings.supermercado_base_url)
        text = text.replace("{ean_base}", settings.estoque_ean_base_url)
        logger.info(f"Carregado prompt do sistema de: {prompt_path}")
        return text
    except Exception as e:
        logger.error(f"Falha ao carregar prompt: {e}")
        raise




def _build_llm():
    provider = getattr(settings, "llm_provider", "openai").lower()
    model = getattr(settings, "llm_model", "gpt-4o-mini")
    temp = float(getattr(settings, "llm_temperature", 0.0))
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
        from langchain_anthropic import ChatAnthropic
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.moonshot_api_key, base_url=settings.moonshot_api_url)
            return ChatAnthropic(model=model, temperature=temp, client=client)
        except Exception:
            return ChatAnthropic(model=model, temperature=temp, api_key=settings.moonshot_api_key)
    return ChatOpenAI(model=model, openai_api_key=settings.openai_api_key, temperature=temp)



def create_agent_with_history():
    """Cria o agente LangGraph com histórico"""
    logger.info("Criando agente LangGraph...")
    
    # Carregar prompt do sistema
    system_prompt = load_system_prompt()
    

    
    # Criar grafo
    workflow = StateGraph(AgentState)
    
    # Definir nós
    def agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Nó do agente que processa mensagens e chama ferramentas"""
        
        # Obter histórico do Postgres
        session_id = state["session_id"]
        history = LimitedPostgresChatMessageHistory(
            connection_string=settings.postgres_connection_string,
            session_id=session_id,
            table_name=settings.postgres_table_name,
            max_messages=settings.postgres_message_limit
        )
        
        # Construir mensagens com histórico
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(history.messages)  # Mensagens recentes do histórico
        messages.append(HumanMessage(content=state["messages"][-1].content))
        
        # Chamar LLM com ferramentas
        try:
            llm_with_tools = llm.bind_tools(ACTIVE_TOOLS)
            response = llm_with_tools.invoke(messages)
            
            # Adicionar resposta ao histórico
            history.add_message(response)
            
            return {"messages": [response]}
            
        except Exception as e:
            logger.error(f"Erro ao processar com LLM: {e}")
            error_msg = AIMessage(content=f"Desculpe, não consegui processar sua mensagem. Erro: {str(e)}")
            history.add_message(error_msg)
            return {"messages": [error_msg]}
    
    def tools_node(state: AgentState) -> Dict[str, Any]:
        """Nó que executa ferramentas"""
        tool_node = ToolNode(ACTIVE_TOOLS)
        result = tool_node.invoke(state)
        
        # Obter histórico do Postgres para salvar respostas das ferramentas
        session_id = state["session_id"]
        history = LimitedPostgresChatMessageHistory(
            connection_string=settings.postgres_connection_string,
            session_id=session_id,
            table_name=settings.postgres_table_name,
            max_messages=settings.postgres_message_limit
        )
        
        # Salvar mensagens das ferramentas no histórico
        for msg in result.get("messages", []):
            history.add_message(msg)
            
        return result
    
    # Adicionar nós ao grafo
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    
    # Definir arestas
    workflow.add_edge("tools", "agent")
    
    # Definir condição para usar ferramentas
    def should_continue(state: AgentState) -> str:
        """Decide se deve continuar ou terminar"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Se a última mensagem for uma AIMessage com tool_calls, continua
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        else:
            return "end"
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # Definir ponto de entrada
    workflow.set_entry_point("agent")
    
    # Compilar grafo
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    
    logger.info("✅ Agente LangGraph criado com sucesso")
    return graph


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
    logger.info(f"Executando agente LangGraph para telefone: {telefone}")
    logger.debug(f"Mensagem recebida: {mensagem}")
    
    try:
        graph = get_agent_graph()
        
        # Preparar estado inicial
        initial_state = {
            "messages": [HumanMessage(content=mensagem)],
            "session_id": telefone,
            "telefone": telefone
        }
        
        # Configuração com session_id para checkpoint
        config = {"configurable": {"thread_id": telefone}}
        
        # Executar grafo
        result = graph.invoke(initial_state, config)
        
        # Extrair última mensagem (resposta do agente)
        last_message = result["messages"][-1]
        if isinstance(last_message, AIMessage):
            output = last_message.content
        else:
            output = str(last_message.content)
        
        logger.info("✅ Agente LangGraph executado com sucesso")
        logger.debug(f"Resposta: {output}")
        
        return {"output": output, "error": None}
        
    except Exception as e:
        logger.error(f"Falha ao executar agente LangGraph: {e}", exc_info=True)
        error_msg = f"Erro ao executar o agente: {e}"
        return {
            "output": "Desculpe, não consegui processar sua mensagem agora.",
            "error": error_msg,
        }


# Manter compatibilidade com o código existente
run_agent = run_agent_langgraph
