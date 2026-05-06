FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgomp1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir onnxruntime && python -c "import onnxruntime; print('onnxruntime ok')"
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8080
CMD ["sh", "-c", "echo PORT=$PORT && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --log-level debug"]