# 🕐 Sistema de Consciência Temporal do Agente

## Visão Geral

O seu agente agora possui capacidade de entender e usar informações de tempo das mensagens salvas na memória. Isso permite que ele responda perguntas como:

- "Quando conversamos da última vez?"
- "Que horas foram quando eu pedi o arroz?"
- "Quanto tempo faz que estou conversando com você?"

## 🛠️ Componentes Implementados

### 1. Funções de Formatação de Tempo (`tools/time_tool.py`)

```python
def format_timestamp(timestamp: datetime.datetime, timezone: str = "America/Sao_Paulo") -> str:
    """Formata timestamp para exibição legível em português"""

def get_time_diff_description(timestamp1: datetime.datetime, timestamp2: datetime.datetime) -> str:
    """Calcula diferença entre timestamps (ex: 'há 2 horas', 'há 1 dia')"""
```

**Exemplos de uso:**
- `format_timestamp(timestamp)` → "Segunda-feira, 17/11/2025 às 14:30:45"
- `get_time_diff_description(agora, passado)` → "há 3 horas"

### 2. Sistema de Memória Aprimorado (`memory/limited_postgres_memory.py`)

```python
def get_messages_with_timestamp_info(self) -> List[Dict[str, Any]]:
    """Recupera mensagens com informações de timestamp"""

def get_time_aware_context(self) -> List[BaseMessage]:
    """Retorna mensagens contextuais com metadados de tempo"""
```

### 3. Nova Ferramenta de Histórico (`agent_langgraph.py`)

```python
@tool
def historico_tool(telefone: str, limite: int = 5) -> str:
    """Consulta histórico de mensagens com timestamps"""
```

## 📋 Como Funciona

### 1. Armazenamento de Mensagens
Quando uma mensagem é salva no banco PostgreSQL, ela inclui:
- `session_id` (telefone do cliente)
- `message` (conteúdo da mensagem em JSON)
- `created_at` (timestamp automático)

### 2. Recuperação com Informações de Tempo
Quando o agente acessa o histórico, ele agora recebe:
- A mensagem original
- Horário formatado (ex: "Segunda-feira, 17/11/2025 às 14:30:45")
- Tempo decorrido (ex: "há 2 horas", "há 1 dia")

### 3. Uso no Contexto do Agente
As mensagens recuperadas incluem metadados de tempo que o agente pode usar para:
- Entender quando cada mensagem foi enviada
- Responder perguntas sobre tempo
- Manter contexto temporal da conversa

## 💬 Exemplos de Conversas

### Exemplo 1: Pergunta sobre Horário Atual
```
Cliente: "Que horas são agora?"
Ana: "📅 Segunda-feira, 17/11/2025 às 14:30:45 (BRT)"
```

### Exemplo 2: Pergunta sobre Histórico
```
Cliente: "Quando foi que eu te falei sobre o arroz?"
Ana: "Você mencionou o arroz há 2 horas, às Segunda-feira, 17/11/2025 às 12:30:15. 
     Ainda está procurando arroz ou posso te ajudar com outra coisa?"
```

### Exemplo 3: Consulta de Histórico Completo
```
Cliente: "Me mostra nossas mensagens anteriores"
Ana: [Usa historico_tool para mostrar últimas mensagens com timestamps]
```

## 🔧 Configuração

O sistema usa automaticamente o fuso horário de São Paulo (`America/Sao_Paulo`), mas pode ser configurado alterando o parâmetro `timezone` nas funções.

## 🎯 Benefícios

1. **Contexto Temporal**: O agente entende a sequência temporal das conversas
2. **Respostas Mais Naturais**: Pode responder perguntas sobre "quando" algo aconteceu
3. **Melhor Experiência**: Clientes sentem que o agente "lembra" da conversa
4. **Depuração Facilitada**: Timestamps ajudam a entender o fluxo de conversas

## 📝 Notas Importantes

- Todos os timestamps são armazenados em UTC no banco de dados
- A conversão para horário local (São Paulo) é feita na exibição
- O sistema mantém compatibilidade com o funcionamento anterior
- As informações de tempo são adicionadas como metadados nas mensagens