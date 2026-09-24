from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser=argparse.ArgumentParser(description="KRISHNA local Sanskrit recitation worker")
    parser.add_argument("--text",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--bundle-root",required=True)
    parser.add_argument("--meter",default="anushtubh")
    parser.add_argument("--nfe",type=int,default=12)
    args=parser.parse_args()

    bundle=Path(args.bundle_root).resolve()
    generator=bundle/"generate_sanskrit_v2.py"
    if not generator.is_file():
        raise FileNotFoundError("EdgeSanskrit generator missing: "+str(generator))
    # Required local assets: fail closed rather than silently downloading at speech time.
    required=(
        bundle/"models"/"IndicF5"/"model.safetensors",
        bundle/"models"/"vocos",
        bundle/"vagdhenu"/"src"/"reference_bank"/"bank.json",
        bundle/"vagdhenu"/"src"/"reference_bank"/"vocab.txt",
    )
    missing=[str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("EdgeSanskrit offline assets missing: "+"; ".join(missing))

    output=Path(args.output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)

    env=dict(os.environ)
    env["HF_HUB_OFFLINE"]="1"
    env["TRANSFORMERS_OFFLINE"]="1"
    env["HF_DATASETS_OFFLINE"]="1"
    env["NO_PROXY"]="*"

    command=[
        sys.executable,str(generator),args.text,
        "--meter",args.meter,
        "--output",str(output),
        "--nfe",str(max(4,min(32,args.nfe))),
        "--voice-model","indicf5",
    ]
    proc=subprocess.run(command,capture_output=True,text=True,shell=False,env=env,timeout=170)
    if proc.returncode:
        detail=(proc.stderr or proc.stdout or "")[-5000:]
        raise RuntimeError(detail or f"EdgeSanskrit worker failed with exit code {proc.returncode}")
    if not output.is_file() or output.stat().st_size<256:
        raise RuntimeError("EdgeSanskrit worker completed without usable WAV output")

    print(json.dumps({
        "output":str(output),
        "language":"sa",
        "provider":"edge-sanskrit-tts",
        "local":True,
        "offline_execution":True,
        "voice_model":"indicf5",
        "voice_note":"Third-party Sanskrit reference recitation; not a claim of Krishna's historical voice.",
    },ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
