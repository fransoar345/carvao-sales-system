# Sistema Web de Vendas e Estoque para Distribuidora de Carvao

Aplicacao online com backend FastAPI, frontend React/Vite e suporte a PostgreSQL em producao. Em desenvolvimento, roda com SQLite automaticamente.

## Recursos entregues

- Login JWT com perfis `admin`, `gerente` e `vendedor`.
- CRUD de produtos, com tipos separados para saco fechado, embalagem vazia e outros.
- Entrada, saida, ajuste e devolucao de estoque com historico e auditoria.
- Cadastro de vendedores com usuario de acesso, WhatsApp, meta e comissao.
- Lancamento de vendas mobile-first com baixa automatica de estoque.
- Dashboard com estoque atual, total vendido, ranking, comissao e filtros.
- Exportacao de vendas em Excel e PDF.
- Configuracao de alertas com modo `mock`, Telegram Bot e estrutura para Meta, Z-API ou Twilio.
- Seed automatico para testar imediatamente.

## Credenciais de teste

- Admin: `admin@carvao.local` / `admin123`
- Gerente: `gerente@carvao.local` / `gerente123`
- Vendedor: `ana@carvao.local` / `vendedor123`
- Vendedor: `lucas@carvao.local` / `vendedor123`

## Rodar localmente

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`.

## Rodar com Docker

```bash
docker compose up --build
```

- Frontend: `http://localhost:8080`
- Backend/API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Variaveis de ambiente

Copie `.env.example` para `.env` no backend ou configure no provedor de hospedagem.

Para PostgreSQL, use:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/banco
```

## WhatsApp

O modo padrao `mock` registra as mensagens no console. Para provedor real, configure:

- `WHATSAPP_PROVIDER=meta`, `zapi` ou `twilio`
- `WHATSAPP_API_URL`
- `WHATSAPP_TOKEN`
- `MANAGER_WHATSAPP`

O endpoint atual envia `{ "to": "...", "message": "..." }` com bearer token. Caso o provedor escolhido tenha formato diferente, ajuste `backend/app/whatsapp.py`.

### Telegram

Crie um bot com o `@BotFather`, envie `/start` para o bot e obtenha o `chat.id` em `https://api.telegram.org/botSEU_TOKEN/getUpdates`. Na tela de alertas, selecione `Telegram Bot`, informe o token e o Chat ID do gestor ou grupo. O Telegram envia os alertas ao chat configurado; ele nao localiza vendedores pelo numero de telefone.

## Backup e deploy

Em producao, use PostgreSQL gerenciado com backup automatico no Railway, Render ou VPS. Exija HTTPS no proxy ou plataforma de deploy e nunca publique o `.env` real.
