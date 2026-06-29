FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for compiling some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the data directories exist with proper permissions
RUN mkdir -p synced_docs analytics_data && chmod 777 synced_docs analytics_data

EXPOSE 8000

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
