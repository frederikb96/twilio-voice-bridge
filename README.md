# twilio-voice-bridge

**Modular Twilio Voice to AI bridge. Connect phone calls to OpenAI, Gemini, or any voice provider via WebSocket.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/downloads/)

## What Is This?

A lightweight server that sits between Twilio and any AI voice provider. When someone calls your Twilio phone number, the server accepts the call, opens a bidirectional audio stream via WebSocket, and bridges it to an AI provider. The caller talks to the AI naturally over a regular phone call.

OpenAI's Realtime API is included as the reference provider implementation. The architecture is designed around a simple `AudioProvider` protocol -- swap in Google Gemini, a local Whisper + Ollama stack, or anything else that can send and receive audio over WebSocket.

This project started as a workaround for the Garmin Fenix 8's lack of microphone API access. The watch can make phone calls, but Garmin's SDK doesn't expose the microphone for third-party apps. By routing calls through Twilio to a server, any watch or phone becomes a voice interface to AI -- press a button, make a call, and start talking to your assistant. More context on this in the [Garmin developer forums](https://forums.garmin.com/).

## Architecture

```
    Phone / Watch              Twilio                Server               AI Provider
    =============          ==========          ===============         =============
         |                      |                      |                      |
         |--- phone call ------>|                      |                      |
         |                      |--- POST /incoming -->|                      |
         |                      |<-- TwiML <Stream> ---|                      |
         |                      |                      |                      |
         |<======= Twilio WebSocket =======>|<==== Provider WebSocket =====>|
         |                      |                      |                      |
         |   g711_ulaw audio ---|----> send_audio() -->|--- audio chunks --->|
         |                      |                      |                      |
         |                      |<--- AudioDelta ------|<-- AI response -----|
         |<-- audio playback ---|                      |                      |
         |                      |                      |                      |
         |                      |<--- SpeechStarted ---|  (interrupt: clear)  |
         |                      |                      |                      |
         |--- hang up -------->|--- stop ------------->|--- disconnect() --->|
```

The server runs two concurrent async tasks per call: one relays audio from Twilio to the provider, the other streams AI responses back. When the provider detects the caller started speaking (VAD), a `clear` event interrupts any in-progress AI playback.

## Quick Start

