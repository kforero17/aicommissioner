# LLM Error Handling System Documentation

## Overview

This fantasy sports recap generator now includes a production-grade LLM error handling system with robust reliability features to ensure recaps are always delivered, even when AI services experience issues.

## Key Features

### 1. Timeout Handling
- **Default timeout**: 30 seconds for all LLM API calls
- Prevents indefinite waiting when APIs are slow or unresponsive
- Automatically falls back to deterministic rendering on timeout

### 2. Smart Retry Logic
- **One retry** for transient errors only
- **Exponential backoff**: 2 seconds between retries
- **Transient errors** (retried):
  - Network timeouts
  - Connection errors
  - Rate limits (429)
  - Service unavailable (503)
  - Internal server errors (500, 502)
- **Permanent errors** (not retried):
  - Authentication errors (401)
  - Invalid requests (400)
  - Context length exceeded

### 3. Circuit Breaker Pattern
- **Per-provider tracking**: Separate circuit breakers for OpenAI and Anthropic
- **Failure threshold**: 5 failures within 10-minute window
- **Auto-recovery**: 30-minute cooldown before retry
- **States**:
  - `CLOSED`: Normal operation
  - `OPEN`: Too many failures, block requests
  - `HALF_OPEN`: Testing recovery after cooldown

### 4. Deterministic Fallback
- Always available as a backup
- Uses existing deterministic rendering methods
- Same output schema as LLM-generated recaps
- Zero cost, instant response

### 5. Comprehensive Logging
All LLM attempts are logged with structured data:
- Attempt mode: "attempted", "skipped", "failed", "success"
- Error classification when failures occur
- Provider and latency for successful calls
- Circuit breaker state changes
- Uses Python's `logging` module with structured extra fields

## Architecture

### Core Components

#### 1. `RecapResult` Dataclass
```python
@dataclass
class RecapResult:
    text: str                      # Generated recap text
    mode: RecapMode                # "llm" | "deterministic" | "circuit_open"
    warnings: List[str]            # Warning messages for monitoring
    provider: Optional[str]        # "openai" | "anthropic" | None
    latency_ms: Optional[int]      # Generation latency in milliseconds
```

#### 2. `CircuitBreaker` Class
Tracks failures over time and manages circuit state:
- Maintains a sliding window of failures (10 minutes)
- Opens circuit after threshold is exceeded (5 failures)
- Auto-recovers after cooldown period (30 minutes)
- Provides status for monitoring dashboards

#### 3. `ErrorClassifier` Class
Classifies errors as transient or permanent:
- Analyzes exception types and status codes
- Determines retry eligibility
- Supports both OpenAI and Anthropic error formats

#### 4. `LLMHandler` Class
Orchestrates the entire error handling flow:
- Checks circuit breaker before attempting LLM calls
- Enforces timeouts on API calls
- Implements retry logic for transient errors
- Records failures and successes with circuit breaker
- Falls back to deterministic rendering when needed
- Provides comprehensive logging

### File Structure

```
ai_text/
├── llm_handler.py          # New: Core error handling logic
├── text_formatter.py       # Updated: Uses LLMHandler
└── summary_generator.py    # Unchanged: Data structures

services/
└── recap_service.py        # Updated: Logs warnings and metadata

test_llm_handler.py         # Test suite for error handling
```

## Usage

### Basic Usage (New Method)

```python
from ai_text.text_formatter import TextFormatter

formatter = TextFormatter()

# Generate recap with full error handling
result = await formatter.generate_recap(
    summary=weekly_summary,
    style="standard",
    persona="witty",
    provider="openai"
)

# Access the text
recap_text = result.text

# Check metadata
print(f"Mode: {result.mode}")              # llm, deterministic, or circuit_open
print(f"Provider: {result.provider}")      # openai, anthropic, or None
print(f"Latency: {result.latency_ms}ms")   # Response time
print(f"Warnings: {result.warnings}")      # Any warnings

# Log warnings for monitoring
for warning in result.warnings:
    logger.warning(warning)
```

### Backward Compatible (Old Method)

```python
# Still works, now uses LLMHandler internally
recap_text = await formatter.render_llm(
    summary=weekly_summary,
    style="standard",
    persona="witty",
    provider="openai"
)
```

### Circuit Breaker Monitoring

```python
# Get circuit breaker status for all providers
status = formatter.get_circuit_status()

# Example output:
# {
#     "openai": {
#         "provider": "openai",
#         "state": "closed",
#         "failure_count": 2,
#         "opened_at": None
#     },
#     "anthropic": {
#         "provider": "anthropic",
#         "state": "open",
#         "failure_count": 5,
#         "opened_at": "2024-01-24T20:30:00"
#     }
# }
```

## Configuration

### Circuit Breaker Settings

In `ai_text/llm_handler.py`:

```python
class CircuitBreaker:
    FAILURE_THRESHOLD = 5          # Open circuit after 5 failures
    FAILURE_WINDOW_MINUTES = 10    # In 10-minute window
    COOLDOWN_MINUTES = 30          # Auto-recover after 30 minutes
```

### LLM Call Settings

