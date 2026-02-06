FROM ghcr.io/astral-sh/uv:alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

FROM python:3.11-alpine
WORKDIR /app
# Install uv in the final image
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
# Copy the project files
COPY . .
# Sync dependencies in the final image
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
RUN mkdir -p data

# Use uv run to ensure the environment is used
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
