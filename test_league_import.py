"""
Test script to verify Yahoo league import with Celery task tracking.

Usage:
    python test_league_import.py

This script demonstrates:
1. How to trigger a Yahoo league import and get a task_id
2. How to poll the task status using the admin endpoint
3. How to interpret the results
"""
import asyncio
import httpx
import time


async def test_yahoo_import():
    """Test Yahoo league import with task tracking."""
    base_url = "http://localhost:8000"

    # Replace with a valid access token for testing
    # You can get this by logging in through the web app
    access_token = "YOUR_ACCESS_TOKEN_HERE"

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        # Step 1: Trigger Yahoo league import
        print("Triggering Yahoo league import...")
        response = await client.post(
            f"{base_url}/auth/yahoo/import-leagues",
            headers=headers
        )

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return

        data = response.json()
        task_id = data.get("task_id")
        print(f"Import started. Task ID: {task_id}")
        print(f"Response: {data}")

        # Step 2: Poll task status
        print("\nPolling task status...")
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            attempt += 1

            # Check task status
            status_response = await client.get(
                f"{base_url}/admin/tasks/{task_id}",
                headers=headers
            )

            if status_response.status_code != 200:
                print(f"Error checking status: {status_response.status_code}")
                break

            status_data = status_response.json()
            status = status_data.get("status")
            print(f"Attempt {attempt}: Status = {status}")

            if status == "SUCCESS":
                result = status_data.get("result", {})
                print(f"\nImport completed successfully!")
                print(f"Result: {result}")
                break
            elif status == "FAILURE":
                error = status_data.get("error")
                print(f"\nImport failed!")
                print(f"Error: {error}")
                break
            elif status in ["PENDING", "STARTED"]:
                # Still processing, wait and retry
                time.sleep(2)
            else:
                print(f"Unknown status: {status}")
                break

        if attempt >= max_attempts:
            print("\nTimeout: Task did not complete within expected time")


if __name__ == "__main__":
    print("Yahoo League Import Test Script")
    print("=" * 50)
    print("\nNote: Update access_token in the script before running")
    print("You can get a token by logging in through the web app\n")

    # Uncomment to run the test
    # asyncio.run(test_yahoo_import())

    print("\nHow to use the import feature:")
    print("-" * 50)
    print("\n1. Manual import endpoint:")
    print("   POST /auth/yahoo/import-leagues")
    print("   Headers: Authorization: Bearer <token>")
    print("   Response: {\"message\": \"...\", \"task_id\": \"abc-123\"}")

    print("\n2. OAuth callback (automatic):")
    print("   GET /auth/yahoo/callback")
    print("   Redirects to: /connect?yahoo_connected=true&task_id=abc-123")

    print("\n3. Poll task status:")
    print("   GET /admin/tasks/{task_id}")
    print("   Headers: Authorization: Bearer <token>")
    print("   Response statuses:")
    print("   - PENDING: Task queued but not started")
    print("   - STARTED: Task is running")
    print("   - SUCCESS: Task completed, check 'result' field")
    print("   - FAILURE: Task failed, check 'error' field")

    print("\n4. Check imported leagues:")
    print("   GET /auth/yahoo/status")
    print("   Headers: Authorization: Bearer <token>")
    print("   Returns connected status and list of imported leagues")
