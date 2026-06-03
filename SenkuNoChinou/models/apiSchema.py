from pydantic import BaseModel


class RespondRequest(BaseModel):
    query: str
    thread_id: str


class RespondResponse(BaseModel):
    response: str


class CreateThreadResponse(BaseModel):
    thread_id: str


class TranscribeResponse(BaseModel):
    text: str


class SttRespondResponse(BaseModel):
    transcript: str
    response: str
