# Dockerfile — builds the image for both the web server and the worker.

FROM python:3.13-slim

# Install uv (the package manager).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy the whole project in first, THEN install — so uv can find src/ when it
# builds the project package.
COPY . .
RUN uv sync --frozen --no-dev

# Default start command (compose overrides this for the worker).
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]