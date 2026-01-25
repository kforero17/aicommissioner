# Celery-Based Admin Endpoints

This document describes the Celery-based async task endpoints for the AI Commissioner operator console.

## Overview

The admin API now uses Celery for asynchronous task processing instead of FastAPI's BackgroundTasks. This provides:

- **Task tracking**: Monitor progress of long-running operations
- **Reliability**: Tasks survive server restarts via Redis persistence
- **Scalability**: Distribute work across multiple Celery workers
- **Observability**: Better monitoring and error handling

## Architecture

```
┌─────────────────┐
│   Frontend      │
│   Dashboard     │
└────────┬────────┘
         │
         │ 1. POST /admin/leagues/{id}/sync
         ▼
┌─────────────────┐
│   FastAPI       │
│   Admin Routes  │
└────────┬────────┘
         │
         │ 2. dispatch task
         ▼
┌─────────────────┐     ┌─────────────────┐
│   Celery        │────▶│   Redis         │
│   Worker        │     │   Broker        │
└─────────────────┘     └─────────────────┘
         │
         │ 3. execute task
         ▼
┌─────────────────┐
│   Ingestors     │
│   (Sleeper/     │
│    Yahoo)       │
└─────────────────┘

Frontend polls: GET /admin/tasks/{task_id}
```

## Endpoints

### 1. POST /admin/leagues/{league_id}/sync

Starts a league data sync operation.

**Request:**
```bash
POST /admin/leagues/123/sync?week=12
Authorization: Bearer <token>
```

**Parameters:**
- `league_id` (path): League ID to sync
- `week` (query, optional): Week number (reserved for future use)

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "League sync started",
  "status": "pending"
}
```

**Errors:**
- `404`: League not found or user doesn't own it
- `401`: Unauthorized

---

### 2. GET /admin/tasks/{task_id}

Polls the status of a Celery task.

**Request:**
```bash
GET /admin/tasks/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
```

**Response (Pending):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING"
}
```

**Response (Success):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "result": {
    "status": "success",
    "message": "Synced league 123"
  }
}
```

**Response (Failure):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILURE",
  "error": "Provider API rate limit exceeded"
}
```

**Response (Started with Progress):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "STARTED",
  "progress": {
    "current": 3,
    "total": 10,
    "message": "Processing team 3 of 10"
  }
}
```

**Task Statuses:**
- `PENDING`: Task waiting to be executed
- `STARTED`: Task is currently running
- `SUCCESS`: Task completed successfully
- `FAILURE`: Task failed with error
- `RETRY`: Task is retrying after failure

---

### 3. POST /admin/recaps/power-rankings

Generates power rankings recap for a league.

**Request:**
```bash
POST /admin/recaps/power-rankings
Authorization: Bearer <token>
Content-Type: application/json

{
  "league_id": 123,
  "week": 12
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Power rankings recap started",
  "status": "pending"
}
```

**Errors:**
- `404`: League not found
- `400`: Power rankings disabled for league
- `401`: Unauthorized

---

### 4. POST /admin/recaps/waiver-recap

Generates waiver wire recap for a league.

**Request:**
```bash
POST /admin/recaps/waiver-recap
Authorization: Bearer <token>
Content-Type: application/json