**Prerequisites:** Python 3.12+, a [Twilio account](https://www.twilio.com/try-twilio), an [OpenAI API key](https://platform.openai.com/api-keys) with Realtime API access, and [ngrok](https://ngrok.com/) for local development.

- Clone the repo and install dependencies:
  ```bash
  git clone https://github.com/frederikb96/twilio-voice-bridge.git
  cd twilio-voice-bridge
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```

- Copy `.env.example` to `.env` and fill in your keys:
  ```bash
  cp .env.example .env
  # Edit .env with your TWILIO_AUTH_TOKEN and OPENAI_API_KEY
  ```

- Start the server:
  ```bash
  uvicorn src.server:app --host 0.0.0.0 --port 5050
  ```

Then expose it with ngrok (`ngrok http 5050`) and configure your Twilio number's webhook (see below).

## Twilio Setup

If you're starting from scratch:

- **Create a Twilio account** at [twilio.com/try-twilio](https://www.twilio.com/try-twilio). The free trial includes a phone number and some credit.

- **Buy a phone number** (or use the trial number). In the Twilio Console, go to *Phone Numbers* -> *Buy a Number*. Make sure it has **Voice** capability.

- **Get your Auth Token** from the Twilio Console dashboard. Set it as `TWILIO_AUTH_TOKEN` in your `.env`.

- **Configure the webhook.** In the Twilio Console: *Phone Numbers* -> *Manage* -> *Active Numbers* -> select your number -> under *Voice Configuration*, set "A call comes in" to **Webhook**, method **POST**, URL:
  ```
  https://your-domain.com/incoming-call
  ```
  For local development, use your ngrok URL:
  ```
  https://abc123.ngrok-free.app/incoming-call
  ```

- **Call your Twilio number.** You should hear the AI assistant respond.

## Configuration

All settings are loaded from environment variables (or a `.env` file). See `.env.example` for a ready-to-use template.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TWILIO_AUTH_TOKEN` | **Yes** | -- | Auth token from Twilio Console, used to validate webhook signatures |
| `OPENAI_API_KEY` | **Yes** (when using OpenAI provider) | -- | OpenAI API key with Realtime API access |
| `PROVIDER` | No | `openai` | Which AI provider to use |
| `SYSTEM_PROMPT` | No | `You are a helpful voice assistant.` | Instructions for the AI assistant |
| `VOICE` | No | `alloy` | Voice for the AI assistant (provider-specific) |
| `MODEL` | No | `gpt-4o-realtime-preview` | Model to use (provider-specific) |
| `ALLOWED_CALLERS` | No | *(empty = allow all)* | Comma-separated phone numbers in E.164 format (e.g. `+14155551234,+49151...`) |
| `MAX_CALL_DURATION` | No | `300` | Maximum call duration in seconds (cost protection) |
| `PORT` | No | `5050` | Server port |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Deployment

### Local Development

```bash
# Terminal 1: start the server
source .venv/bin/activate
uvicorn src.server:app --host 0.0.0.0 --port 5050

# Terminal 2: expose via ngrok
ngrok http 5050
```

Copy the ngrok HTTPS URL and paste it into your Twilio webhook config as `https://<ngrok-url>/incoming-call`.

### Docker

```bash
docker compose up --build
```

For production, put this behind a reverse proxy (nginx, Caddy, Traefik) that terminates TLS. Twilio requires HTTPS for webhooks and WSS for media streams.

## Creating a Custom Provider

The entire bridge is provider-agnostic. To add a new AI backend, implement the `AudioProvider` protocol:

```python
from collections.abc import AsyncIterator

from src.provider import (
    AudioDelta,
    AudioDone,
    AudioEvent,
    ProviderConfig,
    SpeechStarted,
    SpeechStopped,
)


class MyProvider:
    """AudioProvider implementation for My AI Service."""

    async def connect(self, config: ProviderConfig) -> None:
        """Establish connection to the provider.

        Use config.extra for provider-specific settings (API keys, etc).
        """
        ...

    async def send_audio(self, audio_payload: str) -> None:
        """Forward base64-encoded g711_ulaw audio from the caller."""
        ...

    async def receive_audio(self) -> AsyncIterator[AudioEvent]:
        """Yield audio events back to the caller.

        AudioDelta(payload=...)  -- chunk of base64 audio to play
        AudioDone()              -- response finished
        SpeechStarted()          -- caller started speaking (interrupts playback)
        SpeechStopped()          -- caller stopped speaking
        """
        ...

    async def disconnect(self) -> None:
        """Clean up connections."""
        ...
```

Then register it in `src/providers/__init__.py`:

```python
from .my_provider import MyProvider

PROVIDERS: dict[str, type[Any]] = {
    "openai": OpenAIRealtimeProvider,
    "my_provider": MyProvider,
}
```

Set `PROVIDER=my_provider` in your `.env` and you're done. The bridge handles all Twilio communication -- your provider only needs to speak audio.

**Audio format:** Twilio Media Streams sends g711_ulaw at 8kHz mono. If your AI backend uses a different format, convert in your provider's `send_audio()` / `receive_audio()` methods. OpenAI's Realtime API accepts g711_ulaw natively, so the included provider needs no conversion.

**Ideas:** Google Gemini provider, local Whisper + Ollama for fully offline operation, Amazon Nova Sonic, ElevenLabs, or a simple echo provider for testing.

## Cost Estimate

OpenAI's Realtime API dominates the cost. Twilio voice is comparatively cheap.

| Component | Rate |
|-----------|------|
| Twilio phone number | ~$1.15/month |
| Twilio inbound voice | ~$0.0085/min |
| OpenAI Realtime API (gpt-4o) | ~$0.30/min (input + output combined) |
| Server hosting | $5-15/month (small VPS) |

**Monthly estimates:**

| Usage Pattern | Twilio | OpenAI | Server | Total |
|---------------|--------|--------|--------|-------|
| Light (2 calls/day, 2 min) | ~$3 | ~$36 | ~$5-15 | **~$44-54** |
| Casual (5 calls/day, 3 min) | ~$5 | ~$135 | ~$5-15 | **~$145-155** |
| Heavy (15 calls/day, 5 min) | ~$20 | ~$675 | ~$10-20 | **~$705-715** |

**Cost reduction:** Using `gpt-4o-mini-realtime-preview` instead of `gpt-4o-realtime-preview` reduces the OpenAI portion by roughly 70%, bringing the casual use case down to ~$50-60/month. Set `MODEL=gpt-4o-mini-realtime-preview` in your `.env`.

The `MAX_CALL_DURATION` setting (default: 300 seconds) acts as a cost safety net.

<details>
<summary><strong>How I Use This</strong></summary>

I built this to turn my Garmin Fenix 8 smartwatch into a voice AI interface. The watch has a speaker and microphone for phone calls, but Garmin's Connect IQ SDK doesn't expose the mic to third-party apps. So instead of fighting the SDK, I went around it: the watch dials a Twilio number, which routes to this server, which connects to OpenAI's Realtime API.

From button press to hearing "Hello" takes about 5 seconds. The call quality is standard phone audio (8kHz) which works well for voice conversations.

My private fork extends this with Home Assistant integration (lights, climate, sensors), task scheduling, calendar access, and web research -- but that's all custom function calling layered on top of this same bridge architecture.

</details>

## Known Limitations

- **Latency ~950-1100ms** -- The phone call infrastructure (PSTN + Twilio Media Streams) adds ~200-300ms before the AI even starts processing. Total mouth-to-ear time is roughly 1 second. Functional, but noticeably slower than talking to Siri or Alexa.
- **Single concurrent call per instance** -- The architecture assumes one active call. A second call will get its own bridge session, but scaling to many concurrent calls would need separate provider connections and resource management.
- **8kHz phone audio** -- Twilio Media Streams uses g711_ulaw at 8kHz mono. Adequate for speech, but not HD audio. This is inherent to the PSTN path.
- **No WebSocket reconnection** -- If the provider connection drops mid-call (network blip, API timeout), the call dies. No automatic retry.
- **Caller ID is spoofable** -- The `ALLOWED_CALLERS` filter checks the `From` field, which can be spoofed via VoIP services. For sensitive deployments, consider adding a voice PIN prompt before connecting to the AI.

## Alternatives

Depending on your use case, simpler or cheaper options may exist:

- **[OpenAI SIP Direct](https://platform.openai.com/docs/guides/realtime-phone-calling)** -- Twilio Elastic SIP Trunking connects directly to OpenAI, no bridge server needed. Simpler for OpenAI-only setups without custom tool calling.
- **[Plivo](https://www.plivo.com/)** -- 35-40% cheaper than Twilio for voice, 6-second billing granularity vs Twilio's 1-minute minimum.
- **[LiveKit](https://livekit.io/) / [Pipecat](https://github.com/pipecat-ai/pipecat)** -- Open-source WebRTC frameworks with sub-300ms latency. Different client approach (browser/app, not phone call).
- **[Twilio ConversationRelay](https://www.twilio.com/docs/voice/conversation-relay)** -- Twilio's managed orchestration layer. Claims <500ms median latency.

## Legal Notice

While this system does not record calls, it processes and transmits audio content to third-party AI services in real time. This may fall under recording/monitoring regulations depending on your jurisdiction:

- **Germany:** Section 201 StGB -- recording private speech without consent is a criminal offense. AI processing of call audio may require disclosure.
- **US:** Varies by state. 11 states (including California, Illinois, Florida) require all-party consent for call recording/monitoring.
- **EU/GDPR:** Processing voice data requires a legal basis and may require explicit consent.

**Recommendation:** Add a brief spoken disclosure at the start of each call (e.g., via the `SYSTEM_PROMPT`). Something like: *"This call is processed by an AI assistant."*

## Troubleshooting

- **Call connects but no audio** -- Verify your Twilio webhook URL ends with `/incoming-call`. Check that the WebSocket connection upgrades to `wss://` (not `ws://`). If using ngrok, make sure it's still running.

- **403 on incoming call** -- The server validates Twilio webhook signatures. Ensure `TWILIO_AUTH_TOKEN` in `.env` matches your Twilio Console. Also check that the webhook URL configured in Twilio matches exactly what your server sees (watch for trailing slashes, HTTP vs HTTPS).

- **OpenAI connection fails** -- Verify your API key has Realtime API access (it's a separate enablement). Check that the model name is correct (`gpt-4o-realtime-preview`). Look at server logs for the specific error.

- **Audio is choppy or delayed** -- Server location matters. Deploy close to your Twilio region for lower latency. Check server CPU/memory -- audio relay is lightweight but network I/O matters.

- **Call drops after a few minutes** -- Check `MAX_CALL_DURATION` (default: 300 seconds / 5 minutes). Increase it in `.env` if needed.

- **"Unknown provider" error at startup** -- The `PROVIDER` value in `.env` must match a key in `src/providers/__init__.py`. Currently only `openai` is included.

## License

[MIT](LICENSE)