```python
class LLMHandler:
    DEFAULT_TIMEOUT_SECONDS = 30   # Timeout for API calls
    RETRY_DELAY_SECONDS = 2        # Backoff between retries
    MAX_RETRIES = 1                # Retry once for transient errors
```

## Monitoring

### Key Metrics to Track

1. **Recap Generation Mode Distribution**
   - Percentage of LLM vs deterministic vs circuit_open
   - Target: >95% LLM success rate

2. **Circuit Breaker State**
   - Time spent in OPEN state per provider
   - Frequency of circuit opens
   - Target: <1% of time in OPEN state

3. **LLM Latency**
   - P50, P95, P99 latency for successful calls
   - Target: <5 seconds for P95

4. **Error Rates**
   - Rate of transient vs permanent errors
   - Most common error types
   - Target: <5% error rate

### Log Queries

All logs use structured logging with extra fields. Example queries:

**Find all circuit breaker opens:**
```python
# Filter logs where message contains "Circuit breaker OPENED"
```

**Track LLM success rate:**
```python
# Count where extra.llm_mode == "success" vs "failed"
```

**Monitor latency:**
```python
# Analyze extra.latency_ms for successful calls
```

## Error Scenarios and Behavior

| Scenario | Behavior | Mode | User Impact |
|----------|----------|------|-------------|
| OpenAI timeout | Retry once, then fallback | `deterministic` | Recap still delivered, no AI personality |
| Rate limit (429) | Retry once with backoff | `llm` or `deterministic` | May succeed on retry, or fallback |
| Auth error (401) | No retry, immediate fallback | `deterministic` | Recap delivered, logged for investigation |
| 5 failures in 10 min | Circuit opens | `circuit_open` | Deterministic for 30 min, with notice |
| Network issue | Retry once, then fallback | `deterministic` | Recap still delivered |
| Invalid API key | No retry, immediate fallback | `deterministic` | Logged for investigation |

## User Experience

### Normal Operation (LLM Success)
```
🏆 POWER RANKINGS - Fantasy League Week 10

[AI-generated witty recap with personality...]
```

### Circuit Breaker Open
```
⚠️ AI recap temporarily unavailable, showing standard recap:

🏆 POWER RANKINGS - Fantasy League Week 10

[Deterministic recap - clean and informative...]
```

Users are informed when circuit is open but still receive a complete recap.

## Testing

Run the test suite:

```bash
python3 test_llm_handler.py
```

Tests cover:
- Circuit breaker state transitions
- Error classification (transient vs permanent)
- Deterministic fallback
- Circuit breaker integration with LLM handler
- Logging output verification

## Operational Runbook

### Issue: Circuit Breaker Stuck Open

**Symptoms:**
- All recaps show "AI recap temporarily unavailable"
- Circuit status shows `state: "open"`

**Investigation:**
1. Check circuit status: `formatter.get_circuit_status()`
2. Review logs for error types causing failures
3. Verify API keys are valid
4. Check provider service status

**Resolution:**
- If API key invalid: Update environment variable, restart service
- If provider outage: Wait for auto-recovery (30 min) or increase cooldown
- If persistent issue: Disable LLM rendering temporarily

### Issue: High Latency

**Symptoms:**
- Recaps take >10 seconds to generate
- `latency_ms` consistently high in logs

**Investigation:**
1. Check provider API status
2. Review network connectivity
3. Analyze prompt complexity

**Resolution:**
- Reduce timeout if consistently timing out
- Switch providers (OpenAI ↔ Anthropic)
- Optimize prompts for faster generation

### Issue: Frequent Fallbacks

**Symptoms:**
- High percentage of `mode: "deterministic"`
- Many retry warnings in logs

**Investigation:**
1. Check error types in logs
2. Review rate limit quotas
3. Verify network stability

**Resolution:**
- If rate limits: Upgrade API plan or reduce frequency
- If network issues: Investigate infrastructure
- If API instability: Switch providers or increase timeout

## Future Enhancements

Potential improvements for the future:

1. **Metrics Export**: Export metrics to Prometheus/StatsD
2. **Adaptive Timeouts**: Adjust timeout based on historical latency
3. **Fallback Chain**: Try Anthropic if OpenAI fails (and vice versa)
4. **Circuit Breaker Persistence**: Share state across processes/servers
5. **Custom Error Handlers**: Per-league error handling strategies
6. **A/B Testing**: Compare LLM vs deterministic user engagement

## Dependencies

All dependencies are standard library or already in `requirements.txt`:
- `asyncio` (built-in)
- `logging` (built-in)
- `collections.deque` (built-in)
- `datetime` (built-in)
- `dataclasses` (built-in)
- `enum` (built-in)
- `openai` (existing)
- `anthropic` (existing)

No new external dependencies required.

## Success Criteria

✅ LLM calls have 30s timeout
✅ Transient errors retry once with 2s backoff
✅ Circuit breaker activates after 5 failures in 10 min
✅ Circuit breaker auto-recovers after 30 min
✅ Deterministic fallback always works
✅ RecapResult provides complete metadata
✅ All LLM attempts logged with structured data
✅ No breaking changes to existing deterministic rendering
✅ Code follows Python best practices (type hints, docstrings, clean structure)

All criteria have been met and verified with the test suite.
