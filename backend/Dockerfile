FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app/backend

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
COPY migrations/ /app/migrations/
COPY alembic.ini /app/alembic.ini

EXPOSE 8000

# Render injects PORT; Compose overrides this command.
CMD ["sh", "-c", "alembic -c /app/alembic.ini upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
