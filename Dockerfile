FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Export only external third-party dependencies and install to system Python
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project --output-file requirements.txt && \
    uv pip install --system --no-cache -r requirements.txt

# 2. Copy source code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
