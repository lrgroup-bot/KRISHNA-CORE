from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


MODEL_ID = "ai4bharat/indic-parler-tts-pretrained"
DEFAULT_STYLE = (
    "Aryan speaks Sanskrit in a calm, dignified, devotional and reassuring male voice "
    "at a measured pace with balanced pitch, restrained expressivity, very clear audio, "
    "a close recording and no background noise."
)


def _device(torch):
    forced=str(os.getenv("KRISHNA_SANSKRIT_TTS_DEVICE") or "").strip().lower()
    if forced in {"cpu","cuda"}:
        if forced=="cuda" and not torch.cuda.is_available():
            raise RuntimeError("KRISHNA_SANSKRIT_TTS_DEVICE=cuda but CUDA is unavailable")
        return forced
    if not torch.cuda.is_available():
        return "cpu"
    try:
        total=float(torch.cuda.get_device_properties(0).total_memory)/(1024**3)
    except Exception:
        total=0.0
    # The 0.9B F32 model plus text encoder/generation overhead is unsafe on a
    # 4 GB class card. Prefer reliability over an OOM-prone nominal GPU path.
    return "cuda" if total >= 6.0 else "cpu"


def main() -> int:
    parser=argparse.ArgumentParser(description="KRISHNA local Sanskrit Indic Parler-TTS worker")
    parser.add_argument("--text",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--model-root",required=True)
    parser.add_argument("--style",default=DEFAULT_STYLE)
    args=parser.parse_args()

    text=str(args.text or "").strip()
    if not text:
        raise ValueError("text is required")

    model_root=Path(args.model_root).resolve()
    if not model_root.is_dir():
        raise FileNotFoundError(f"Sanskrit model root missing: {model_root}")

    import torch
    import soundfile as sf
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    device=_device(torch)
    model=ParlerTTSForConditionalGeneration.from_pretrained(
        str(model_root),
        local_files_only=True,
    ).to(device)
    tokenizer=AutoTokenizer.from_pretrained(str(model_root),local_files_only=True)
    description_tokenizer=AutoTokenizer.from_pretrained(
        model.config.text_encoder._name_or_path,
        local_files_only=True,
    )

    description_input_ids=description_tokenizer(
        args.style,return_tensors="pt"
    ).to(device)
    prompt_input_ids=tokenizer(text,return_tensors="pt").to(device)

    with torch.inference_mode():
        generation=model.generate(
            input_ids=description_input_ids.input_ids,
            attention_mask=description_input_ids.attention_mask,
            prompt_input_ids=prompt_input_ids.input_ids,
            prompt_attention_mask=prompt_input_ids.attention_mask,
        )
    audio_arr=generation.cpu().numpy().squeeze()
    output=Path(args.output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    sf.write(str(output),audio_arr,model.config.sampling_rate)
    if not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError("Sanskrit TTS worker did not create a valid output WAV")

    print(json.dumps({
        "output":str(output),
        "language":"sa",
        "provider":"ai4bharat-indic-parler-tts-pretrained",
        "speaker":"Aryan",
        "device":device,
        "model":MODEL_ID,
    }))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
