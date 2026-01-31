# Frontend Integration - League Import Progress Tracking

Quick reference for frontend developers implementing import progress tracking.

## TL;DR

1. Backend now returns `task_id` when triggering imports
2. Poll `GET /admin/tasks/{task_id}` to check status
3. Display progress based on task status (PENDING/STARTED/SUCCESS/FAILURE)

## API Changes

### Yahoo OAuth Callback
**What changed:** Redirect URL now includes `task_id`

```typescript
// Old redirect
/connect?yahoo_connected=true

// New redirect
/connect?yahoo_connected=true&task_id=abc-123-def-456
```

**Action needed:**
```typescript
// Extract task_id from URL
const searchParams = new URLSearchParams(window.location.search);
const taskId = searchParams.get('task_id');

if (taskId) {
  // Start polling
  pollTaskStatus(taskId);
}
```

### Manual Yahoo Import
**Endpoint:** `POST /auth/yahoo/import-leagues`

**Response changed:**
```typescript
// Old response
{ message: "Yahoo league import started" }

// New response
{
  message: "Yahoo league import started",
  task_id: "abc-123-def-456"
}
```

**Action needed:**
```typescript
const response = await fetch('/auth/yahoo/import-leagues', {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}` }
});

const { task_id } = await response.json();
pollTaskStatus(task_id);
```

### Sleeper Leagues
**Endpoint:** `POST /auth/sleeper/leagues`

**Response changed significantly:**
```typescript
// Old response
{
  id: 1,
  username: "user",
  sleeper_leagues: ["league1", "league2"],
  ...
}

// New response
{
  message: "Sleeper league import started",
  task_ids: [
    { league_id: "league1", task_id: "task-1" },
    { league_id: "league2", task_id: "task-2" }
  ],
  user: {
    id: 1,
    username: "user",
    sleeper_leagues: ["league1", "league2"],
    ...
  }
}
```

**Action needed:**
```typescript
const response = await fetch('/auth/sleeper/leagues', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ league_ids: ["league1", "league2"] })
});

const { task_ids, user } = await response.json();

// Poll each task
task_ids.forEach(({ league_id, task_id }) => {
  pollTaskStatus(task_id, league_id);
});
```

## Polling Implementation

### Simple Polling Function

```typescript
async function pollTaskStatus(
  taskId: string,
  onUpdate: (status: TaskStatus) => void
): Promise<void> {
  const maxAttempts = 30;
  const interval = 2000; // 2 seconds

  for (let i = 0; i < maxAttempts; i++) {
    const response = await fetch(`/admin/tasks/${taskId}`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });

    const status: TaskStatus = await response.json();
    onUpdate(status);

    // Stop if complete
    if (status.status === 'SUCCESS' || status.status === 'FAILURE') {
      return;
    }

    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  // Timeout
  onUpdate({ task_id: taskId, status: 'TIMEOUT' });
}
```

### React Hook (Recommended)

```typescript
import { useState, useEffect, useRef } from 'react';

interface TaskStatus {
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE';
  result?: {
    status: string;
    message: string;
    league_count?: number;
  };
  error?: string;
}

