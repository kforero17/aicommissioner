#!/usr/bin/env python3
"""
Test script for Celery-based admin endpoints.

This script verifies that the updated admin endpoints properly:
1. Dispatch Celery tasks and return task IDs
2. Poll task status correctly
3. Handle errors appropriately

Usage:
    python dev_tools/test_celery_endpoints.py

Prerequisites:
    - Redis running on localhost:6379
    - Celery worker running: celery -A schedulers.celery_app worker --loglevel=info
    - API server running on localhost:8000
    - Valid auth token
"""

import time
import requests
from typing import Dict, Any, Optional


# Configuration
BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "your-auth-token-here"  # Replace with valid token
LEAGUE_ID = 1  # Replace with valid league ID


def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Make an authenticated API request."""
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    url = f"{BASE_URL}{endpoint}"

    if method == "GET":
        response = requests.get(url, headers=headers, params=params)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data, params=params)
    else:
        raise ValueError(f"Unsupported method: {method}")

    response.raise_for_status()
    return response.json()


def test_league_sync():
    """Test POST /admin/leagues/{league_id}/sync endpoint."""
    print("\n" + "="*60)
    print("TEST 1: League Sync Endpoint")
    print("="*60)

    # Start sync
    print(f"\n1. Starting sync for league {LEAGUE_ID}...")
    response = make_request(
        "POST",
        f"/admin/leagues/{LEAGUE_ID}/sync",
        params={"week": 12}
    )

    print(f"   Response: {response}")
    assert "task_id" in response, "Response missing task_id"
    assert response["status"] == "pending", "Initial status should be pending"

    task_id = response["task_id"]
    print(f"   ✓ Task started with ID: {task_id}")

    return task_id


def test_task_polling(task_id: str):
    """Test GET /admin/tasks/{task_id} endpoint."""
    print("\n" + "="*60)
    print("TEST 2: Task Polling Endpoint")
    print("="*60)

    print(f"\n2. Polling task {task_id}...")

    max_attempts = 30
    for attempt in range(max_attempts):
        response = make_request("GET", f"/admin/tasks/{task_id}")

        status = response["status"]
        print(f"   Attempt {attempt + 1}: Status = {status}")

        if status == "SUCCESS":
            print(f"   ✓ Task completed successfully!")
            print(f"   Result: {response.get('result', {})}")
            return True
        elif status == "FAILURE":
            print(f"   ✗ Task failed!")
            print(f"   Error: {response.get('error', 'Unknown error')}")
            return False
        elif status == "STARTED":
            progress = response.get("progress", {})
            if progress:
                print(f"   Progress: {progress}")

        # Wait before next poll
        time.sleep(2)

    print(f"   ✗ Task did not complete within {max_attempts * 2} seconds")
    return False


def test_power_rankings():
    """Test POST /admin/recaps/power-rankings endpoint."""
    print("\n" + "="*60)
    print("TEST 3: Power Rankings Recap Endpoint")
    print("="*60)

    print(f"\n3. Starting power rankings for league {LEAGUE_ID}...")
    response = make_request(
        "POST",
        "/admin/recaps/power-rankings",
        data={"league_id": LEAGUE_ID, "week": 12}
    )

    print(f"   Response: {response}")
    assert "task_id" in response, "Response missing task_id"
    assert response["status"] == "pending", "Initial status should be pending"

    task_id = response["task_id"]
    print(f"   ✓ Power rankings task started with ID: {task_id}")

    return task_id


def test_waiver_recap():
    """Test POST /admin/recaps/waiver-recap endpoint."""
    print("\n" + "="*60)
    print("TEST 4: Waiver Recap Endpoint")
    print("="*60)

    print(f"\n4. Starting waiver recap for league {LEAGUE_ID}...")
    response = make_request(
        "POST",
        "/admin/recaps/waiver-recap",
        data={"league_id": LEAGUE_ID, "week": 12}
    )

    print(f"   Response: {response}")
    assert "task_id" in response, "Response missing task_id"
    assert response["status"] == "pending", "Initial status should be pending"

    task_id = response["task_id"]
    print(f"   ✓ Waiver recap task started with ID: {task_id}")

    return task_id


def test_invalid_task_id():
    """Test polling with invalid task ID."""
    print("\n" + "="*60)
    print("TEST 5: Invalid Task ID Handling")
    print("="*60)

    print("\n5. Polling with fake task ID...")
    fake_task_id = "fake-task-id-12345"

    response = make_request("GET", f"/admin/tasks/{fake_task_id}")

    print(f"   Response: {response}")
    print(f"   Status: {response.get('status')}")

    # For non-existent task, Celery returns PENDING status
    assert response["status"] == "PENDING", "Non-existent task should be PENDING"
    print(f"   ✓ Correctly returns PENDING for non-existent task")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CELERY ENDPOINTS TEST SUITE")
    print("="*60)
    print("\nPrerequisites:")
    print("  - Redis running on localhost:6379")
    print("  - Celery worker running")
    print("  - API server running on localhost:8000")
    print("  - Valid auth token configured")
    print("  - Valid league ID configured")

    try:
        # Test 1: League sync
        task_id = test_league_sync()

        # Test 2: Task polling
        test_task_polling(task_id)

        # Test 3: Power rankings (optional - requires league config)
        # Uncomment if league has power rankings enabled
        # pr_task_id = test_power_rankings()
        # test_task_polling(pr_task_id)

        # Test 4: Waiver recap (optional - requires league config)
        # Uncomment if league has waiver recaps enabled
        # wr_task_id = test_waiver_recap()
        # test_task_polling(wr_task_id)

        # Test 5: Invalid task ID
        test_invalid_task_id()

        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request error: {e}")
        print("\nMake sure:")
        print("  1. API server is running")
        print("  2. Auth token is valid")
        print("  3. League ID exists and belongs to user")
    except AssertionError as e:
        print(f"\n✗ Assertion failed: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
