#!/usr/bin/env python3
"""Test Yahoo OAuth 2.0 configuration without hitting rate limits."""

import os
import time
from datetime import datetime
from config import settings

def check_config():
    """Check OAuth 2.0 configuration."""
    print("🔍 Checking Yahoo OAuth 2.0 Configuration...")
    print("=" * 50)
    
    # Check environment variables
    has_client_id = bool(settings.yahoo_client_id)
    has_client_secret = bool(settings.yahoo_client_secret)
    
    print(f"✅ Client ID configured: {has_client_id}")
    print(f"✅ Client Secret configured: {has_client_secret}")
    print(f"✅ Redirect URI: {settings.yahoo_redirect_uri}")
    print(f"✅ Frontend URL: {settings.frontend_url}")
    
    if not has_client_id or not has_client_secret:
        print("\n❌ ERROR: Yahoo OAuth credentials not found!")
        print("Please set YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET in your .env file")
        return False
    
    # Check SSL certificates
    has_ssl = os.path.exists("cert.pem") and os.path.exists("key.pem")
    print(f"\n✅ SSL Certificates: {'Found' if has_ssl else 'Missing'}")
    
    if not has_ssl:
        print("⚠️  Run this to create SSL certificates:")
        print("   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj '/CN=localhost'")
    
    print("\n📝 Yahoo App Configuration Requirements:")
    print("1. Go to https://developer.yahoo.com/apps/")
    print("2. Make sure your app has this EXACT redirect URI:")
    print(f"   {settings.yahoo_redirect_uri}")
    print("3. Ensure 'Fantasy Sports Read' permission is enabled")
    
    return True

def wait_for_rate_limit():
    """Wait for rate limit to reset."""
    wait_time = 900  # 15 minutes
    print(f"\n⏰ Waiting {wait_time//60} minutes for rate limit to reset...")
    print(f"Started at: {datetime.now().strftime('%H:%M:%S')}")
    
    for i in range(wait_time, 0, -60):
        mins = i // 60
        print(f"   {mins} minutes remaining...", end='\r')
        time.sleep(60)
    
    print("\n✅ Wait complete! Rate limit should be reset.")

if __name__ == "__main__":
    if check_config():
        print("\n⚠️  IMPORTANT: Due to rate limiting, you should wait before testing again.")
        print("Options:")
        print("1. Wait 15 minutes (press 'w')")
        print("2. Skip wait and test now (press 's')")
        print("3. Exit (press any other key)")
        
        choice = input("\nYour choice: ").lower()
        
        if choice == 'w':
            wait_for_rate_limit()
            print("\n🚀 Ready to test! Run:")
            print("   python https_main_server.py")
        elif choice == 's':
            print("\n🚀 To test now, run:")
            print("   python https_main_server.py")
        else:
            print("\n👋 Exiting...")
