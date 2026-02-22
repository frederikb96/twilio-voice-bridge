"""FastAPI application: health check, TwiML webhook, and WebSocket handler."""

import logging

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, Response
from twilio.request_validator import RequestValidator  # type: ignore[import-untyped]
from twilio.twiml.voice_response import VoiceResponse  # type: ignore[import-untyped]

from .bridge import run_bridge
from .config import Settings

logger = logging.getLogger(__name__)

settings = Settings()  # type: ignore[call-arg]

app = FastAPI()
_validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)


@app.get("/")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/incoming-call")
async def incoming_call(request: Request) -> Response:
    """TwiML webhook for incoming Twilio calls."""
    signature = request.headers.get("X-Twilio-Signature", "")
    form = dict(await request.form())
    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    url = f"{proto}://{host}{request.url.path}"

    if not _validator.validate(url, form, signature):
        logger.warning("Invalid Twilio signature")
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    caller = form.get("From", "")
    allowed = settings.allowed_caller_list
    if allowed and caller not in allowed:
        logger.warning("Unauthorized caller: %s", caller)
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    ws_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    response = VoiceResponse()
    connect = response.connect()
    connect.stream(url=f"wss://{ws_host}/media-stream")

    return Response(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket) -> None:
    """Accept Twilio Media Stream and bridge to AI provider."""
    await websocket.accept()
    logger.info("Media stream connected from %s", websocket.client)
    try:
        await run_bridge(websocket, settings)
    except Exception:
        logger.exception("Bridge error")
    finally:
        logger.info("Media stream closed")
