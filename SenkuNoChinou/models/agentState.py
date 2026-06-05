from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class NowPlaying(TypedDict):
    video_id: str
    title: str
    artist: str


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    gear: str                               # "ichi" | "ni" | "san" | "go"
    now_playing: NowPlaying | None          # current track, persists across turns
    retry_count: int                        # retries attempted this turn (reset each new human message)
    fulfilled: bool                         # set True by gear_yon when task is complete
