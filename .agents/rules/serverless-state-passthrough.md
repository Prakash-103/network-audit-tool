# Serverless State Passthrough Rule

## When This Applies
Any FastAPI/Flask application deployed to stateless serverless platforms (Netlify Functions, Vercel Serverless Functions, AWS Lambda, Google Cloud Functions).

## Core Principle
**Never rely on server-side in-memory state for operations that depend on user-created data.**

On serverless platforms, each request may be handled by a different container instance with no shared memory. The browser is the single source of truth.

## Mandatory Patterns

### 1. Client → Server: Always Send State
Every API call that reads or modifies project/device/task state MUST include the full client state in the request body:
```js
body: JSON.stringify({
    ...params,
    project_state: currentState  // Always include
})
```

### 2. Server → Client: Always Return State
Every API response that modifies state MUST return the updated state:
```python
return {
    "status": "completed",
    ...results,
    "project_state": active_state.dict()  # Always return
}
```

### 3. Client Adoption: Never Fetch Separately
After receiving a response with `project_state`, adopt it directly — do NOT call `GET /api/state` on a separate (potentially different) serverless instance:
```js
if (data.project_state) {
    currentState = data.project_state;
} else {
    // Fallback only for local/persistent servers
    const sRes = await fetch('/api/state');
    currentState = await sRes.json();
}
```

### 4. Backend Parsing: Accept and Normalize
Use a shared `parse_client_state()` helper to deserialize, normalize enums, and validate the client payload:
```python
active_state = parse_client_state(req.project_state) if req.project_state else project_state
```

### 5. Serverless Detection
Detect serverless environments and run operations synchronously (no background threads):
```python
is_serverless = any(os.getenv(v) for v in [
    "VERCEL", "VERCEL_ENV", "NETLIFY",
    "AWS_LAMBDA_FUNCTION_NAME", "LAMBDA_TASK_ROOT"
])
```

## Checklist for New Endpoints
- [ ] Does the endpoint accept `project_state` in the request body?
- [ ] Does the endpoint return `project_state` in the response?
- [ ] Does the frontend send `currentState` in the request?
- [ ] Does the frontend adopt `data.project_state` from the response?
- [ ] Does the endpoint run synchronously on serverless (no background threads)?
