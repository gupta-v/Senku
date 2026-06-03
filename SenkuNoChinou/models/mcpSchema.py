from typing import Annotated, Literal, TypedDict
from pydantic import BaseModel, BeforeValidator, Field

# coerce "5" → 5 for LLMs that stringify numbers
CoerceInt = Annotated[int, BeforeValidator(lambda v: int(v))]


# ------ WikiPedia Schemas ------

class WikiDocument(TypedDict):
    page_content: str
    url: str


# --- MCP Tool I/O Schemas ---

class WikipediaInput(BaseModel):
    question: str = Field(..., description="The natural-language question to answer.")


class WikipediaOutput(BaseModel):
    answer: str = Field(..., description="Grounded answer synthesised from Wikipedia content.")


# ------ Tavily Schemas ------

class TavilySearchInput(BaseModel):
    query: str = Field(..., description="Search query.")
    max_results: int = Field(5, description="Maximum number of results to return.")
    topic: Literal["general", "news", "finance"] = Field("general", description="Search topic category.")
    include_raw_content: bool = Field(False, description="Include raw page content in results.")


# ------ Jina Reader Schemas ------

class JinaReaderInput(BaseModel):
    url: str = Field(..., description="URL to fetch and convert to clean markdown.")
    with_links: bool = Field(False, description="Append a links summary at the end of the content.")
    with_images: bool = Field(False, description="Append an images summary at the end of the content.")


# ------ Datetime Schemas ------

class DatetimeInput(BaseModel):
    timezone: str = Field("Asia/Kolkata", description="Timezone name (e.g. Asia/Kolkata, UTC, America/New_York).")


# ------ Weather Schemas ------

class WeatherInput(BaseModel):
    location: str = Field(..., description="City name or location (e.g. Mumbai, Delhi, London).")
    days: int = Field(1, description="Number of forecast days (1-3). 1 = current only.")


# ------ Ntfy Notification Schemas ------

class NtfyInput(BaseModel):
    message: str = Field(..., description="Notification body text.")
    title: str = Field("Senku", description="Notification title.")
    priority: Literal[1, 2, 3, 4, 5] = Field(3, description="Priority: 1=min, 2=low, 3=default, 4=high, 5=urgent.")
    tags: list[str] = Field(default_factory=list, description="Emoji tag names (e.g. ['robot', 'mag']).")
    url: str = Field("", description="Optional click-action URL attached to notification.")


class PlayMusicLinkInput(BaseModel):
    video_id: str = Field(..., description="YouTube video ID from search_music results.")
    title: str = Field("", description="Track title shown in notification.")
    artist: str = Field("", description="Artist name shown in notification.")


# ------ Music Schemas ------

class PlayMusicInput(BaseModel):
    query: str = Field(..., description="Song, artist, album, or playlist to search and play.")

class PlayByNumberInput(BaseModel):
    number: CoerceInt = Field(..., ge=1, description="Track number from the last search results to play.")

class PlayByIdInput(BaseModel):
    video_id: str = Field(..., description="YouTube video ID from search_music results.")

class SearchMusicInput(BaseModel):
    query: str = Field(..., description="Song, artist, or album to search on YouTube Music.")
    limit: CoerceInt = Field(5, ge=3, le=20, description="Number of results to return. Minimum 3, default 5, max 20.")
    search_type: Literal["songs", "videos", "all"] = Field(
        "songs",
        description="'songs' for studio tracks, 'videos' for live/concerts/music videos, 'all' for everything.",
    )

class VolumeInput(BaseModel):
    level: CoerceInt = Field(..., ge=0, le=100, description="Volume level 0-100.")
