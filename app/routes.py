from uuid import uuid4
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, abort


bp = Blueprint("donotmiss_api", __name__)

# In-memory task store for now. In real usage, replace with DB.
_TASKS = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    """Placeholder endpoint to 'send' a task to Jira.

    For now, this only flips the `status` to `sent` and
    records a `sentAt` timestamp. Integrate with Jira REST
    API here in the future.
    """
    task = _TASKS.get(task_id)
    if not task:
        abort(404, description="Task not found")

    task["status"] = "sent"
    task["sentAt"] = _now_iso()

    return jsonify(task)


@bp.delete("/tasks/<task_id>")
def delete_task(task_id: str):
    """Delete a task from the store."""
    task = _TASKS.pop(task_id, None)
    if not task:
        abort(404, description="Task not found")
    return "", 204
