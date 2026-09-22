# KRISHNA Video Avatar Pipeline

KRISHNA uses a local-first provider stack to reproduce the workflow class of hosted avatar/video studios without copying proprietary service code, weights, prompts, or private endpoints.

## Provider roles

- **MuseTalk 1.5** — primary low-latency talking/lip-sync provider.
- **LivePortrait** — portrait motion/expression transfer from a driving video or template.
- **EchoMimicV3 Flash** — higher-quality image + audio talking-body/video provider. Upstream documents a 12 GB VRAM Flash path and up to 768×768 output.
- **Wan-Animate-2** — optional cinematic character/body animation provider for heavier GPUs.
- **Higgsfield** — optional hosted connector only. It is not a free/local KRISHNA dependency and its proprietary implementation is never copied.

The canonical workflow is:

`identity/reference -> motion/audio -> lip-sync -> render -> verification`

## Privacy and license rules

All local providers install under:

`E:\\Krishna-The GOD\\tools\\avatar-video\\`

Private KRISHNA avatar assets remain local for these providers. The installer downloads source code only; model weights are deliberately not auto-downloaded until hardware capacity, disk space, and the exact upstream model-license path are checked.

LivePortrait code is MIT, but its upstream documentation notes separate non-commercial terms for bundled InsightFace models. KRISHNA must replace those models with a commercially compatible detector before any commercial deployment.

MuseTalk code is MIT and its upstream README permits its trained model for commercial use, subject to licenses of third-party dependencies and input/test data.

EchoMimicV3 and Wan-Animate-2 are Apache-2.0 projects.

## Installation

Fast/local providers:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\\scripts\\INSTALL_VIDEO_AVATAR_ENGINES.ps1" -Provider All
```

The default `All` mode installs MuseTalk and LivePortrait source code. Heavy providers are opt-in:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\\scripts\\INSTALL_VIDEO_AVATAR_ENGINES.ps1" -Provider All -IncludeHeavy
```

This still does **not** auto-download model weights.

## Runtime API

- `GET /api/avatar/video/status`
- `GET /api/avatar/video/recommend?goal=<goal>&vram_gb=<number>`
- `GET /api/avatar/video/contract?provider=musetalk`

`/api/avatar/status` also embeds the video-avatar provider status.

## Routing policy

For live conversation, prefer MuseTalk or the existing 3D TalkingHead renderer. For high-quality generated talking clips, prefer EchoMimicV3 when the GPU has enough VRAM. Use Wan-Animate-2 for offline/cinematic body motion. LivePortrait is best when a specific driving motion/video already exists.

Higgsfield can be connected later through its official API only when the owner explicitly chooses a paid/cloud workflow. It never replaces the free local path.
