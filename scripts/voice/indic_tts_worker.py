from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


LANGUAGES = {"hi", "or"}


def _patch_config(config_path: Path, speakers_path: Path) -> Path:
    """Create a KRISHNA-local config copy with an absolute speakers_file path."""
    data = json.loads(config_path.read_text(encoding="utf-8"))
    changed = False

    def visit(value):
        nonlocal changed
        if isinstance(value, dict):
            for key, item in list(value.items()):
                if key == "speakers_file" and speakers_path.is_file():
                    value[key] = str(speakers_path)
                    changed = True
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(data)
    if not changed:
        return config_path

    target = config_path.with_name("config.krishna.json")
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="KRISHNA AI4Bharat Indic-TTS worker")
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--language", required=True, choices=sorted(LANGUAGES))
    parser.add_argument("--model-root", required=True)
    args = parser.parse_args()

    lang_root = Path(args.model_root).resolve() / args.language
    fastpitch = lang_root / "fastpitch"
    hifigan = lang_root / "hifigan"

    model = fastpitch / "best_model.pth"
    config = fastpitch / "config.json"
    speakers = fastpitch / "speakers.pth"
    vocoder = hifigan / "best_model.pth"
    vocoder_config = hifigan / "config.json"

    required = (model, config, vocoder, vocoder_config)
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Indic-TTS model files missing: " + "; ".join(missing))

    config_for_run = _patch_config(config, speakers)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "TTS.bin.synthesize",
        "--text",
        args.text,
        "--model_path",
        str(model),
        "--config_path",
        str(config_for_run),
        "--vocoder_path",
        str(vocoder),
        "--vocoder_config_path",
        str(vocoder_config),
        "--out_path",
        str(output),
    ]
    proc = subprocess.run(command, capture_output=True, text=True, shell=False)
    if proc.returncode:
        detail = (proc.stderr or proc.stdout or "")[-4000:]
        raise RuntimeError(detail or f"Indic-TTS worker failed with exit code {proc.returncode}")
    if not output.is_file():
        raise RuntimeError("Indic-TTS worker completed without creating output audio")
    print(json.dumps({"output": str(output), "language": args.language, "provider": "ai4bharat-indic-tts"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
