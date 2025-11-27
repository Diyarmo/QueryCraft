## Assumptions & Scope Notes
- **Model availability**: The Ollama container can download and serve `sqlcoder-7b-2.Q4_K_M.gguf` without manual intervention; warm-up latency is acceptable for demo purposes.
- **Read-only SQL**: All generated SQL remains read-only (SELECT-only). DDL/DML statements such as INSERT/UPDATE/DELETE/DROP are out of scope and should be rejected.
- **Seed data volume**: Generating ≥1,000 Faker-driven rows across customers, products, and orders is sufficient to showcase realistic queries.
- **Single-tenant demo**: Authentication/authorization is not required for this MVP; assume all users share the same access.
- **Synchronous agent**: LangGraph workflow executes synchronously per request; no background queue or async worker is planned.
- **Local deployment**: Primary target is local docker-compose usage; production hardening (observability, autoscaling) is deferred unless noted otherwise.
