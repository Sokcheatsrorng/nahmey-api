FROM python:3.9-slim

WORKDIR /app

# Create uploads directory and make it writable
RUN mkdir -p /app/uploads && chmod 777 /app/uploads

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

