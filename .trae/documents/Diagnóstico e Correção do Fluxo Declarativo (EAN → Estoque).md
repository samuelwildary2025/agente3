## Diagnóstico
- Sua Function do Supabase funciona (curl retornou múltiplos EANs). O agente respondeu com pedido de detalhes porque não recebeu EAN para "Arroz" ou não carregou corretamente `SMART_RESPONDER_URL/AUTH/APIKEY` do `.env`.
- Possível causa adicional: `ESTOQUE_EAN_BASE_URL` pode estar incorreta, impedindo a segunda etapa (preço/estoque).

## Ações Propostas
### 1) Garantir que o servidor lê seu `.env`
- Ajustar `.env` com:
  - `SMART_RESPONDER_URL=https://gmhpegzldsuibmmvqbxs.supabase.co/functions/v1/smart-responder`
  - `SMART_RESPONDER_AUTH=Bearer <token mostrado no curl>`
  - `SMART_RESPONDER_APIKEY=<mesmo token do curl>`
- Reiniciar o servidor para recarregar `config/settings.py`.

### 2) Validar a consulta EAN no agente
- Enviar `POST /agent/dryrun` com `{ "telefone": "5585...", "mensagem": "Coca Cola 2L" }`.
- Esperado: chamada de `ean` retorna EAN; em seguida o agente chama `estoque` com esse EAN.

### 3) Validar `ESTOQUE_EAN_BASE_URL`
- Testar manualmente com um EAN do seu curl (ex.: `7894900014211`): `GET {ESTOQUE_EAN_BASE_URL}/7894900014211` deve retornar lista com preço/estoque.
- Se retornar 404/erro, atualizar `ESTOQUE_EAN_BASE_URL` no `.env` para o endpoint correto do seu sistema.

### 4) Observabilidade (opcional)
- Adicionar logs de debug do resultado das ferramentas `ean` e `estoque` (somente servidor) para confirmar o encadeamento sem expor ao cliente.

## Critérios de Sucesso
- Dryrun com "Coca Cola 2L" retorna resposta contendo nome, EAN, preço, disponibilidade e quantidade.
- Mensagens no WhatsApp seguem o fluxo declarativo sem pedir detalhes quando houver EAN válido.

## Referências
- Ferramenta `ean`: `tools/http_tools.py:164–194`.
- `estoque_preco` (EAN → preço/estoque): `tools/http_tools.py:365–520`.
- Execução do agente: `agent.py:336–370`.
- Prompt declarativo: `prompts/agent_system.md:1–39`. 