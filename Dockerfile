FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r api/requirements.txt

CMD ["uvicorn", "api.dev_app:api_app", "--host", "0.0.0.0", "--port", "10000"]
