# Análise do Workflow do Agente de Supermercado (n8n → Python)

## Visão Geral

O agente de supermercado foi originalmente implementado no **n8n** como um workflow de automação que integra diversos serviços para atendimento ao cliente via WhatsApp. O objetivo é recriar toda essa lógica em **Python** utilizando o framework **LangChain** para orquestração de agentes de IA.

## Arquitetura do Sistema Original (n8n)

### Fluxo Principal

O workflow do n8n segue este fluxo de execução:

1. **Webhook de Entrada**: Recebe mensagens do WhatsApp (texto, áudio, imagens)
2. **Processamento de Tipo de Mensagem**: Identifica se é texto, áudio ou imagem
3. **Conversão de Áudio**: Se for áudio, baixa e transcreve para texto
4. **Controle de Duplicação**: Verifica se a mensagem já foi processada
5. **Agente de IA**: Processa a mensagem usando GPT com acesso a ferramentas
6. **Envio de Resposta**: Retorna a resposta ao cliente via WhatsApp

### Componentes Identificados

| Componente | Função | Tecnologia no n8n | Implementação Python |
|------------|--------|-------------------|----------------------|
| **Webhook** | Receber mensagens do WhatsApp | n8n Webhook Node | FastAPI/Flask endpoint |
| **Switch de Tipo** | Identificar tipo de mensagem (texto/áudio/imagem) | Switch Node | Lógica condicional Python |
| **Download de Áudio** | Baixar arquivo de áudio | HTTP Request Node | `requests` library |
| **Transcrição** | Converter áudio em texto | Whisper/Speech-to-Text | OpenAI Whisper API |
| **Memória de Conversação** | Armazenar histórico de chat | Postgres Chat Memory | `PostgresChatMessageHistory` (LangChain) |
| **Agente de IA** | Orquestrar conversação e ferramentas | AI Agent Node | `AgentExecutor` (LangChain) |
| **LLM** | Modelo de linguagem | OpenAI GPT | `ChatOpenAI` (LangChain) |
| **Ferramentas** | Consultar estoque, criar pedidos, etc. | Custom Tools | Python functions + `@tool` decorator |
| **Base de Conhecimento** | RAG com embeddings | Supabase Vector Store + Cohere Reranker | `SupabaseVectorStore` + `CohereRerank` |
| **Redis** | Controle de estado de pedidos | Redis Node | `redis-py` library |
| **Envio de Resposta** | Enviar mensagem ao WhatsApp | HTTP Request Node | `requests` library |

## Ferramentas (Tools) do Agente

O agente possui **7 ferramentas** principais:

### 1. **estoque** - Consulta de Estoque
- **Função**: Consultar disponibilidade e preço de produtos
- **Método HTTP**: GET
- **URL**: `https://wildhub-wildhub-sistema-supermercado.5mos1l.easypanel.host/api/produtos/consulta?nome={produto}`
- **Autenticação**: Bearer Token
- **Implementação**: `tools/http_tools.py::estoque()`

### 2. **pedidos** - Criar Pedido
- **Função**: Enviar pedido finalizado para o dashboard
- **Método HTTP**: POST
- **URL**: `https://wildhub-wildhub-sistema-supermercado.5mos1l.easypanel.host/api/pedidos/`
- **Body**: JSON com detalhes do pedido
- **Implementação**: `tools/http_tools.py::pedidos()`

### 3. **alterar** - Atualizar Pedido
- **Função**: Modificar pedido existente
- **Método HTTP**: PUT
- **URL**: `https://wildhub-wildhub-sistema-supermercado.5mos1l.easypanel.host/api/pedidos/telefone/{telefone}`
- **Body**: JSON com alterações
- **Implementação**: `tools/http_tools.py::alterar()`

### 4. **set** - Marcar Pedido Ativo
- **Função**: Definir no Redis que um pedido está ativo
- **Chave**: `{telefone}pedido`
- **TTL**: 600 segundos (10 minutos)
- **Implementação**: `tools/redis_tools.py::set_pedido_ativo()`

### 5. **confirme** - Verificar Pedido Ativo
- **Função**: Consultar se existe pedido ativo no Redis
- **Chave**: `{telefone}pedido`
- **Implementação**: `tools/redis_tools.py::confirme_pedido_ativo()`

