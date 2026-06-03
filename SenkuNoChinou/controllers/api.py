import json
import logging
import uuid

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from SenkuNoChinou.core.workflow import respond, respond_stream
from SenkuNoChinou.models.apiSchema import CreateThreadResponse, RespondRequest, RespondResponse, SttRespondResponse, TranscribeResponse

log = logging.getLogger("senku.api")

router = APIRouter(prefix="/senku", tags=["senku"])


def _require_workflow(request: Request):
    wf = request.app.state.workflow
    if wf is None:
        raise HTTPException(503, "Service starting up, try again shortly")
    return wf


@router.get("/health")
async def health(request: Request):
    return {"status": "ok", "workflow_ready": request.app.state.workflow is not None}


@router.post("/create-thread", response_model=CreateThreadResponse)
async def create_thread():
    thread_id = str(uuid.uuid4())
    log.info("create_thread thread_id=%s", thread_id)
    return CreateThreadResponse(thread_id=thread_id)


@router.post("/respond", response_model=RespondResponse)
async def respond_endpoint(body: RespondRequest, request: Request):
    log.info("respond thread_id=%s query=%r", body.thread_id, body.query)
    wf = _require_workflow(request)
    response = await respond(wf, body.query, body.thread_id)
    log.info("respond done thread_id=%s response_len=%d", body.thread_id, len(response))
    return RespondResponse(response=response)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile, request: Request, language: str = "en"):
    log.info("transcribe file=%s content_type=%s language=%s", audio.filename, audio.content_type, language)
    stt = request.app.state.stt
    audio_bytes = await audio.read()
    text = await stt.transcribe(audio_bytes, filename=audio.filename or "audio", language=language)
    return TranscribeResponse(text=text)


@router.post("/stt-respond", response_model=SttRespondResponse)
async def stt_respond(
    request: Request,
    audio: UploadFile,
    thread_id: str = Form(...),
    language: str = Form("en"),
):
    log.info("stt_respond thread_id=%s file=%s language=%s", thread_id, audio.filename, language)
    wf = _require_workflow(request)
    stt = request.app.state.stt
    audio_bytes = await audio.read()
    transcript = await stt.transcribe(audio_bytes, filename=audio.filename or "audio", language=language)
    log.info("stt_respond transcript=%r", transcript[:100])
    response = await respond(wf, transcript, thread_id)
    log.info("stt_respond done thread_id=%s", thread_id)
    return SttRespondResponse(transcript=transcript, response=response)


@router.post("/stt-respond-stream")
async def stt_respond_stream(
    request: Request,
    audio: UploadFile,
    thread_id: str = Form(...),
    language: str = Form("en"),
):
    log.info("stt_respond_stream thread_id=%s file=%s", thread_id, audio.filename)
    wf = _require_workflow(request)
    stt = request.app.state.stt
    audio_bytes = await audio.read()
    transcript = await stt.transcribe(audio_bytes, filename=audio.filename or "audio", language=language)
    log.info("stt_respond_stream transcript=%r", transcript[:100])

    async def event_stream():
        yield f"data: {json.dumps({'transcript': transcript})}\n\n"
        token_count = 0
        async for token in respond_stream(wf, transcript, thread_id):
            token_count += 1
            yield f"data: {json.dumps({'token': token})}\n\n"
        log.info("stt_respond_stream done thread_id=%s tokens=%d", thread_id, token_count)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/respond-stream")
async def respond_stream_endpoint(body: RespondRequest, request: Request):
    log.info("respond_stream thread_id=%s query=%r", body.thread_id, body.query)
    wf = _require_workflow(request)

    async def event_stream():
        token_count = 0
        async for token in respond_stream(wf, body.query, body.thread_id):
            token_count += 1
            yield f"data: {json.dumps({'token': token})}\n\n"
        log.info("respond_stream done thread_id=%s tokens=%d", body.thread_id, token_count)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
