# Healthcare Terminology Service

A standalone FastAPI microservice that owns all FHIR terminology data — ICD-10-CM, LOINC, RxNorm, SNOMED CT, and FHIR R4 built-in code systems. Split out from the FHIR server to allow independent scaling and deployment of terminology lookups.

## Tech Stack

| Concern | Library |
|---|---|
| Web framework | FastAPI 0.129+ |
| Database | PostgreSQL 17 (async via asyncpg) |
| ORM | SQLAlchemy 2.0+ (async) |
| Migrations | Alembic |
| Cache / Rate limit | Redis 8 |
| DI container | dependency-injector |
| Config | pydantic-settings (.env) |
| Package manager | uv |
| Python | 3.12+ |

## API

All endpoints are under `/api/v1/terminology/`. Interactive docs available at `http://localhost:8005/docs`.

Org-scoped requests require `X-Org-ID` and `X-User-ID` headers (no JWT in this service).

## Database Schema

11 tables, all prefixed `terminology_`:

| Table | Purpose |
|---|---|
| `terminology_code_system` | ICD-10-CM, LOINC, RxNorm, SNOMED CT, HL7 v2/v3 systems |
| `terminology_concept` | Individual codes with TSVECTOR full-text search + pg_trgm similarity |
| `terminology_concept_synonym` | Alternate names per concept |
| `terminology_concept_translation` | Translated display names |
| `terminology_relationship` | Parent/child and other inter-concept links |
| `terminology_value_set` | FHIR ValueSet definitions |
| `terminology_value_set_concept` | Concept membership in value sets |
| `terminology_field_binding` | Maps FHIR resource fields to value sets |
| `terminology_concept_embedding` | Vector embeddings for semantic search |
| `terminology_audit_log` | Change history |
| `terminology_concept_map` | Cross-system code mappings |

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [uv](https://github.com/astral-sh/uv)
- [just](https://github.com/casey/just)

### Environment

Copy `.env.example` to `.env` — defaults work for local Docker:

```bash
cp .env.example .env
```

### Run

```bash
just infra-up        # start Postgres 17 + Redis 8 (Docker)
just install         # install Python dependencies
just migrate         # apply database migrations
just run             # uvicorn with --reload on :8005
```

### Load Terminology Data

All loaders are idempotent — safe to re-run.

```bash
# FHIR R4 built-ins (required for field bindings)
# Download definitions.json.zip from https://hl7.org/fhir/R4/
just terminology-fhir-r4

# ICD-10-CM (~72k codes)
# Download from https://www.cms.gov/medicare/coding-billing/icd-10-codes
just terminology-icd10cm

# RxNorm (~100k drugs)
# Download from https://uts.nlm.nih.gov/uts/login
just terminology-rxnorm

# LOINC (~100k codes)
# Download from https://loinc.org/downloads/
just terminology-loinc

# SNOMED CT (~350k concepts, requires UMLS account)
# Download from https://www.nlm.nih.gov/healthit/snomedct/us_edition.html
just terminology-snomed

# Field bindings (run after terminology-fhir-r4)
just terminology-seed-bindings-r4

# Or load everything at once
just terminology-all
```

### Migration Commands

```bash
just migrate                          # apply pending migrations
just migrate-generate "add_table"     # autogenerate new migration
just migrate-down                     # roll back one migration
just migrate-status                   # show current revision
just migrate-history                  # show full history
```

### Reset Database

```bash
just db-reset    # drop volumes, recreate containers (destructive)
```

## Project Structure

```
app/
├── main.py                    # FastAPI app, lifespan, middleware
├── core/                      # config, database, logging, redis, schema_utils
├── di/                        # dependency injection container
├── models/terminology/        # SQLAlchemy ORM models
├── schemas/terminology.py     # Pydantic request/response schemas
├── repository/                # async database queries
├── services/                  # business logic
├── routers/                   # 17 REST endpoints
├── errors/                    # error types and handlers
├── middleware/                # rate limiting, user context
└── terminology/
    ├── import_/loaders/       # FHIR R4, ICD-10-CM, LOINC, RxNorm, SNOMED CT
    ├── import_/cli.py         # loader CLI entrypoint
    ├── seed_field_bindings.py
    └── seed_field_bindings_r4.py
migrations/                    # Alembic async migrations
```

## Environment Variables

| Variable | Description |
|---|---|
| `TERMINOLOGY_DATABASE_URL` | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis URL (`redis://...`) |
| `ENVIRONMENT` | `development` or `production` |

## Docker

Infrastructure only (DB + Redis) — the app runs locally via `just run`:

```bash
docker compose up -d    # start infra
docker compose down     # stop infra
docker compose down -v  # stop and wipe data
```
