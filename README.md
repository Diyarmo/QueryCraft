# QueryCraft

QueryCraft lets non-technical teammates ask business questions in Persian or English, auto-convert them to safe SQL via an Ollama-powered LangGraph agent, and return results from PostgreSQL through a small Django web app.


## Documentation
- `agent-docs/task.md` – challenge brief and acceptance criteria.
- `agent-docs/design-doc.md` – architecture, LangGraph plan, schema notes.
- `agent-docs/planning.md` – single source of truth for tasks/status.
- `info.md` – running list of assumptions or scope tweaks.

## Run with Docker Compose
Prereqs: Docker (24+) with the Compose plugin and ~8 GB of disk for the sqlcoder model + Postgres volume.

1. Copy environment defaults and tweak as needed:
   ```bash
   cp .env.example .env
   ```
2. Build and launch all services (web, db, ollama) together:
   ```bash
   docker compose up --build
   ```
   - The first start downloads the `sqlcoder:7b-q4_K_M` model inside the `ollama` container, so expect several minutes of logs before it reports ready.
   - The `web` container runs Django’s dev server on `http://localhost:8000`; Postgres is available on `localhost:5432`.
3. In another terminal, run initial migrations and seed data if desired. You can use **Seed Database** button in UI for this purpose too!
   ```bash
   docker compose exec web python manage.py seed_db
   ```
4. Visit `http://localhost:8000/` to load the UI, or call the API directly once the logs show the web service listening.

To stop and clean up containers, press `Ctrl+C` in the Compose terminal; use `docker compose down -v` if you want to delete the Postgres/Ollama volumes.


## API Usage
- **Endpoint:** `POST /api/query/`
- **Headers:** `Content-Type: application/json`
- **Request body**
  - `question` (string, required): natural-language question, trimmed server-side.
  - `language` (string, optional): ISO-ish tag (e.g. `en`, `fa`). Default `en`.
  - `max_rows` (integer, optional): overrides the backend limit (upper bounded by server configuration).

```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
        "question": "List the top 5 products by total orders last quarter",
        "language": "en",
        "max_rows": 5
      }'
```

Successful responses follow this structure:

```json
{
  "status": "ok",
  "sql": "SELECT ... LIMIT 5",
  "columns": ["product_name", "order_count"],
  "rows": [
    {"product_name": "Wireless Headphones", "order_count": 87},
    {"product_name": "USB-C Cable", "order_count": 75}
  ],
  "execution_ms": 42.3,
  "metadata": {
    "max_rows": 5,
    "row_count": 2
  }
}
```

Validation or execution issues return structured errors so clients can branch on `status`:

```json
{
  "status": "error",
  "message": "`question` is required.",
  "stage": "request"
}
```

Errors originating deeper in the workflow set `stage` to `validate_sql`, `execute_sql`, or `server` to simplify troubleshooting.


## Coder Model Considerations

* The `sqlcoder:7b-q4_K_M` model has some trouble in using correct table name and schemas. Tweak your question to get the result!
* The `sqlcoder:7b-q4_K_M` is not primarly a multilingual model and has lower performance in Persian!
* These questions have been tested:
```
1. What are the products in `core_product` table?
2. What is `name` and `email` of customers in `core_customer` table?
3. نام محصولات در جدول `core_product` را نمایش بده
```



  
