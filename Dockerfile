FROM python:3.12.11-bookworm

# use the latest version of uv from the official repository
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN groupadd -r presidio && useradd --no-log-init -r -g presidio presidio

WORKDIR /app

# Create necessary directories and set permissions
RUN mkdir -p /home/presidio/.cache/uv && \
    chown -R presidio:presidio /home/presidio/.cache && \
    chown -R presidio:presidio /app

COPY --chown=presidio:presidio pyproject.toml uv.lock ./

USER presidio

# Disable UV cache for runtime (read-only filesystem in K8s)
ENV UV_NO_CACHE=1

# resolve from uv.lock only, no dev dependencies
RUN uv sync --frozen --no-dev --no-cache
 
# Pre-install Dutch SpaCy model used in production/staging (pin to SpaCy 3.8 series).
# Use pip inside the venv and verify; force layer rebuild with ARG.
ARG FORCE_REBUILD_MAIN="2026-03-02T00:00Z"
RUN set -eux; echo "$FORCE_REBUILD_MAIN" >/dev/null; \
    .venv/bin/python -m ensurepip --upgrade; \
    .venv/bin/python -m pip install -q \
      "nl_core_news_md @ https://github.com/explosion/spacy-models/releases/download/nl_core_news_md-3.8.0/nl_core_news_md-3.8.0-py3-none-any.whl" \
    || .venv/bin/python -m spacy download nl_core_news_md; \
    .venv/bin/python -c "import spacy, importlib.metadata as m; spacy.load('nl_core_news_md'); print('nl_core_news_md installed'); [print(f'  {p}: {m.version(p)}') for p in ['presidio-analyzer','presidio-anonymizer','spacy']]"

COPY --chown=presidio:presidio src/api ./src/api
COPY --chown=presidio:presidio api.py ./
COPY --chown=presidio:presidio scripts/healthcheck.py scripts/check_deps.py ./scripts/


EXPOSE 8080

# Add Docker healthcheck
HEALTHCHECK \
    --interval=60s \
    --timeout=5s \
    --start-period=25s \
    --retries=5 \
  CMD [".venv/bin/python", "scripts/healthcheck.py", "--port", "8080"]

CMD [".venv/bin/python", "api.py", "--host", "0.0.0.0", "--workers", "2", "--env", "production", "--port", "8080"]