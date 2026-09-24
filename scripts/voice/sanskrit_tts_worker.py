from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser=argparse.ArgumentParser(description="KRISHNA isolated EdgeSanskrit recitation worker")
    parser.add_argument("--text",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--meter",default="anushtubh")
    parser.add_argument("--engine-root",required=True)
    parser.add_argument("--nfe",type=int,default=12)
    args=parser.parse_args()

    engine_root=Path(args.engine_root).resolve()
    generator=engine_root/"generate_sanskrit_v2.py"
    if not generator.is_file():
        raise FileNotFoundError(f"EdgeSanskrit generator missing: {generator}")
    output=Path(args.output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)

    command=[
        sys.executable, str(generator),
        "--text",str(args.text),
        "--meter",str(args.meter or "anushtubh"),
        "--output",str(output),
        "--nfe",str(max(4,min(32,int(args.nfe)))),
        "--voice-model","indicf5",
    ]
    proc=subprocess.run(command,cwd=str(engine_root),capture_output=True,text=True,
                        encoding="utf-8",errors="replace",shell=False,timeout=900)
    if proc.returncode:
        detail=(proc.stderr or proc.stdout or "")[-6000:]
        raise RuntimeError(detail or f"EdgeSanskrit failed with exit code {proc.returncode}")
    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError("EdgeSanskrit completed without a usable WAV output")
    print(json.dumps({"output":str(output),"language":"sa","provider":"edge-sanskrit-tts",
                      "meter":str(args.meter or "anushtubh"),"nfe":max(4,min(32,int(args.nfe)))},
                     ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
