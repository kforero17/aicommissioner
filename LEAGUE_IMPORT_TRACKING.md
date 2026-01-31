# League Import Progress Tracking

## Overview

The league import flow has been updated to use **Celery tasks** instead of FastAPI's `background_tasks`. This provides trackable task IDs that the frontend can poll to monitor import progress.

## Changes Made

### 1. New Celery Tasks (`schedulers/tasks.py`)

#### `import_yahoo_leagues_task(user_id: int)`
- Imports all Yahoo leagues for a user
- Returns result with status, message, and league count
- Can be tracked using the returned task_id

#### `import_sleeper_league_task(league_id: str, owner_id: int)`
- Imports a single Sleeper league
- Returns result with status and message
- Can be tracked using the returned task_id

### 2. Updated Auth Endpoints (`api/routes/auth.py`)

#### Yahoo OAuth Callback
**Endpoint:** `GET /auth/yahoo/callback`

**Changes:**
- Removed `BackgroundTasks` dependency
- Now triggers `import_yahoo_leagues_task.apply_async()`
- Redirects with task_id in query params:
  ```
  /connect?yahoo_connected=true&task_id=abc-123-def-456
  ```

**Frontend Integration:**
```typescript
// Extract task_id from redirect URL
const params = new URLSearchParams(window.location.search);
const taskId = params.get('task_id');

if (taskId) {
  // Start polling for task status
  pollTaskStatus(taskId);
}
```

#### Manual Yahoo Import
**Endpoint:** `POST /auth/yahoo/import-leagues`

**Request:**
```bash
curl -X POST http://localhost:8000/auth/yahoo/import-leagues \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "message": "Yahoo league import started",
  "task_id": "abc-123-def-456"
}
```

#### Sleeper League Addition
**Endpoint:** `POST /auth/sleeper/leagues`

**Request:**
```bash
curl -X POST http://localhost:8000/auth/sleeper/leagues \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "league_ids": ["league1", "league2"]
  }'
```

**Response:**
```json
{
  "message": "Sleeper league import started",
  "task_ids": [
    {
      "league_id": "league1",
      "task_id": "task-1-id"
    },
    {
      "league_id": "league2",
      "task_id": "task-2-id"
    }
  ],
  "user": {
    "id": 1,
    "username": "user@example.com",
    ...
  }
}
```

## Polling Task Status

### Endpoint
**GET** `/admin/tasks/{task_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

### Response States

#### PENDING (Task Queued)
```json
{
  "task_id": "abc-123-def-456",
  "status": "PENDING"
}
```

#### STARTED (Task Running)
```json
{
  "task_id": "abc-123-def-456",
  "status": "STARTED"
}
```

#### SUCCESS (Task Completed)
```json
{
  "task_id": "abc-123-def-456",
  "status": "SUCCESS",
  "result": {
    "status": "success",
    "message": "Successfully imported 3 Yahoo league(s)",
    "league_count": 3
  }
}
```

#### FAILURE (Task Failed)
```json
{
  "task_id": "abc-123-def-456",
  "status": "FAILURE",
  "error": "Failed to import Yahoo leagues - check user credentials"
}
```

## Frontend Implementation Guide

### React Hook for Task Polling

```typescript
import { useState, useEffect, useRef } from 'react';

interface TaskStatus {
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE';
  result?: any;
  error?: string;
}

export function useTaskPolling(taskId: string | null, interval = 2000) {
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!taskId) return;

    setIsPolling(true);

    const pollStatus = async () => {
      try {
        const response = await fetch(`/admin/tasks/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${getAccessToken()}`
          }
        });

        const data: TaskStatus = await response.json();
        setTaskStatus(data);

        // Stop polling if task is complete
        if (data.status === 'SUCCESS' || data.status === 'FAILURE') {
          setIsPolling(false);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
          }
        }
      } catch (error) {
        console.error('Error polling task status:', error);
        setIsPolling(false);
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      }
    };

    // Poll immediately, then on interval
    pollStatus();
    intervalRef.current = setInterval(pollStatus, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [taskId, interval]);

  return { taskStatus, isPolling };
}
```

### Usage Example

```typescript
function LeagueImportStatus({ taskId }: { taskId: string }) {
  const { taskStatus, isPolling } = useTaskPolling(taskId);

  if (!taskStatus) {
    return <div>Loading...</div>;
  }

  if (isPolling) {
    return (
      <div className="flex items-center gap-2">
        <Spinner />
        <span>Importing leagues...</span>
      </div>
    );
  }

  if (taskStatus.status === 'SUCCESS') {
    return (
      <div className="text-green-600">
        ✓ {taskStatus.result?.message}
      </div>
    );
  }

  if (taskStatus.status === 'FAILURE') {
    return (
      <div className="text-red-600">
        ✗ {taskStatus.error || 'Import failed'}
      </div>
    );
  }

  return null;
}
```

## Testing

### Manual Testing with cURL

1. **Trigger Yahoo import:**
```bash
curl -X POST http://localhost:8000/auth/yahoo/import-leagues \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -v
```

2. **Poll task status:**
```bash
# Use task_id from previous response
curl http://localhost:8000/admin/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

3. **Check imported leagues:**
```bash
curl http://localhost:8000/auth/yahoo/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Automated Testing

See `test_league_import.py` for a complete test script demonstrating:
- Triggering imports
- Polling task status
- Handling success/failure cases

## Error Handling

### Common Errors

1. **No Yahoo credentials:**
   - Status: 400 Bad Request
   - Message: "Yahoo account not connected"
   - Action: User needs to complete Yahoo OAuth flow

2. **Token expired:**
   - Task completes with "error" status
   - Message: "Failed to import Yahoo leagues - check user credentials"
   - Action: Re-authenticate with Yahoo

3. **Network/API errors:**
   - Task completes with "error" status
   - Message includes exception details
   - Action: Retry import or check logs

### Retry Strategy

Frontend should implement:
1. **Initial polling:** Every 2 seconds
2. **Timeout:** Stop after 60 seconds (30 attempts)
3. **Exponential backoff:** Optional for long-running imports
4. **Manual retry:** Provide button to re-trigger import

## Benefits of Celery Tasks

1. **Progress Tracking:** Frontend can show real-time status
2. **User Feedback:** Clear success/failure messages
3. **Debugging:** Task results stored in Redis for inspection
4. **Scalability:** Tasks can be distributed across workers
5. **Retry Logic:** Built-in retry mechanisms for transient failures
6. **Monitoring:** Celery provides task monitoring tools (Flower)

## Migration Notes

### Breaking Changes
- `/auth/sleeper/leagues` response format changed
  - Before: Returns `UserResponse` directly
  - After: Returns object with `message`, `task_ids`, and `user`

### Backward Compatibility
- All other endpoints remain unchanged
- Existing OAuth flows still work
- Task polling is optional (tasks complete regardless)

## Performance Considerations

1. **Polling frequency:** 2-second interval is reasonable
2. **Task timeout:** Yahoo import typically takes 5-30 seconds
3. **Redis storage:** Task results expire after 1 hour by default
4. **Concurrent imports:** Multiple users can import simultaneously

## Future Enhancements

1. **WebSocket notifications:** Push task status instead of polling
2. **Progress percentage:** Track individual league imports
3. **Batch operations:** Import all leagues with single task
4. **Cancel support:** Allow users to cancel in-progress imports
5. **Retry button:** Automatic retry with exponential backoff
