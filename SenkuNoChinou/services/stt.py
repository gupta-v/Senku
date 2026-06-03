import logging
import os

from groq import AsyncGroq

log = logging.getLogger("senku.stt")


class STTService:
    def __init__(self, api_key: str | None = None, model: str = "whisper-large-v3-turbo"):
        self._client = AsyncGroq(api_key=api_key or os.environ["GROQ_API_KEY"])
        self._model = model
        log.info("stt ready model=%s (groq api)", model)

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav", language: str = "en") -> str:
        log.info("stt transcribing file=%s bytes=%d language=%s", filename, len(audio_bytes), language)
        transcription = await self._client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=self._model,
            language=language,
            response_format="text",
        )
        text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
        log.info("stt done text=%r", text[:100])
        return text
