FROM python:3.12-slim AS base

RUN useradd -r -s /bin/false appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Dev stage: source mounted from host
FROM base AS dev
COPY config/ ./config/
EXPOSE 5050
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "5050", "--reload"]

# Prod stage: source baked into image
FROM base AS prod
COPY config/ ./config/
COPY src ./src
USER appuser
EXPOSE 5050
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "5050"]
