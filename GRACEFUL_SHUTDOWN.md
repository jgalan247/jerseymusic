# Graceful Shutdown Handling

This document describes the graceful shutdown implementation for Jersey Events when deployed in containerized environments (Railway, Docker, Kubernetes, etc.).

## Overview

When a container orchestrator needs to stop or restart the application (for deployments, scaling, or maintenance), it sends a `SIGTERM` signal to the process. Without proper handling, this can result in:
- Aborted in-flight HTTP requests
- Unclosed database connections
- Lost transactions
- Poor user experience

Our implementation ensures graceful shutdown through **two complementary layers**:

1. **Gunicorn-level shutdown handling** (main layer)
2. **Django-level cleanup handlers** (backup/supplementary)

## Architecture

### Layer 1: Gunicorn Configuration

**File:** `gunicorn.conf.py`

Gunicorn handles the primary graceful shutdown logic:

```python
# Key timeout settings
timeout = 30              # Worker timeout for single request
graceful_timeout = 30     # Time to wait for workers after SIGTERM
keepalive = 2             # Keep-alive connection timeout

# Worker lifecycle
max_requests = 1000       # Restart workers periodically (memory leak prevention)
max_requests_jitter = 50  # Randomize restarts to avoid thundering herd
```

**Shutdown Flow:**
1. Container orchestrator sends `SIGTERM` to gunicorn master process
2. Gunicorn master stops accepting new connections
3. Existing worker processes finish handling current requests (up to `graceful_timeout`)
4. Workers shutdown cleanly
5. Master process exits

**Lifecycle Hooks:**
- `on_starting()`: Log master process initialization
- `when_ready()`: Log successful server start
- `worker_int()`: Handle worker SIGINT/SIGQUIT signals
- `worker_abort()`: Log worker timeout/abort events
- `worker_exit()`: Log worker shutdown
- `on_exit()`: Log master process exit

### Layer 2: Django Signal Handlers

**Files:**
- `events/shutdown_handlers.py` - Cleanup logic
- `events/apps.py` - Handler registration

Django-level handlers provide additional cleanup:

```python
def graceful_shutdown(signum, frame):
    """Main shutdown handler - cleans up Django resources"""
    log_shutdown()              # Log the shutdown event
    close_database_connections() # Close all DB connections
    clear_cache()               # Clear cache data
    sys.exit(0)
```

**Cleanup Tasks:**
1. **Database connections**: Explicitly close all connections from `django.db.connections`
2. **Cache**: Clear cache to prevent stale data
3. **Logging**: Record shutdown events for monitoring

**Registration:**
- Handlers registered in `EventsConfig.ready()` method
- Handles `SIGTERM` and `SIGINT` signals
- Backup `atexit` handler for normal Python exits

## Configuration

### Environment Variables

Control worker behavior via environment variables:

```bash
# Worker count (default: CPU count * 2 + 1)
WEB_CONCURRENCY=4

# Gunicorn log level (default: info)
GUNICORN_LOG_LEVEL=debug

# Port binding (Railway sets this automatically)
PORT=8000
```

### Worker Tuning

**Current defaults:**
- Workers: `multiprocessing.cpu_count() * 2 + 1`
- Worker class: `sync` (suitable for Django)
- Connections per worker: 1000
- Request timeout: 30s
- Graceful timeout: 30s

**For high-traffic sites, consider:**
- Increase `workers` for more parallelism
- Use `gevent` worker class for async I/O
- Adjust `timeout` based on slowest endpoint

## Testing Graceful Shutdown

### Local Testing

1. Start the development server:
```bash
./start.sh
```

2. In another terminal, send SIGTERM to the gunicorn process:
```bash
# Find the gunicorn master PID
ps aux | grep gunicorn

# Send SIGTERM
kill -TERM <PID>
```

3. Check logs for graceful shutdown messages:
```
[INFO] Worker 123 received SIGINT/SIGQUIT, gracefully shutting down...
[INFO] Closing database connection: default
[INFO] All database connections closed successfully
[INFO] Graceful shutdown complete, exiting...
```

### Container Testing (Railway)

Railway automatically sends `SIGTERM` during deployments. Monitor logs in Railway dashboard:

