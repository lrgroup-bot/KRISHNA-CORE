from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def _score_value(value, np) -> float:
    try:
        arr=np.asarray(value,dtype=float).reshape(-1)
        return float(arr[-1]) if arr.size else 0.0
    except Exception:
        try:return float(value)
        except Exception:return 0.0


def main() -> int:
    parser=argparse.ArgumentParser(description="KRISHNA isolated openWakeWord worker")
    parser.add_argument("--model",required=True)
    parser.add_argument("--threshold",type=float,default=0.65)
    parser.add_argument("--device",default=None)
    parser.add_argument("--cooldown",type=float,default=2.0)
    args=parser.parse_args()

    model_path=Path(args.model).expanduser().resolve()
    if not model_path.is_file():
        raise FileNotFoundError(str(model_path))

    import numpy as np
    import sounddevice as sd
    from openwakeword.model import Model

    device=args.device
    if isinstance(device,str) and device.strip().isdigit():
        device=int(device.strip())

    detector=Model(wakeword_models=[str(model_path)])
    cooldown_until=0.0

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=1280,
        dtype="int16",
        channels=1,
        device=device,
    ) as stream:
        while True:
            data,_overflowed=stream.read(1280)
            audio=np.frombuffer(data,dtype=np.int16)
            predictions=detector.predict(audio)
            score=max((_score_value(v,np) for v in predictions.values()),default=0.0)
            now=time.time()
            if score>=args.threshold and now>=cooldown_until:
                cooldown_until=now+max(0.5,args.cooldown)
                print(json.dumps({
                    "event":"wake",
                    "wake_word":"Krishna",
                    "score":round(max(0.0,min(1.0,score)),6),
                    "at":now,
                    "provider":"openwakeword-isolated",
                }),flush=True)


if __name__=="__main__":
    raise SystemExit(main())
