"""Database models for DoNotMiss backend."""
import os
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Task(db.Model):
    """Task model for storing captured tasks."""
    __tablename__ = 'tasks'
    
    id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    text = db.Column(db.Text)
    source = db.Column(db.String(50), default='web')
    url = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, sent, declined
    jira_key = db.Column(db.String(50), nullable=True)
    jira_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at = db.Column(db.DateTime, nullable=True)
    declined_at = db.Column(db.DateTime, nullable=True)
    created_via = db.Column(db.String(50), default='extension')
    metadata_json = db.Column(db.Text, default='{}')
    
    def to_dict(self):
        """Convert task to dictionary for JSON serialization."""
        import json
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'text': self.text,
            'source': self.source,
            'url': self.url,
            'priority': self.priority,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'status': self.status,
            'jiraKey': self.jira_key,
            'jiraUrl': self.jira_url,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'sentAt': self.sent_at.isoformat() if self.sent_at else None,
            'declinedAt': self.declined_at.isoformat() if self.declined_at else None,
            'createdVia': self.created_via,
            'metadata': json.loads(self.metadata_json) if self.metadata_json else {}
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create task from dictionary."""
        import json
        from uuid import uuid4
        from datetime import date
        
        task = cls(
            id=data.get('id') or f"task-{uuid4()}",
            title=data.get('title') or (data.get('text', '')[:80] if data.get('text') else 'Untitled'),
            description=data.get('description') or data.get('text', ''),
            text=data.get('text', ''),
            source=data.get('source', 'web'),
            url=data.get('url'),
            priority=data.get('priority', 'medium'),
            status=data.get('status', 'pending'),
            created_via=data.get('createdVia', 'extension'),
            metadata_json=json.dumps(data.get('metadata', {}))
        )
        
        # Handle deadline
        if data.get('deadline'):
            if isinstance(data['deadline'], str):
                task.deadline = date.fromisoformat(data['deadline'].split('T')[0])
            else:
                task.deadline = data['deadline']
        
        return task
