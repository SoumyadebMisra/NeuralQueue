FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code (which acts as our neuralqueue-core library)
COPY backend/ ./backend/

ENV PYTHONPATH=/app
