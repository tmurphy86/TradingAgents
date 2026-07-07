# Stage 1: Build React frontend
FROM node:20-slim AS ui-builder
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci --ignore-scripts
COPY ui/ ./
RUN npm run build

# Stage 2: Build Python package + deps
FROM python:3.12-slim AS py-builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_CACHE=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build
COPY . .
RUN uv pip install ".[api]"

# Stage 3: Dev — source volume-mounted for hot-reload; venv from py-builder is reused
FROM py-builder AS dev
RUN uv pip install ".[api,dev]"
WORKDIR /app
ENV PYTHONPATH=/app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# Stage 4: Test — extends py-builder, adds dev deps, runs pytest
FROM py-builder AS test
RUN uv pip install ".[api,dev]"
ENV PYTHONPATH=/build
CMD ["python", "-m", "pytest", "tests/", "-m", "unit or smoke or regression", "-q", "--tb=short"]

# Stage 5: Minimal runtime image
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080
COPY --from=py-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN useradd --create-home appuser \
 && install -d -m 0755 -o appuser -g appuser /home/appuser/.tradingagents
USER appuser
WORKDIR /home/appuser/app
COPY --from=py-builder --chown=appuser:appuser /build .
COPY --from=ui-builder --chown=appuser:appuser /ui/dist ./ui/dist
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
