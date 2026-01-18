"""API routes for DoNotMiss backend."""
import json
from uuid import uuid4
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, abort

from .models import db, Task


bp = Blueprint("donotmiss_api", __name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Health & Status
# ============================================================

@bp.get("/health")
def health_check():
    """Health check endpoint to verify backend is awake."""
    return jsonify({"status": "ok", "timestamp": _now_iso()})


# ============================================================
# Task CRUD Operations
# ============================================================

@bp.get("/tasks")
def list_tasks():
    """Return all tasks.
    
    Optional query param `status` can filter tasks by status
    (e.g., pending, sent, declined).
    """
    status = request.args.get("status")
    
    query = Task.query.order_by(Task.created_at.desc())
    if status:
        query = query.filter(Task.status == status)
    
    tasks = query.all()
    return jsonify([task.to_dict() for task in tasks])


@bp.post("/tasks")
def create_task():
    """Create a new task from extension capture."""
    data = request.get_json(silent=True) or {}

    text = data.get("text") or data.get("description")
    if not text:
        abort(400, description="Missing required field: text or description")

    # Create task from data
    task = Task.from_dict({
        'id': data.get('id') or f"task-{uuid4()}",
        'title': data.get('title') or text[:80],
        'description': data.get('description') or text,
        'text': text,
        'source': data.get('source', 'web'),
        'url': data.get('url'),
        'priority': data.get('priority', 'medium'),
        'deadline': data.get('deadline'),
        'status': 'pending',
        'createdVia': 'extension',
        'metadata': data.get('metadata', {})
    })
    
    db.session.add(task)
    db.session.commit()
    
    return jsonify(task.to_dict()), 201


@bp.get("/tasks/<task_id>")
def get_task(task_id: str):
    """Get a single task by ID."""
    task = Task.query.get(task_id)
    if not task:
        abort(404, description="Task not found")
    return jsonify(task.to_dict())


@bp.put("/tasks/<task_id>")
def update_task(task_id: str):
    """Update a task."""
    task = Task.query.get(task_id)
    if not task:
        abort(404, description="Task not found")
    
    data = request.get_json(silent=True) or {}
    
    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'priority' in data:
        task.priority = data['priority']
    if 'deadline' in data:
        if data['deadline']:
            from datetime import date
            task.deadline = date.fromisoformat(data['deadline'].split('T')[0])
        else:
            task.deadline = None
    if 'status' in data:
        task.status = data['status']
    
    db.session.commit()
    return jsonify(task.to_dict())


@bp.delete("/tasks/<task_id>")
def delete_task(task_id: str):
    """Delete a task permanently."""
    task = Task.query.get(task_id)
    if not task:
        abort(404, description="Task not found")
    
    db.session.delete(task)
    db.session.commit()
    return "", 204


# ============================================================
# Task Status Operations (for Forge app)
# ============================================================

@bp.post("/tasks/<task_id>/mark-sent")
def mark_task_sent(task_id: str):
    """Mark a task as sent (called by Forge app after creating Jira issue)."""
    task = Task.query.get(task_id)
    if not task:
        abort(404, description="Task not found")
    
    data = request.get_json(silent=True) or {}
    
    task.status = "sent"
    task.sent_at = datetime.now(timezone.utc)
    if data.get("jiraKey"):
        task.jira_key = data["jiraKey"]
    if data.get("jiraUrl"):
        task.jira_url = data["jiraUrl"]
    
    db.session.commit()
    return jsonify(task.to_dict())


@bp.post("/tasks/<task_id>/decline")
def decline_task(task_id: str):
    """Mark a task as declined."""
    task = Task.query.get(task_id)
    if not task:
        abort(404, description="Task not found")
    
    task.status = "declined"
    task.declined_at = datetime.now(timezone.utc)
    
    db.session.commit()
    return jsonify(task.to_dict())


@bp.post("/tasks/<task_id>/restore")
def restore_task(task_id: str):
    """Restore a declined task back to pending."""
    task = Task.query.get(task_id)
    if not task:
        abort(404, description="Task not found")
    
    task.status = "pending"
    task.declined_at = None
    
    db.session.commit()
    return jsonify(task.to_dict())


# ============================================================
# Bulk Operations
# ============================================================

@bp.delete("/tasks")
def clear_all_tasks():
    """Delete all tasks (use with caution)."""
    Task.query.delete()
    db.session.commit()
    return jsonify({"success": True, "message": "All tasks deleted"})


@bp.get("/stats")
def get_stats():
    """Get task statistics."""
    pending_count = Task.query.filter(Task.status == 'pending').count()
    sent_count = Task.query.filter(Task.status == 'sent').count()
    declined_count = Task.query.filter(Task.status == 'declined').count()
    total_count = Task.query.count()
    
    return jsonify({
        "total": total_count,
        "pending": pending_count,
        "sent": sent_count,
        "declined": declined_count
    })
