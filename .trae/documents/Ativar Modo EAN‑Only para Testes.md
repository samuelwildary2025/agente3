## Objetivo
- Fazer o agente responder apenas com EAN(s) e nome(s) do produto consultando a ferramenta `ean`. Ignorar estoque e qualquer outra ferramenta durante o teste.

## Mudanças Propostas (sem executar ainda)
1) Atualizar `prompts/agent_system.md` para modo EAN‑only:
- Instruir o agente a chamar somente `ean` com o nome simplificado do produto.
- Formatar resposta como lista: "<EAN> — <Produto>" (máx. 10 itens).
- Quando não houver resultados, pedir marca/tamanho.

2) Restringir ferramentas em `create_agent()`:
- Passar apenas `[ean_tool, ean_tool_alias]` para `create_openai_tools_agent` e `AgentExecutor`.
- Manter as demais ferramentas no código, mas fora do conjunto ativo durante este modo de teste.

3) Garantir ambiente Supabase:
- Confirmar `.env`: `SMART_RESPONDER_URL`, `SMART_RESPONDER_AUTH` (Bearer ...), `SMART_RESPONDER_APIKEY`.

## Verificação
- `POST /agent/dryrun` com "Coca Cola 2L" deve retornar somente EAN(s) e nome(s).
- "Arroz" pode solicitar refinamento (marca/tamanho) se a base não retornar EAN.

## Reversão
- Para voltar ao fluxo completo mais tarde, reintroduzir `estoque` no conjunto de ferramentas e restaurar o prompt declarativo produto→EAN→estoque.

## Referências
- Ferramenta `ean`: `tools/http_tools.py:164–194`
- Aliases: `agent.py:111–125`
- Construção do agente: `agent.py:269–281`