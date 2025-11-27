## QueryCraft Design Document

### 1. Purpose and Problem Statement
- Enable non-technical stakeholders to ask business questions in Persian or English and receive answers sourced from company databases.
- Automate translation of natural-language questions into SQL queries via an AI agent and return validated results through a web UI.
- Ship a reproducible, dockerized reference implementation that Bitpin can run with `docker-compose up`.

### 2. Functional Requirements
- Accept natural-language questions via a simple web page and a REST API (`POST /api/query/`).
- Convert questions to SQL using an Ollama-hosted `sqlcoder-7b-2.Q4_K_M.gguf` model orchestrated through LangGraph.
- Validate generated SQL and execute it only if safe; otherwise surface a helpful error.
- Persist and expose data stored across three tables: `customers`, `products`, `orders`.
- Provide a Faker-powered seeding command that populates ≥1,000 synthetic yet relationally consistent rows.
- Return query results (rows + optional metadata like execution time) as JSON.
- Document architecture, assumptions, and run instructions in `README.md` and `info.md`.

### 3. Non-Functional Requirements
- Reproducible local environment via Docker Compose with isolated services for `web`, `db`, `ollama`.
- Reasonable latency (<10s per question) and graceful handling of agent or database failures.
- Clean, maintainable Django codebase with clear module boundaries and lint/test hooks where feasible.
- Secure-by-default SQL execution (parameterized queries, deny destructive statements, limit result counts).

### 4. High-Level Architecture
```
Browser ⇄ Django Web (REST API, LangGraph Orchestrator) ⇄ Ollama LLM Service
                      ⇅
                 PostgreSQL DB
```
- **Django Web Service**: Hosts API, LangGraph workflow, ORM models, management commands, and static frontend.
- **PostgreSQL Service**: Stores normalized relational data.
- **Ollama Service**: Serves `sqlcoder` model accessible via HTTP from Django container.
- Docker Compose networks all services; `.env` files carry credentials.

### 5. Logical Modules
1. **API & Presentation Layer**
   - DRF or Django view for `/api/query/`.
   - Static frontend page served via Django template or `collectstatic`.
2. **Agent Orchestration**
   - LangGraph graph definition with nodes: `QuestionToSQL`, `ValidateSQL`, `ExecuteSQL`, `FormatResponse`.
   - Conditional edge routes invalid SQL to an `ErrorNode`.
3. **Data Layer**
   - Django models for `Customer`, `Product`, `Order`.
   - Custom manager/repository for raw SQL execution with safety checks.
4. **Seeding & Utilities**
   - `manage.py seed_db` command using Faker and bulk inserts, ensures referential integrity.
5. **Infrastructure**
   - Dockerfile for Django app, Compose file orchestrating `web`, `db`, `ollama`.
   - Volume bindings for persistent Postgres data and Ollama models.
6. **Frontend**
   - Minimal HTML/JS page (LLM-generated) that hits the API and displays results/error states.

### 6. Data Model
- **customers**: `id (PK)`, `name`, `email (unique)`, `registration_date`.
- **products**: `id (PK)`, `name`, `category`, `price (Decimal)`.
- **orders**: `id (PK)`, `customer (FK)`, `product (FK)`, `order_date`, `quantity`, `status (enum/text)`.
- ORM relationships: `Order` has `ForeignKey` to `Customer` & `Product` with cascade deletes disabled to preserve history.
- Index strategy: default PK indexes, plus indexes on `registration_date`, `category`, `status` for query speed.

### 7. LangGraph Workflow
1. **Input Node**: Receive `{question, language}` payload.
2. **QuestionToSQL Node**: Prompt template describing schema/table columns, expected SQL style, result limits.
3. **ValidateSQL Node**: Lightweight parser ensuring presence of `SELECT`/`FROM`, restricts keywords (`DROP`, `INSERT`, etc.), optional `sqlparse` sanity checks.
4. **Conditional Edge**:
   - **Valid** → ExecuteSQL Node.
   - **Invalid** → Error Node returning validation message.
5. **ExecuteSQL Node**: Run SQL against Postgres using Django connection with read-only transaction, limit rows (e.g., 200), convert decimals/dates for JSON.
6. **FormatResponse Node**: Package result rows, metadata, and optionally a natural-language summary (stretch goal).

