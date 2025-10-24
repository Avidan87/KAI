# Use official Python image
FROM python:3.13.7-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY midas-mcp-server/requirements-midas.txt ./midas-mcp-server/

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r ./midas-mcp-server/requirements-midas.txt

# Copy app code
COPY midas-mcp-server/ ./midas-mcp-server/

# Set environment variables for better performance
ENV PYTHONUNBUFFERED=1
ENV TORCH_HOME=/tmp/torch_cache

# Expose port (Railway sets $PORT)
EXPOSE 8000

# Copy startup script
COPY start_server.py ./

# Start server with optimized settings
CMD ["python", "start_server.py"]
