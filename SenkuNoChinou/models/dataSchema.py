from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class Todo(Document):
    task: str
    priority: str = "medium"
    due_date: str = ""
    due_time: str = ""
    note: str = ""
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Settings:
        name = "todos"


class Event(Document):
    title: str
    event_datetime: datetime
    notes: str = ""
    status: str = "scheduled"
    reminder_sent: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Settings:
        name = "events"


class JournalEntry(Document):
    title: str = ""
    content: str
    mood: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "journal"
