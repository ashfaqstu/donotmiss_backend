import os
from uuid import uuid4
from datetime import datetime, timezone

import requests
from flask import Blueprint, jsonify, request, abort


bp = Blueprint("donotmiss_api", __name__)

# In-memory task store for now. In real usage, replace with DB.
_TASKS = {}

# Jira configuration from environment variables
JIRA_SITE = os.environ.get("JIRA_SITE")  # e.g., "ahammadshawki8.atlassian.net"
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")  # Your Atlassian account email
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")  # API token from id.atlassian.com
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "DNM")  # Default project key


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_jira_auth():
    """Return auth tuple for Jira API requests."""
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        return None
    return (JIRA_EMAIL, JIRA_API_TOKEN)


def _create_jira_issue(task):
    """Create a Jira issue from a task. Returns issue key or None."""
    if not JIRA_SITE or not _get_jira_auth():
        return None, "Jira credentials not configured"
    
    # Map priority
    priority_map = {
        "highest": "1",
        "high": "2", 
        "medium": "3",
        "low": "4",
        "lowest": "5"
    }
    
    # Build issue payload
    issue_data = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": task.get("title", task.get("text", "")[:80]),
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": task.get("description") or task.get("text", "")}]
                    },
                    {
                        "type": "paragraph", 
                        "content": [
                            {"type": "text", "text": f"📍 Source: {task.get('source', 'web').upper()}"},
                        ]
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": f"🔗 URL: {task.get('url', 'N/A')}"}
                        ]
                    },
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "✨ Created via DoNotMiss"}]
                    }
                ]
            },
            "issuetype": {"name": "Task"},
            "priority": {"id": priority_map.get(task.get("priority", "medium"), "3")},
            "labels": ["donotmiss", f"source-{task.get('source', 'web')}"]
        }
    }
    
    # Add due date if deadline exists
    if task.get("deadline"):
        issue_data["fields"]["duedate"] = task["deadline"]
    
    try:
        response = requests.post(
            f"https://{JIRA_SITE}/rest/api/3/issue",
            json=issue_data,
            auth=_get_jira_auth(),
            headers={"Content-Type": "application/json"}
        )
        
        if response.ok:
            result = response.json()
            return result.get("key"), None
        else:
            error_msg = response.json().get("errorMessages", [response.text])
            return None, str(error_msg)
    except Exception as e:
        return None, str(e)


@bp.get("/health")
def health_check():
    """Health check endpoint to verify backend is awake."""
    return jsonify({"status": "ok", "timestamp": _now_iso()})


@bp.get("/tasks")
def list_tasks():
    """Return all tasks.

    Optional query param `status` can filter tasks by status
    (e.g., pending, sent, deleted).
    """
    status = request.args.get("status")
    tasks = list(_TASKS.values())
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    return jsonify(tasks)


@bp.post("/tasks")
def create_task():
    data = request.get_json(silent=True) or {}

    text = data.get("text")
    if not text:
        abort(400, description="Missing required field: text")

    task_id = data.get("id") or f"task-{uuid4()}"

    task = {
        "id": task_id,
        "title": data.get("title") or text[:80],
        "description": data.get("description") or text,
        "text": text,
        "source": data.get("source") or "web",
        "url": data.get("url"),
        "priority": data.get("priority") or "medium",
        "status": data.get("status") or "pending",
        "createdAt": data.get("createdAt") or _now_iso(),
        "createdVia": "donotmiss-flask",
        "metadata": data.get("metadata") or {},
    }

    _TASKS[task_id] = task
    return jsonify(task), 201


@bp.post("/tasks/<task_id>/send")
def send_task(task_id: str):
    """Send a task to Jira by creating an issue."""
    task = _TASKS.get(task_id)
    if not task:
        abort(404, description="Task not found")

    # Create Jira issue
    jira_key, error = _create_jira_issue(task)
    
    if jira_key:
        task["status"] = "sent"
        task["sentAt"] = _now_iso()
        task["jiraKey"] = jira_key
        task["jiraUrl"] = f"https://{JIRA_SITE}/browse/{jira_key}"
        return jsonify(task)
    else:
        return jsonify({"error": error or "Failed to create Jira issue"}), 500


@bp.post("/tasks/<task_id>/send-to-jira")
def send_task_to_jira(task_id: str):
    """Alternative endpoint - send existing task to Jira."""
    return send_task(task_id)


@bp.post("/tasks/create-and-send")
def create_and_send_task():
    """Create a task and immediately send it to Jira."""
    data = request.get_json(silent=True) or {}

    text = data.get("text") or data.get("description")
    if not text:
        abort(400, description="Missing required field: text or description")

    task_id = data.get("id") or f"task-{uuid4()}"

    task = {
        "id": task_id,
        "title": data.get("title") or text[:80],
        "description": data.get("description") or text,
        "text": text,
        "source": data.get("source") or "web",
        "url": data.get("url"),
        "priority": data.get("priority") or "medium",
        "deadline": data.get("deadline"),
        "status": "pending",
        "createdAt": data.get("createdAt") or _now_iso(),
        "createdVia": "donotmiss-extension",
        "metadata": data.get("metadata") or {},
    }

    # Create Jira issue immediately
    jira_key, error = _create_jira_issue(task)
    
    if jira_key:
        task["status"] = "sent"
        task["sentAt"] = _now_iso()
        task["jiraKey"] = jira_key
        task["jiraUrl"] = f"https://{JIRA_SITE}/browse/{jira_key}"
        _TASKS[task_id] = task
        return jsonify(task), 201
    else:
        # Store task anyway but mark as failed
        task["status"] = "failed"
        task["error"] = error
        _TASKS[task_id] = task
        return jsonify({"error": error or "Failed to create Jira issue", "task": task}), 500


@bp.get("/jira/status")
def jira_status():
    """Check if Jira integration is configured."""
    configured = bool(JIRA_SITE and JIRA_EMAIL and JIRA_API_TOKEN)
    return jsonify({
        "configured": configured,
        "site": JIRA_SITE if configured else None,
        "project": JIRA_PROJECT_KEY if configured else None
    })


@bp.delete("/tasks/<task_id>")
def delete_task(task_id: str):
    """Delete a task from the store."""
    task = _TASKS.pop(task_id, None)
    if not task:
        abort(404, description="Task not found")
    return "", 204