export function useTaskPolling(taskId: string | null) {
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!taskId) return;

    setIsPolling(true);
    let attempts = 0;
    const maxAttempts = 30;

    const poll = async () => {
      try {
        const res = await fetch(`/admin/tasks/${taskId}`, {
          headers: { Authorization: `Bearer ${getToken()}` }
        });

        const data: TaskStatus = await res.json();
        setStatus(data);

        // Stop polling if complete or max attempts reached
        if (
          data.status === 'SUCCESS' ||
          data.status === 'FAILURE' ||
          ++attempts >= maxAttempts
        ) {
          setIsPolling(false);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
        setIsPolling(false);
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      }
    };

    // Poll immediately, then every 2 seconds
    poll();
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [taskId]);

  return { status, isPolling };
}
```

## UI Components

### Loading State

```typescript
function ImportProgress({ taskId }: { taskId: string }) {
  const { status, isPolling } = useTaskPolling(taskId);

  if (!status) {
    return <Spinner />;
  }

  if (isPolling) {
    return (
      <div className="flex items-center gap-2">
        <Spinner className="h-4 w-4" />
        <span>Importing leagues...</span>
      </div>
    );
  }

  if (status.status === 'SUCCESS') {
    return (
      <div className="text-green-600 flex items-center gap-2">
        <CheckIcon className="h-5 w-5" />
        <span>{status.result?.message}</span>
      </div>
    );
  }

  if (status.status === 'FAILURE') {
    return (
      <div className="text-red-600 flex items-center gap-2">
        <XIcon className="h-5 w-5" />
        <span>{status.error || 'Import failed'}</span>
      </div>
    );
  }

  return null;
}
```

### Multiple Tasks (Sleeper)

```typescript
function MultipleImportProgress({ taskIds }: { taskIds: TaskIdMapping[] }) {
  return (
    <div className="space-y-2">
      {taskIds.map(({ league_id, task_id }) => (
        <div key={task_id} className="flex items-center justify-between">
          <span className="text-sm text-gray-600">League {league_id}</span>
          <ImportProgress taskId={task_id} />
        </div>
      ))}
    </div>
  );
}
```

### Toast Notifications

```typescript
function useImportWithToast() {
  const { toast } = useToast();

  const importYahooLeagues = async () => {
    const res = await fetch('/auth/yahoo/import-leagues', {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` }
    });

    const { task_id, message } = await res.json();

    toast({
      title: 'Import Started',
      description: message
    });

    // Poll in background
    pollTaskStatus(task_id, (status) => {
      if (status.status === 'SUCCESS') {
        toast({
          title: 'Success',
          description: status.result?.message,
          variant: 'success'
        });
      } else if (status.status === 'FAILURE') {
        toast({
          title: 'Import Failed',
          description: status.error,
          variant: 'destructive'
        });
      }
    });
  };

  return { importYahooLeagues };
}
```

## Task Status Reference

### PENDING
```json
{
  "task_id": "abc-123",
  "status": "PENDING"
}
```
**UI:** Show spinner with "Queued..." or "Starting..."

### STARTED
```json
{
  "task_id": "abc-123",
  "status": "STARTED"
}
```
**UI:** Show spinner with "Importing leagues..."

### SUCCESS
```json
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "result": {
    "status": "success",
    "message": "Successfully imported 3 Yahoo league(s)",
    "league_count": 3
  }
}
```
**UI:** Show success icon with result message

### FAILURE
```json
{
  "task_id": "abc-123",
  "status": "FAILURE",
  "error": "Failed to import Yahoo leagues - check user credentials"
}
```
**UI:** Show error icon with error message and retry button

## Error Handling

### Common Errors

1. **Token expired**
   ```typescript
   if (status.error?.includes('credentials')) {
     // Prompt re-authentication
     redirectToYahooAuth();
   }
   ```

2. **Network timeout**
   ```typescript
   if (!response.ok) {
     // Show generic error with retry
     showRetryButton();
   }
   ```

3. **Task timeout (60s)**
   ```typescript
   if (attempts >= maxAttempts) {
     // Show timeout message
     toast({
       title: 'Import taking longer than expected',
       description: 'Check back in a few minutes',
       action: <RefreshButton />
     });
   }
   ```

## Testing

### Test with Mock Data

```typescript
// Mock successful import
const mockSuccess: TaskStatus = {
  task_id: 'test-123',
  status: 'SUCCESS',
  result: {
    status: 'success',
    message: 'Successfully imported 3 Yahoo league(s)',
    league_count: 3
  }
};

// Mock failure
const mockFailure: TaskStatus = {
  task_id: 'test-123',
  status: 'FAILURE',
  error: 'Token expired'
};

// Test component with mock
<ImportProgress taskId="test-123" mockStatus={mockSuccess} />
```

### Manual Testing Steps

1. Login with Yahoo
2. Check that task_id appears in redirect URL
3. Verify polling starts automatically
4. Watch for status changes (PENDING → STARTED → SUCCESS)
5. Verify success message displays
6. Check that imported leagues appear in UI

## Performance Tips

1. **Debounce rapid imports** - Prevent users from spamming import button
2. **Cache results** - Store task status to avoid unnecessary re-polls
3. **Cleanup intervals** - Always clear intervals on unmount
4. **Batch UI updates** - Use React.memo to prevent unnecessary re-renders
5. **Background polling** - Move to service worker for better UX

## Migration Checklist

- [ ] Update OAuth callback to handle `task_id` query param
- [ ] Implement task polling hook
- [ ] Update manual import handlers
- [ ] Update Sleeper leagues handler for new response format
- [ ] Add UI components for progress indication
- [ ] Add error handling and retry logic
- [ ] Test with real Yahoo/Sleeper accounts
- [ ] Update any E2E tests

## Need Help?

See complete documentation:
- `LEAGUE_IMPORT_TRACKING.md` - Full technical docs
- `test_league_import.py` - Backend test examples
- `CHANGES_SUMMARY.md` - Implementation overview
