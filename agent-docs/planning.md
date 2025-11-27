## High-Level Plan
1. **Environment & Tooling** – Virtualenv, dependencies, Git, project structure docs.
2. **Backend Foundation** – Django project/app scaffolding, settings, database config.
3. **Data Layer** – Models, migrations, seeding command, Faker data.
4. **Agent Workflow** – LangGraph integration, Ollama client, SQL validation/execution.
5. **API & Frontend** – REST endpoint, simple UI, error handling.
6. **Dockerization & Ops** – Dockerfile, docker-compose, entrypoints, README/info docs.
7. **Testing & Polish** – Automated tests, linting, final doc updates, repo hygiene.

## Status Legend
- `Todo` – Next action, no work started.
- `Backlog` – Known work, not prioritized yet.
- `Doing` – Currently in progress.
- `Hold` – Blocked or awaiting input.
- `Failed` – Attempted but needs replan.
- `Done` - Action is done.

## Environment & Tooling Tasks
7. `Done` – Capture task context (`task.md`) and architecture (`design-doc.md`).
1. `Done` – Choose Python version and confirm availability -> 3.11
2. `Done` – Create virtual environment.
3. `Done` – Generate `requirements.txt` with baseline dependencies.
4. `Done` – Install dependencies inside the virtualenv.
5. `Done` – Add `.gitignore` for Python/Django/Docker artifacts.
6. `Done` – Initialize Git repository and connect to remote.
8. `Done` – Create short `README.md`.
9. `Backlog` – Configure formatter/linter tooling (Black, Ruff, etc.).
10. `Backlog` – Set up pre-commit hooks to enforce formatting/linting.
11. `Done` – Draft `agents.md` outlining agent architecture/usage guidelines.
12. `Done` – Craft the repo structure in `design-doc.md`.
13. `Done` – Write initial assumptions in `info.md` and remove them from `design-doc.md`.


## Backend Foundation Tasks
1. `Done` – Scaffold Django project (`django-admin startproject querycraft .`).
2. `Done` – Create primary Django app (e.g., `core`) for business logic.
3. `Done` – Register app and required third-party apps in `INSTALLED_APPS`.
4. `Done` – Configure base settings (time zone, language, static files, DRF defaults).
5. `Done` – Add environment variable loading (`python-dotenv`) for secrets and DB config placeholders.
6. `Done` – Run basic Django health check (`python manage.py check`) to confirm setup.
7. `Done` – Configure `DATABASES` for Postgres using env-driven credentials (`NAME`, `USER`, `PASSWORD`, `HOST`, `PORT`).
8. `Done` – Add `.env.example` (and stub `.env`) capturing `SECRET_KEY`, DB values, and Ollama host referenced by settings.


## Data Layer Tasks
1. `Done` – Define Django models for `Customer`, `Product`, `Order` with required fields, relationships, and metadata from the design doc.
2. `Done` – Generate initial migrations for the data models (`python manage.py makemigrations core`).
3. `Done` – Start the Postgres service via Docker Compose to make the database reachable for migrations.
4. `Done` – Apply migrations to the Postgres database (`python manage.py migrate`).
5. `Done` – Implement a read-only SQL execution helper/manager with safety checks (LIMIT enforcement, prohibited keywords).
6. `Done` – Build a Faker-powered `seed_db` management command inserting ≥1,000 relational rows across all tables.


## Agent Workflow Tasks
1. `Done` – Scaffold the LangGraph workflow structure (graph, nodes, edges) within the Django project.
2. `Todo` – Implement the QuestionToSQL node that calls the Ollama `sqlcoder` model with schema-aware prompting.
3. `Todo` – Implement the ValidateSQL node that enforces read-only rules and leverages the SQL helper for safety.
4. `Todo` – Implement the ExecuteSQL node that runs validated queries via `execute_safe_sql` and captures metadata.
5. `Todo` – Implement the FormatResponse/Error nodes that normalize outputs (rows, columns, execution time, errors).
6. `Todo` – Wire the nodes together in a LangGraph entrypoint function ready for the API to call.


## Dockerization & Ops Tasks
1. `Done` – Create an initial `docker-compose.yml` with the Postgres `db` service so other tasks can run against a containerized database.
2. `Done` – Extend `docker-compose.yml` with the `ollama` service (serving sqlcoder).
3. `Todo` – Add the `web` service definition (build context, env file, command) to docker-compose.
4. `Todo` – Ensure the Django web container can reach both `db` and `ollama` (network setup, service dependencies).
5. `Todo` – Wire Django settings/env vars to read the Ollama host/port from `.env` for local and containerized runs.
6. `Todo` – Document how to start all services (db, ollama, web) via Docker Compose and update README accordingly.
7. `Done` – Update the Ollama entrypoint script so it can pull the SQLCoder model without relying on missing tools in the base image.
8. `Todo` – Verify `docker-compose up` alone launches `web`, `db`, and `ollama` with working dependencies and document any prerequisites in `README.md`.
