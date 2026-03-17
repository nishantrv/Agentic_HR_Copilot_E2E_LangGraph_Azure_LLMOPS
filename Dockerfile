FROM python:3.11-slim
  WORKDIR /app
  
  # Copy dependencies first — Docker caches this layer if requirements.txt unchanged
  COPY requirements.txt .
  RUN pip install --no-cache-dir --upgrade pip && \
      pip install --no-cache-dir -r requirements.txt
  
  COPY app/ ./app/
  
  # Non-root user — security best practice
  RUN useradd --create-home appuser
  USER appuser
  
  EXPOSE 8000
  CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
