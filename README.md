# DoNotMiss Flask Backend

Simple Flask backend for the DoNotMiss Chrome extension, mirroring the task model used by the Forge app.

## Setup

1. Create and activate a virtual environment (recommended):

```bash
cd donotmiss_backend
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the development server:

```bash
python run.py
```

The API will be available at:

- `http://localhost:5000/health`
- `http://localhost:5000/api/tasks`

## API Overview

All API routes are prefixed with `/api`.

### `GET /api/tasks`

Return all tasks. Optional query parameter `status` to filter:

- `pending`
- `sent`

### `POST /api/tasks`

Create a new task.

Example JSON body:

```json
{
  "text": "Finish API documentation",
  "source": "web",
  "url": "https://example.com",
  "priority": "high"
}
```

Fields:

- `text` (string, required)
- `source` (string, optional, default `web`)
- `url` (string, optional)
- `priority` (string, optional, default `medium`)
- `title`, `description`, `status`, `createdAt`, `metadata` (optional)

### `POST /api/tasks/{id}/send`

Marks a task as sent and sets `sentAt`.

### `DELETE /api/tasks/{id}`

Deletes a task.

## Chrome Extension Integration

Point the extension's backend endpoint to this Flask server.

In `donotmiss-extension/background.js`, replace the backend URL with:

```javascript
const endpoint = 'http://localhost:5000/api/tasks';
```

Then, update the extension's fetch/POST logic to send tasks to this endpoint instead of the Forge URL.

> Note: This backend currently stores tasks in memory only. Restarting the server will clear all data. For production, replace the in-memory store with a database (e.g., SQLite, Postgres) and add authentication.