{
  "league_id": 123,
  "week": 12
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Waiver recap started",
  "status": "pending"
}
```

**Errors:**
- `404`: League not found
- `400`: Waiver recaps disabled for league
- `401`: Unauthorized

## Frontend Integration

### Polling Pattern

```typescript
async function syncLeague(leagueId: number): Promise<void> {
  // Start sync
  const response = await fetch(`/admin/leagues/${leagueId}/sync`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  const { task_id } = await response.json();

  // Poll for completion
  const result = await pollTask(task_id);

  if (result.status === 'SUCCESS') {
    console.log('Sync completed:', result.result);
  } else {
    console.error('Sync failed:', result.error);
  }
}

async function pollTask(taskId: string, maxAttempts = 60): Promise<any> {
  for (let i = 0; i < maxAttempts; i++) {
    const response = await fetch(`/admin/tasks/${taskId}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const status = await response.json();

    if (status.status === 'SUCCESS' || status.status === 'FAILURE') {
      return status;
    }

    // Wait 2 seconds before next poll
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  throw new Error('Task polling timeout');
}
```

### React Hook Example

```typescript
import { useState, useCallback } from 'react';

interface TaskStatus {
  taskId: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE';
  result?: any;
  error?: string;
  progress?: any;
}

export function useTaskPolling() {
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const pollTask = useCallback(async (taskId: string) => {
    setIsPolling(true);
    setTaskStatus({ taskId, status: 'PENDING' });

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/admin/tasks/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });

        const status: TaskStatus = await response.json();
        setTaskStatus(status);

        if (status.status === 'SUCCESS' || status.status === 'FAILURE') {
          clearInterval(pollInterval);
          setIsPolling(false);
        }
      } catch (error) {
        console.error('Polling error:', error);
        clearInterval(pollInterval);
        setIsPolling(false);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, []);

  return { taskStatus, isPolling, pollTask };
}
```

## Celery Tasks

### Available Tasks

| Task | Function | Args |
|------|----------|------|
| `sync_specific_league` | Sync single league | `league_id`, `provider`, `provider_league_id` |
| `generate_manual_recap` | Generate recap | `league_id`, `recap_type`, `week` |
| `sync_all_leagues` | Sync all active leagues | None |
| `run_weekly_power_rankings` | Scheduled power rankings | None |
| `run_weekly_waiver_recaps` | Scheduled waiver recaps | None |

### Task Configuration

Tasks are configured in `/Users/kforero/aicommissioner/schedulers/celery_app.py`:

```python
app.conf.update(
    broker_url='redis://localhost:6379',
    result_backend='redis://localhost:6379',
    task_serializer='json',
    result_serializer='json',
    result_expires=3600,  # Results stored for 1 hour
    task_soft_time_limit=300,  # 5 minute soft limit
    task_time_limit=600,  # 10 minute hard limit
)
```

## Running Celery

### Start Worker

```bash
# Development (single worker)
celery -A schedulers.celery_app worker --loglevel=info

# Production (multiple workers)
celery -A schedulers.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --pool=prefork
```

### Start Beat Scheduler (for scheduled tasks)

```bash
celery -A schedulers.celery_app beat --loglevel=info
```

### Monitor Tasks (Flower)

```bash
# Install Flower
pip install flower

# Start Flower dashboard
celery -A schedulers.celery_app flower --port=5555
```

Access Flower at http://localhost:5555

## Testing

### Manual Testing

```bash
# Start sync
curl -X POST "http://localhost:8000/admin/leagues/1/sync?week=12" \
  -H "Authorization: Bearer <token>"

# Response: {"task_id": "abc-123", "message": "League sync started", "status": "pending"}

# Poll status (repeat until SUCCESS/FAILURE)
curl "http://localhost:8000/admin/tasks/abc-123" \
  -H "Authorization: Bearer <token>"

# Response: {"task_id": "abc-123", "status": "SUCCESS", "result": {...}}
```

### Automated Testing

Run the test suite:

```bash
python dev_tools/test_celery_endpoints.py
```

## Monitoring & Debugging

### Check Task Result in Redis

```bash
redis-cli

# Get task result
> GET celery-task-meta-<task-id>

# List all task results
> KEYS celery-task-meta-*
```

### View Task Logs

Celery worker logs show task execution:

```
[2026-01-24 14:30:00,123: INFO/MainProcess] Task schedulers.tasks.sync_specific_league[abc-123] received
[2026-01-24 14:30:05,456: INFO/ForkPoolWorker-1] Task schedulers.tasks.sync_specific_league[abc-123] succeeded
```

### Common Issues

**Issue: Tasks stuck in PENDING**
- Check if Celery worker is running
- Verify Redis connection
- Check worker logs for errors

**Issue: Tasks timeout**
- Increase `task_time_limit` in celery_app.py
- Check if provider APIs are responding
- Review task logs for bottlenecks

**Issue: Task results not found**
- Results expire after 1 hour (configurable)
- Check `result_expires` setting
- Ensure Redis is persisting data

## Migration Notes

### Changes from BackgroundTasks

**Before:**
```python
@router.post("/leagues/{league_id}/sync")
async def sync_league_data(
    league_id: int,
    background_tasks: BackgroundTasks,
    ...
):
    background_tasks.add_task(ingest_sleeper_league, ...)
    return {"message": "League sync started"}
```

**After:**
```python
@router.post("/leagues/{league_id}/sync")
async def sync_league_data(
    league_id: int,
    week: Optional[int] = None,
    ...
) -> Dict[str, Any]:
    task = sync_specific_league.apply_async(args=[...])
    return {
        "task_id": task.id,
        "message": "League sync started",
        "status": "pending"
    }
```

### Breaking Changes

1. **Response format changed**: Sync endpoints now return `task_id` instead of just `message`
2. **Async execution**: Tasks execute in separate worker processes, not main API process
3. **Dependencies**: Requires Redis and Celery worker to be running

### Backwards Compatibility

Existing endpoints remain functional:
- `GET /admin/leagues` - List leagues (unchanged)
- `PATCH /admin/leagues/{id}` - Update league (unchanged)
- `DELETE /admin/leagues/{id}` - Delete league (unchanged)

## Security Considerations

1. **Authentication required**: All endpoints require valid JWT token
2. **League ownership verified**: Users can only sync/manage their own leagues
3. **Task ID exposure**: Task IDs are UUIDs, safe to expose to frontend
4. **Rate limiting**: Consider adding rate limits for sync endpoints

## Performance

### Expected Timings

| Operation | Typical Duration |
|-----------|-----------------|
| League sync (Sleeper) | 2-5 seconds |
| League sync (Yahoo) | 5-10 seconds |
| Power rankings | 10-30 seconds (with LLM) |
| Waiver recap | 5-15 seconds |

### Polling Recommendations

- Poll interval: 2 seconds
- Max attempts: 60 (2 minutes timeout)
- Exponential backoff for retries
- Cancel polling on component unmount

## Future Enhancements

1. **WebSocket support**: Real-time task updates instead of polling
2. **Progress tracking**: Report task progress percentage
3. **Task cancellation**: Allow users to cancel running tasks
4. **Batch operations**: Sync multiple leagues in parallel
5. **Task history**: Store completed task history in database
