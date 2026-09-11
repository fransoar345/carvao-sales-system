# Deploy online do Sistema Carvao

Este guia usa Railway para backend + PostgreSQL e Vercel para frontend.

## 1. Subir o codigo para o GitHub

Crie um repositorio no GitHub e envie a pasta `carvao-sales-system`.

## 2. Backend no Railway

1. Acesse `https://railway.com`.
2. Crie um novo projeto.
3. Adicione um banco PostgreSQL.
4. Adicione um servico a partir do repositorio GitHub.
5. Se o Railway pedir diretório raiz, use `backend`. Se ele estiver usando a raiz do repositório, tudo bem: existe um `Dockerfile` na raiz que sobe o backend.
6. Configure as variaveis:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET=gere-um-segredo-forte
ACCESS_TOKEN_EXPIRE_MINUTES=720
CORS_ORIGINS=https://seu-frontend.vercel.app
WHATSAPP_PROVIDER=mock
WHATSAPP_API_URL=
WHATSAPP_TOKEN=
MANAGER_WHATSAPP=+5563999999999
```

7. Faça deploy e copie a URL publica do backend.

## 3. Frontend na Vercel

1. Acesse `https://vercel.com`.
2. Importe o mesmo repositorio GitHub.
3. Defina o diretório raiz como `frontend`.
4. Configure a variavel:

```env
VITE_API_URL=https://sua-api.up.railway.app/api
```

5. Faça deploy.

## 4. Liberar CORS final

Depois que a Vercel gerar a URL final, volte no Railway e ajuste:

```env
CORS_ORIGINS=https://sua-url-final.vercel.app
```

Faça redeploy do backend.

## 5. Teste final

1. Abra a URL da Vercel.
2. Entre com `admin@carvao.local` / `admin123`.
3. Cadastre um produto.
4. Lance uma venda.
5. Confira se o estoque baixou no dashboard.

## Observacoes

- O banco e criado automaticamente na primeira inicializacao.
- Em producao, troque as senhas seed depois do primeiro acesso.
- Para WhatsApp real, ajuste `WHATSAPP_PROVIDER`, `WHATSAPP_API_URL` e `WHATSAPP_TOKEN`.
