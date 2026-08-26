FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install dependencies only (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-install-project

# 2. Copy source code
COPY . .

# 3. Add virtualenv to PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
