FROM python:3.12-slim

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install production dependencies first — this layer is cached until
# pyproject.toml or uv.lock change, even when app code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY entrypoint.sh ./
COPY seed-all.sh ./
RUN chmod +x entrypoint.sh seed-all.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
