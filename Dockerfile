FROM python:3.11-slim
WORKDIR /app

# Copia tudo (UI + API + helpers)
COPY . /app

# Dependências
RUN pip install --no-cache-dir -r api/requirements.txt

# Render define $PORT. Aponta para o objeto 'dev_app' em api/dev_app.py
CMD ["sh","-c","python -m uvicorn api.dev_app:dev_app --host 0.0.0.0 --port ${PORT:-8000}"]