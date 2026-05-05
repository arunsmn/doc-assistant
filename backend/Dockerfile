FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install chromadb without heavy optional dependencies
RUN pip install --no-cache-dir chromadb --no-deps
RUN pip install --no-cache-dir hnswlib pydantic httpx overrides \
    posthog typing-extensions packaging importlib-metadata
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]