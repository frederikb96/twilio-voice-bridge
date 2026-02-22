FROM python:3.12-slim

RUN useradd -r -s /bin/false appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

USER appuser

EXPOSE 5050

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "5050"]