### 6. **time** - Obter Hora Atual
- **Função**: Retornar data e hora no fuso horário de São Paulo
- **Timezone**: America/Sao_Paulo
- **Implementação**: `tools/time_tool.py::get_current_time()`

### 7. **ean** - Base de Conhecimento (RAG)
- **Função**: Recuperar informações da base de conhecimento da empresa
- **Tecnologia**: Supabase Vector Store + OpenAI Embeddings + Cohere Reranker
- **TopK**: 3 documentos mais relevantes
- **Implementação**: `tools/kb_tools.py::ean_retrieve()`

## Fluxo de Dados

### Entrada de Mensagem

```
WhatsApp → Webhook → Identificação de Tipo → Processamento
                                                    ↓
                                            [Texto/Áudio/Imagem]
                                                    ↓
                                            Agente de IA
```

### Processamento pelo Agente

```
Mensagem do Cliente
        ↓
Consulta Base de Conhecimento (ean_tool)
        ↓
Identifica Intenção
        ↓
Executa Ferramentas Necessárias:
  - estoque_tool (consultar produtos)
  - confirme_tool (verificar pedido ativo)
  - pedidos_tool (criar novo pedido)
  - alterar_tool (modificar pedido)
  - set_tool (marcar pedido como ativo)
  - time_tool (informar horário)
        ↓
Gera Resposta
        ↓
Envia ao WhatsApp
```

## Variáveis de Ambiente Necessárias

O sistema requer as seguintes configurações:

```env
# OpenAI
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Supabase (Base de Conhecimento)
SUPABASE_URL=https://...
SUPABASE_KEY=...

# Cohere (Reranker)
COHERE_API_KEY=...

# Postgres (Memória)
POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:port/db
POSTGRES_TABLE_NAME=basemercadaokLkGG

# Redis (Estado)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# API do Supermercado
BASE_URL=https://wildhub-wildhub-sistema-supermercado.5mos1l.easypanel.host/api
AUTH_TOKEN=Bearer ...
```

## Diferenças entre n8n e Python

| Aspecto | n8n | Python (LangChain) |
|---------|-----|---------------------|
| **Orquestração** | Visual, baseada em nós | Código, baseada em classes |
| **Memória** | Automática via nó | Configuração manual com `RunnableWithMessageHistory` |
| **Ferramentas** | Nós pré-configurados | Funções Python com decorator `@tool` |
| **Prompt** | Configurado no nó Agent | `ChatPromptTemplate` com placeholders |
| **Webhook** | Nó Webhook integrado | Servidor web separado (FastAPI/Flask) |
| **Execução** | Trigger automático | Chamada de função explícita |

## Melhorias Propostas na Implementação Python

1. **Modularização**: Separação clara entre ferramentas, agente e servidor web
2. **Validação**: Uso de Pydantic para validar dados de entrada/saída
3. **Logging**: Sistema robusto de logs para debugging
4. **Tratamento de Erros**: Try-catch abrangente com mensagens claras
5. **Configuração**: Uso de `.env` para todas as credenciais
6. **Testes**: Possibilidade de criar testes unitários para cada ferramenta
7. **Escalabilidade**: Facilidade de adicionar novas ferramentas
8. **Documentação**: Docstrings detalhadas em todas as funções

## Próximos Passos

1. ✅ Análise completa do workflow
2. 🔄 Implementação das ferramentas em Python
3. 🔄 Configuração do agente LangChain
4. 🔄 Criação do servidor web (FastAPI)
5. 🔄 Integração com WhatsApp
6. 🔄 Testes e validação
7. 🔄 Documentação final

## Observações Importantes

- O modelo `gpt-5-mini-2025-08-07` mencionado no n8n não existe na OpenAI. Provavelmente é um erro de digitação ou modelo customizado. Usaremos `gpt-4o-mini` como alternativa.
- A tabela do Postgres se chama `basemercadaokLkGG` no workflow original.
- O TTL do Redis é de 600 segundos (10 minutos) para pedidos ativos.
- A base de conhecimento usa Cohere Reranker com topK=3 para melhorar a relevância dos resultados.
