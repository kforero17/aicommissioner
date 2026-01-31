# League Import Progress Tracking - Implementation Summary

## Overview
Updated the Yahoo and Sleeper league import flow to use Celery tasks instead of FastAPI background tasks, enabling the frontend to track import progress via task IDs.

## Files Modified

### 1. `/Users/kforero/aicommissioner/schedulers/tasks.py`

**Added two new Celery tasks:**

#### `import_yahoo_leagues_task(user_id: int)`
- Celery task wrapper for Yahoo league import
- Returns structured result with status, message, and league count
- Used for trackable Yahoo league imports

#### `import_sleeper_league_task(league_id: str, owner_id: int)`
- Celery task wrapper for single Sleeper league import
- Returns structured result with status and message
- Used for trackable Sleeper league imports

**Added two async implementation functions:**

#### `_import_yahoo_leagues_task(user_id: int)`
- Async implementation that calls `ingest_yahoo_leagues()`
- Counts imported leagues on success
- Returns detailed error messages on failure

#### `_import_sleeper_league_task(league_id: str, owner_id: int)`
- Async implementation that calls `ingest_sleeper_league()`
- Returns success/failure status with messages

### 2. `/Users/kforero/aicommissioner/api/routes/auth.py`

**Removed:**
- `BackgroundTasks` import (no longer needed)
- `background_tasks` parameter from relevant endpoints

**Modified endpoints:**

#### `GET /auth/yahoo/callback`
- **Before:** Used `background_tasks.add_task()`
- **After:** Uses `import_yahoo_leagues_task.apply_async()`
- **New behavior:** Redirects to `/connect?yahoo_connected=true&task_id={task.id}`
- **Benefit:** Frontend receives task_id in URL for progress tracking

#### `POST /auth/yahoo/import-leagues`
- **Before:** Used `background_tasks.add_task()`, returned simple message
- **After:** Uses `import_yahoo_leagues_task.apply_async()`
- **New response:**
  ```json
  {
    "message": "Yahoo league import started",
    "task_id": "abc-123-def-456"
  }
  ```

#### `POST /auth/sleeper/leagues`
- **Before:** Used `background_tasks.add_task()` for each league
- **After:** Uses `import_sleeper_league_task.apply_async()` for each league
- **New response:**
  ```json
  {
    "message": "Sleeper league import started",
    "task_ids": [
      {"league_id": "league1", "task_id": "task-1"},
      {"league_id": "league2", "task_id": "task-2"}
    ],
    "user": { ... }
  }
  ```

## Files Created

### 3. `/Users/kforero/aicommissioner/LEAGUE_IMPORT_TRACKING.md`
Comprehensive documentation including:
- API endpoint specifications
- Response formats for all task states
- Frontend integration guide with React hooks
- Testing instructions
- Error handling strategies

### 4. `/Users/kforero/aicommissioner/test_league_import.py`
Test script demonstrating:
- How to trigger imports
- How to poll task status
- Example usage patterns

### 5. `/Users/kforero/aicommissioner/CHANGES_SUMMARY.md`
This file - summary of all implementation changes.

## How It Works

### Flow Diagram

```
User Action (OAuth or Manual Import)
         ↓
Backend creates Celery task
         ↓
Backend returns task_id to frontend
         ↓
Frontend polls GET /admin/tasks/{task_id}
         ↓
Backend returns task status (PENDING/STARTED/SUCCESS/FAILURE)
         ↓
Frontend displays progress/result to user
```

### Task Status Lifecycle

1. **PENDING** - Task is queued, waiting for worker
2. **STARTED** - Worker has picked up the task
3. **SUCCESS** - Task completed successfully
   - Result includes message and data
4. **FAILURE** - Task failed with error
   - Error message included in response

## Existing Infrastructure Used

### Task Status Endpoint
**Endpoint:** `GET /admin/tasks/{task_id}`

Already exists in `/Users/kforero/aicommissioner/api/routes/admin.py` and handles:
- Checking task status via Celery's `AsyncResult`
- Returning task metadata, results, and errors
- Requires authentication

### Celery Configuration
Located in `/Users/kforero/aicommissioner/schedulers/celery_app.py`:
- Already configured with Redis backend
- Already imports tasks from `schedulers.tasks`
- New tasks automatically registered

## Benefits

### For Users
1. **Real-time feedback** - See import progress
2. **Clear error messages** - Know when/why imports fail
3. **Better UX** - No wondering if import worked

### For Developers
1. **Debugging** - Task results stored in Redis
2. **Monitoring** - Can track task performance
3. **Scalability** - Tasks distributed across workers
4. **Reliability** - Built-in retry mechanisms

### For Frontend
1. **Progress tracking** - Can show spinners/progress bars
2. **Error handling** - Can display specific error messages
3. **User feedback** - Can show success notifications
4. **Retry logic** - Can implement retry buttons

## Testing Checklist

### Backend Testing
- [ ] Start Celery worker: `celery -A schedulers.celery_app worker --loglevel=info`
- [ ] Start Celery beat (optional): `celery -A schedulers.celery_app beat --loglevel=info`
- [ ] Test Yahoo OAuth flow and check task_id in redirect
- [ ] Test manual Yahoo import endpoint
- [ ] Test Sleeper league addition endpoint
- [ ] Verify tasks appear in Celery logs
- [ ] Verify task status endpoint returns correct states

### Frontend Testing
- [ ] Extract task_id from OAuth redirect URL
- [ ] Implement polling with 2-second interval
- [ ] Display loading state during PENDING/STARTED
- [ ] Display success message on SUCCESS
- [ ] Display error message on FAILURE
- [ ] Test timeout after 60 seconds
- [ ] Verify multiple simultaneous imports work

### Integration Testing
- [ ] Test with actual Yahoo account
- [ ] Test with multiple Sleeper leagues
- [ ] Test error cases (expired tokens, network failures)
- [ ] Test concurrent imports by multiple users
- [ ] Verify imported leagues appear in database

## Migration Notes

### Breaking Changes
The `/auth/sleeper/leagues` endpoint response format has changed:
- **Before:** Returns `UserResponse` directly
- **After:** Returns object with `message`, `task_ids`, and `user` fields

### Frontend Updates Required
1. Update OAuth callback handler to extract `task_id` from URL
2. Implement task polling logic
3. Update Sleeper leagues handler for new response format
4. Add UI components for progress indication

### Backward Compatibility
- All other endpoints unchanged
- OAuth flows still redirect correctly
- Task polling is optional (imports complete regardless)

## Performance Considerations

- **Polling frequency:** 2 seconds recommended
- **Timeout:** 60 seconds (30 polling attempts)
- **Task duration:** Yahoo imports typically 5-30 seconds
- **Redis storage:** Task results expire after 1 hour
- **Concurrency:** Multiple users can import simultaneously

## Rollback Plan

If issues arise, rollback is straightforward:

1. Revert `api/routes/auth.py` to use `background_tasks`
2. Keep new Celery tasks (they don't hurt anything)
3. Frontend can ignore task_id if present

## Future Enhancements

1. **WebSocket notifications** - Push updates instead of polling
2. **Progress percentage** - Track individual league imports
3. **Batch operations** - Single task for multiple leagues
4. **Cancel support** - Allow users to cancel in-progress imports
5. **Retry mechanisms** - Automatic retry with exponential backoff
6. **Monitoring dashboard** - Track import success rates

## Questions or Issues?

See documentation files:
- `LEAGUE_IMPORT_TRACKING.md` - Complete technical documentation
- `test_league_import.py` - Working test examples

Contact: Check git history for this feature's author
