# SAC Pró-Gestão RPPS — API

API do Sistema de Auditoria e Certificação **Pró-Gestão RPPS** (Manual MPS/PREVIC v4.1).
Backend **FastAPI + SQLAlchemy 2 + PostgreSQL**, consumido pelo frontend Next.js.

## Stack

| Camada     | Tecnologia                                   |
|------------|----------------------------------------------|
| Runtime    | Python 3.11–3.13                              |
| Framework  | FastAPI + Uvicorn                             |
| ORM        | SQLAlchemy 2.0 (`Column`-style)               |
| Banco      | PostgreSQL (dev/prod) · SQLite (fallback dev) |
| Auth       | JWT (HS256, python-jose) + bcrypt             |
| Config     | pydantic-settings (`.env`)                    |
| Cache      | Redis (opcional — ainda sem features)         |
| Qualidade  | pytest + httpx · ruff                          |
| Deps       | Poetry                                         |

## Requisitos

- Python 3.11+ (3.13 ok)
- [Poetry](https://python-poetry.org/)
- PostgreSQL 16 (local ou via Docker) — opcional, há fallback SQLite
- Docker (opcional) para subir Postgres + Redis

## Como rodar

```bash
cd backend

# 1. Instalar dependências
poetry install

# 2. Copiar e ajustar variáveis de ambiente
cp .env.example .env

# 3. (opcional) Subir Postgres + Redis
docker compose -f docker-compose.dev.yml up -d

# 4. Criar as tabelas (estrutura base) e, opcionalmente, dados demo
poetry run python -m app.db.seed          # só base: tenant, perfis, páginas, usuários
poetry run python -m app.db.seed --demo   # + unidades, requisitos, ações, diligências

# 5. Subir a API
poetry run uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Docs interativas: http://localhost:8000/api/docs
- Health: http://localhost:8000/api/health

> Recomendado usar Poetry. Sem ele, crie um venv e instale as dependências
> listadas no `pyproject.toml` manualmente.

### Banco sem Postgres (dev rápido)

No `.env`, aponte para SQLite:

```env
DATABASE_URL=sqlite:///./sac_progestao.db
```

## Credenciais de demonstração (senha: `Demo@2026!`)

| Perfil          | E-mail                          |
|-----------------|---------------------------------|
| Admin Master    | admin@fumpres.ba.gov.br         |
| Admin do Ente   | auditor@fumpres.ba.gov.br       |
| Operacional     | operador@fumpres.ba.gov.br      |
| Visualizador    | viewer@previc.gov.br            |
| Katiane Vieira  | katiane@fumpres.ba.gov.br       |

## Testes e lint

```bash
poetry run pytest        # testes de fumaça (SQLite temporário)
poetry run ruff check .  # lint
```

## Estrutura

```
backend/
├── pyproject.toml            ← Poetry, deps, ruff, pytest
├── .env.example              ← variáveis de ambiente
├── docker-compose.dev.yml    ← Postgres + Redis (infra)
├── app/
│   ├── main.py               ← cria o FastAPI e inclui os routers
│   ├── core/
│   │   ├── config.py         ← Settings (pydantic-settings)
│   │   ├── security.py       ← bcrypt + JWT
│   │   └── redis.py          ← client Redis (opcional)
│   ├── db/
│   │   ├── base.py           ← engine, SessionLocal, Base, get_db
│   │   └── seed.py           ← popula dados demo (python -m app.db.seed)
│   ├── models/               ← SQLAlchemy: rbac, progestao, certificacao, ged
│   ├── schemas/              ← Pydantic v2
│   └── api/
│       ├── deps.py           ← get_usuario_atual, requer_perfil
│       └── routers/          ← auth, admin, diagnostico, plano, diligencias,
│                                bi, certificacoes, operacional, health
└── tests/                    ← pytest + TestClient
```

## Endpoints principais

| Grupo            | Rotas                                                            |
|------------------|------------------------------------------------------------------|
| Auth             | `POST /api/auth/login` · `GET /api/auth/me`                      |
| Administração    | `/api/usuarios` · `/api/perfis` · `/api/unidades`                |
| Diagnóstico      | `GET /api/requisitos`                                            |
| Plano de Ação    | `GET/POST /api/acoes` · `PATCH /api/acoes/{id}/status`           |
| Diligências      | `GET/POST /api/diligencias` · `PATCH .../retorno` · `.../aprovar`|
| BI               | `GET /api/bi/consolidado`                                        |
| Certificações    | `/api/certificacoes` · `/api/auditorias`                         |
| Operacional      | `/api/tarefas` · `/api/evidencias` · `/api/onboarding` · `/api/processos` |
| Sistema          | `GET /api/health`                                                |
