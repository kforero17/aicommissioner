# Celery Endpoints - Quick Reference

## 🚀 Quick Start

### Start Services
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
celery -A schedulers.celery_app worker --loglevel=info

# Terminal 3: API Server
uvicorn main:app --reload
```

## 📡 API Endpoints

### Sync League
```bash
POST /admin/leagues/{league_id}/sync?week={week}
Authorization: Bearer <token>

Response:
{
  "task_id": "uuid-here",
  "message": "League sync started",
  "status": "pending"
}
```

### Poll Task Status
```bash
GET /admin/tasks/{task_id}
Authorization: Bearer <token>

Response:
{
  "task_id": "uuid-here",
  "status": "SUCCESS",  # or PENDING, STARTED, FAILURE
  "result": {...}       # if SUCCESS
  "error": "..."        # if FAILURE
}
```

### Generate Power Rankings
```bash
POST /admin/recaps/power-rankings
Authorization: Bearer <token>
Content-Type: application/json

{
  "league_id": 123,
  "week": 12
}

Response: Same as sync endpoint
```

### Generate Waiver Recap
```bash
POST /admin/recaps/waiver-recap
Authorization: Bearer <token>
Content-Type: application/json

{
  "league_id": 123,
  "week": 12
}

Response: Same as sync endpoint
```

## 💻 Frontend Code

### TypeScript/JavaScript
```typescript
// Start sync
const response = await fetch(`/admin/leagues/${leagueId}/sync`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
});
const { task_id } = await response.json();

// Poll status
async function pollTask(taskId: string): Promise<any> {
  while (true) {
    const response = await fetch(`/admin/tasks/${taskId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const status = await response.json();

    if (status.status === 'SUCCESS') {
      return status.result;
    } else if (status.status === 'FAILURE') {
      throw new Error(status.error);
    }

    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

// Usage
const result = await pollTask(task_id);
console.log('Sync complete:', result);
```

### React Hook
```typescript
const { taskStatus, isPolling, pollTask } = useTaskPolling();

// Start sync and poll
const handleSync = async () => {
  const response = await fetch(`/admin/leagues/${leagueId}/sync`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const { task_id } = await response.json();
  await pollTask(task_id);
};

// Display status
{isPolling && <Spinner />}
{taskStatus?.status === 'SUCCESS' && <Success message={taskStatus.result.message} />}
{taskStatus?.status === 'FAILURE' && <Error message={taskStatus.error} />}
```

## 🔍 Task Statuses

| Status | Meaning | Action |
|--------|---------|--------|
| `PENDING` | Task queued, not started | Keep polling |
| `STARTED` | Task executing | Keep polling, show progress if available |
| `SUCCESS` | Task completed | Stop polling, show result |
| `FAILURE` | Task failed | Stop polling, show error |
| `RETRY` | Task retrying after failure | Keep polling |

## 🛠️ Debugging

### Check Redis
```bash
redis-cli

# List all task results
KEYS celery-task-meta-*

# Get specific task result
GET celery-task-meta-<task-id>
```

### Monitor with Flower
```bash
pip install flower
celery -A schedulers.celery_app flower --port=5555
# Open http://localhost:5555
```

### View Celery Logs
```bash
# Worker logs show task execution
celery -A schedulers.celery_app worker --loglevel=debug
```

## ⚡ Common Issues

### Task stuck in PENDING
- ✓ Check Celery worker is running
- ✓ Verify Redis is running
- ✓ Check worker logs for errors

### Task timeout
- ✓ Increase `task_time_limit` in celery_app.py
- ✓ Check provider API response times
- ✓ Review task logs

### Can't find task result
- ✓ Results expire after 1 hour
- ✓ Check `result_expires` in celery_app.py
- ✓ Ensure Redis persistence enabled

## 📋 Polling Best Practices

- **Poll interval**: 2 seconds
- **Timeout**: 60 attempts (2 minutes)
- **Cancel on unmount**: Clear interval in cleanup
- **Error handling**: Retry with exponential backoff

## 🔐 Security

- All endpoints require authentication
- Users can only access their own leagues
- Task IDs are UUIDs (safe to expose)
- Consider rate limiting for production

## 📊 Performance

| Operation | Expected Time |
|-----------|--------------|
| Sleeper sync | 2-5 seconds |
| Yahoo sync | 5-10 seconds |
| Power rankings | 10-30 seconds |
| Waiver recap | 5-15 seconds |

## 📚 Full Documentation

- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Complete API Docs**: See `CELERY_ENDPOINTS.md`
- **Test Suite**: See `dev_tools/test_celery_endpoints.py`
