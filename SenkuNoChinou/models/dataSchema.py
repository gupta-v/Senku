from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TodoItem(BaseModel):
    task: str
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    due_date: str  # "YYYY-MM-DD"
    due_time: str = ""  # "HH:MM" or empty
    status: Literal["pending", "done"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class CalendarEvent(BaseModel):
    title: str
    event_datetime: datetime
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reminder_sent: bool = False  # scheduler flips this after 15-min ntfy


class JournalEntry(BaseModel):
    content: str
    mood: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
