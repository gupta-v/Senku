from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class NowPlaying(TypedDict):
    video_id: str
    title: str
    artist: str


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    gear: str                               # "ichi" | "ni" | "san"
    now_playing: NowPlaying | None          # current track, persists across turns
