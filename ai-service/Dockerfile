# ai-service/Dockerfile

FROM python:3.10-slim
WORKDIR /app

# Install system dependencies (needed for compiling some Python packages)
RUN apt-get update && apt-get install -y build-essential curl tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Start the server using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]