1. Deploy the application
2. Trigger a new deployment (push to branch)
3. Watch logs during the transition:
   - "Handling signal: term"
   - "Worker exiting (pid: X)"
   - "Shutting down: Master"

### Load Testing

Test graceful shutdown under load:

```bash
# Terminal 1: Start load test
ab -n 1000 -c 10 https://your-app.railway.app/

# Terminal 2: During the test, trigger a restart
# (In Railway: re-deploy or restart service)
```

Verify:
- No 502/503 errors during shutdown
- In-flight requests complete successfully
- Response times remain consistent

## Monitoring

### Logs to Watch

**Startup logs:**
```
🚀 Starting Jersey Music application...
📦 Running database migrations...
📦 Collecting static files...
🌐 Starting gunicorn web server with graceful shutdown handling...
[INFO] Gunicorn is ready. Listening on 0.0.0.0:8000 with 5 workers
[INFO] Jersey Events app initialized with shutdown handlers
```

**Shutdown logs:**
```
[INFO] Handling signal: term
[INFO] Worker 36 received SIGINT/SIGQUIT, gracefully shutting down...
[INFO] Closing database connection: default
[INFO] All database connections closed successfully
[INFO] Cache cleared successfully
[INFO] Graceful shutdown complete, exiting...
[INFO] Worker exiting (pid: 36)
[INFO] Shutting down: Master
```

### Health Checks

Ensure health check endpoints don't interfere with shutdown:
- Health checks should timeout quickly (< 5s)
- Load balancer should stop sending traffic before SIGTERM
- Grace period should exceed `graceful_timeout` (30s)

## Troubleshooting

### Workers Not Shutting Down

**Symptom:** Workers killed forcefully after timeout

**Solutions:**
1. Increase `graceful_timeout` in `gunicorn.conf.py`
2. Check for long-running requests (optimize or move to background tasks)
3. Review `timeout` setting - may be too long

### Database Connection Errors

**Symptom:** "connection already closed" errors during shutdown

**Solutions:**
1. Check that `CONN_MAX_AGE` is not set too high in Django settings
2. Ensure database connection pooling is properly configured
3. Review Django database connection settings

### 502 Errors During Deployment

**Symptom:** Users see 502 errors when deploying

**Solutions:**
1. Ensure Railway health checks are configured
2. Increase `graceful_timeout` to give more time for requests to complete
3. Use Railway's "Zero Downtime Deployments" feature if available
4. Consider implementing a maintenance mode page

### Memory Leaks

**Symptom:** Workers consuming increasing memory over time

**Solutions:**
1. `max_requests = 1000` is already set to recycle workers
2. Decrease `max_requests` to recycle workers more frequently
3. Profile the application to find memory leaks
4. Consider using `max_requests_jitter` to spread out restarts

## Production Considerations

### Railway-Specific

Railway automatically:
- Sets `PORT` environment variable
- Sends `SIGTERM` on deploy/restart
- Has 30-second default shutdown timeout
- Provides zero-downtime deployments (pro plan)

### Best Practices

1. **Log aggregation**: Send logs to external service (Sentry, Papertrail)
2. **Monitoring**: Track shutdown events and duration
3. **Alerts**: Alert on:
   - High worker timeout rates
   - Frequent forced kills
   - Database connection errors during shutdown
4. **Testing**: Include graceful shutdown in CI/CD tests
5. **Documentation**: Keep this document updated as configuration changes

## Related Files

- `gunicorn.conf.py` - Gunicorn configuration with shutdown settings
- `start.sh` - Startup script that launches gunicorn with config
- `events/apps.py` - Django app configuration for handler registration
- `events/shutdown_handlers.py` - Django-level cleanup handlers
- `events/settings.py` - Django settings (INSTALLED_APPS uses EventsConfig)
- `Procfile` - Railway/Heroku process definition

## References

- [Gunicorn Design](https://docs.gunicorn.org/en/stable/design.html)
- [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html)
- [Django Signals](https://docs.djangoproject.com/en/stable/topics/signals/)
- [Railway Deployments](https://docs.railway.app/deploy/deployments)
- [Linux Signals](https://man7.org/linux/man-pages/man7/signal.7.html)
