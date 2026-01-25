#!/usr/bin/env python3
"""HTTPS server for main application to support Yahoo OAuth 2.0."""

import uvicorn
from main import app

if __name__ == "__main__":
    # Check if SSL certificates exist
    import os
    if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
        print("⚠️  SSL certificates not found. Creating self-signed certificates...")
        os.system("openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj '/CN=localhost'")
    
    print("🚀 Starting HTTPS server on https://localhost:8000")
    print("📝 Note: You may see a browser warning about self-signed certificate - that's normal for development")
    
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )
