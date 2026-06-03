import asyncio
import logging
import os
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

log = logging.getLogger("senku.stt")

# <project_root>/models/stt_models/
_DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "stt_models"


class STTService:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        model_dir: Path | str | None = None,
    ):
        download_root = Path(model_dir) if model_dir else _DEFAULT_MODEL_DIR
        download_root.mkdir(parents=True, exist_ok=True)

        local_path = download_root / model_size
        if (local_path / "model.bin").exists():
            model_ref = str(local_path)
            log.info("stt using local model dir=%s", local_path)
        else:
            model_ref = model_size
            log.info("stt downloading model=%s to %s", model_size, download_root)

        self._model = WhisperModel(model_ref, device=device, compute_type=compute_type)
        log.info("stt model ready")

    def _run_transcription(self, path: str, language: str | None) -> tuple[str, str]:
        segments, info = self._model.transcribe(path, language=language, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments)
        return text.strip(), info.language

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio", language: str | None = None) -> str:
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            log.info("stt transcribing file=%s bytes=%d", filename, len(audio_bytes))
            loop = asyncio.get_event_loop()
            text, detected_lang = await loop.run_in_executor(
                None, self._run_transcription, tmp_path, language
            )
            log.info("stt done lang=%s text=%r", detected_lang, text[:100])
            return text
        finally:
            os.unlink(tmp_path)
