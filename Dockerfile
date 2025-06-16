FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install web server for webhook handling
RUN pip install --no-cache-dir gunicorn

# Copy the serverless entry point
COPY server.py .

# Expose port for Yandex Serverless Container
EXPOSE 8080

# Run with gunicorn for webhook handling
CMD ["gunicorn", "server:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120"]
