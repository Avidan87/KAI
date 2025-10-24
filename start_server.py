#!/usr/bin/env python3
"""
Startup script for KAI MiDaS server
Handles model loading and server startup with proper timing
"""

import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main startup function"""
    logger.info("Starting KAI MiDaS server...")
    
    # Get port from environment
    port = os.environ.get("PORT", "8000")
    host = "0.0.0.0"
    
    logger.info(f"Starting server on {host}:{port}")
    
    # Start the FastAPI server
    cmd = [
        "uvicorn", 
        "midas-mcp-server.server:app",
        "--host", host,
        "--port", port,
        "--workers", "1",
        "--timeout-keep-alive", "30",
        "--access-log"
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        # Start the server
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
