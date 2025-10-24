# Use official Python image
FROM python:3.13.7-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY midas-mcp-server/requirements-midas.txt ./midas-mcp-server/

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r ./midas-mcp-server/requirements-midas.txt

# Copy app code
COPY midas-mcp-server/ ./midas-mcp-server/

# Expose port (Railway sets $PORT)
EXPOSE 8000

# Start server (use $PORT if set)
CMD ["sh", "-c", "uvicorn midas-mcp-server.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
