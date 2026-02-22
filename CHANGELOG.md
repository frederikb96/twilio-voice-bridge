# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-02-22

### Added

- Repo logo and README header with icon
- Security section explaining Twilio signature validation
- CI path filters to skip builds on docs-only changes

### Changed

- Simplified cost section (removed specific numbers)
- Promoted "How I Use This" from collapsible to full section

## [0.1.0] - 2026-02-22

### Added

- Core bridge architecture with `AudioProvider` protocol
- OpenAI Realtime API provider (native g711_ulaw, no audio conversion)
- FastAPI server with Twilio webhook signature validation and caller allowlist
- Configurable VAD (semantic_vad/server_vad), eagerness, and barge-in control
- Initial greeting prompt (AI speaks first on call connect)
- Docker deployment with docker-compose and health check
- Step-by-step setup guide with Twilio regional routing (ie1)