### 8. API Contract
- Endpoint: `POST /api/query/`
- Request JSON: `{ "question": "در ماه گذشته چند کاربر جدید ثبت نام کرده‌اند؟", "language": "fa" }`
- Response Success: `{ "status": "ok", "sql": "...", "rows": [...], "columns": [...], "execution_ms": 123 }`
- Response Error: `{ "status": "error", "message": "...", "stage": "validation|execution|agent" }`
- Input validation: enforce non-empty strings, optional length caps, log requests for debugging (without sensitive data).

### 9. Frontend Page
- Static HTML + vanilla JS (generated via LLM) with:
  - Textarea for question input, optional language selector.
  - Submit button calling `/api/query/`.
  - Result table rendering and error banner.
  - Loading indicator and simple styling.
- Hosted via Django `TemplateView` or static file served through `collectstatic`.

### 10. Docker & Deployment Plan
- **Dockerfile (web)**: Base on Python 3.11 slim, install dependencies, copy app, run `python manage.py migrate && seed_db`.
- **docker-compose.yml**:
  - `db`: Postgres 15, env vars for user/pass/database, volume mount for data, healthcheck.
  - `ollama`: Official Ollama image, command to pull/run `sqlcoder-7b-2.Q4_K_M.gguf`, expose 11434.
  - `web`: Depends on `db`, `ollama`; build from Dockerfile, mounts source for rapid dev, env file for secrets, command `gunicorn` or `python manage.py runserver 0.0.0.0:8000`.
- Ensure networks allow `web` to reach `ollama:11434` and `db:5432`.
- Document `docker-compose up --build` as single entrypoint.

### 11. Tooling & Dependencies
- **Backend**: Django 5.x, Django REST Framework (optional), LangChain + LangGraph, psycopg2-binary, Faker, python-dotenv, sqlparse.
- **Frontend**: Plain HTML/JS; optional Tailwind/Bootstrap CDN if needed.
- **Testing**: pytest or Django’s `TestCase`, factory_boy for data, HTTP client tests, LangGraph unit tests with mocked Ollama responses.

### 12. Implementation Steps
1. Initialize Django project/app structure; configure settings & env handling.
2. Author models + migrations; set up Postgres connection.
3. Write `seed_db` management command leveraging Faker and bulk operations.
4. Implement LangGraph graph with nodes + conditional edge; integrate Ollama client.
5. Build `/api/query/` endpoint hooking into LangGraph workflow.
6. Create simple frontend page and static assets.
7. Containerize: Dockerfile, docker-compose, entrypoint scripts, README instructions.
8. Add tests (model, API, agent validation) and linting.
9. Document assumptions in `info.md`, finalize README.

### 13. Assumptions
- Ollama model file can be auto-downloaded within the container; startup time acceptable for demo.
- SQL queries remain read-only; no DDL/DML statements required.
- Seed data (1k+ rows) provides enough coverage for demonstration queries.
- Single-tenant deployment; authentication/authorization out of scope.
- LangGraph-based agent can run synchronously per request (no background queue needed).

### 14. Open Questions / Clarifications Needed
1. Should the agent log or store generated SQL/results for auditing?
2. Are there constraints on maximum runtime per query or need for pagination?
3. Is bilingual output (responses in Persian) necessary or just question input support?
4. Any security requirements around rate limiting or authentication for the API?
5. Should the frontend support query history/download?

### 15. Risks and Mitigations
- **LLM hallucinations or unsafe SQL**: enforce regex/AST validation, whitelist tables/columns, cap LIMIT.
- **Model startup latency**: document warm-up time, optionally add healthcheck endpoint to block requests until ready.
- **Seed command slowness**: use bulk_create in chunks, disable signals.
- **Docker resource usage**: allow configurable model quantization and Postgres memory settings.
- **Developer unfamiliarity with LangGraph**: modularize nodes, include docstrings/tests to ease understanding.

### 16. Future Enhancements (Post-MVP)
- Support schema inspection and automatic documentation to improve prompts.
- Add caching of frequent queries/questions.
- Introduce authentication + multi-tenant org separation.
- Add streaming responses or natural-language summaries on results.
- Integrate telemetry dashboards (Prometheus/Grafana) for monitoring agent performance.
