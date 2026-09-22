#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CORE=ROOT/"core"
if str(CORE) not in sys.path:
    sys.path.insert(0,str(CORE))

from krishna_core.avatar_asset_pipeline import inspect_avatar


def main() -> int:
    parser=argparse.ArgumentParser(description="Audit a KRISHNA GLB without modifying it.")
    parser.add_argument("asset",type=Path)
    parser.add_argument("--report",type=Path,default=None)
    parser.add_argument("--require-ready",action="store_true")
    args=parser.parse_args()
    result=inspect_avatar(args.asset,args.report)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if (not args.require_ready or result.get("ready")) else 2


if __name__=="__main__":
    raise SystemExit(main())
