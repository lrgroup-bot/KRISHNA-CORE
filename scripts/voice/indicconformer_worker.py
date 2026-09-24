from __future__ import annotations

import argparse
import json
from pathlib import Path


LANGUAGES = {"hi", "or"}


def main() -> int:
    parser = argparse.ArgumentParser(description="KRISHNA AI4Bharat IndicConformer worker")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--language", required=True, choices=sorted(LANGUAGES))
    parser.add_argument("--model", required=True)
    parser.add_argument("--decoder", default="ctc", choices=("ctc", "rnnt"))
    args = parser.parse_args()

    audio_path = Path(args.audio).resolve()
    if not audio_path.is_file():
        raise FileNotFoundError(str(audio_path))

    import torch
    import torchaudio
    from transformers import AutoModel

    model_source = str(Path(args.model).resolve()) if Path(args.model).exists() else args.model
    model = AutoModel.from_pretrained(model_source, trust_remote_code=True)
    model.eval()

    wav, sample_rate = torchaudio.load(str(audio_path))
    wav = torch.mean(wav, dim=0, keepdim=True)
    if sample_rate != 16000:
        wav = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)(wav)

    with torch.inference_mode():
        transcription = model(wav, args.language, args.decoder)

    if isinstance(transcription, (list, tuple)):
        transcription = transcription[0] if transcription else ""
    text = str(transcription or "").strip()
    print(json.dumps({
        "text": text,
        "language": args.language,
        "decoder": args.decoder,
        "provider": "ai4bharat-indicconformer",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
