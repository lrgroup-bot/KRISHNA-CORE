from __future__ import annotations

import argparse
import json
from pathlib import Path

from krishna_core.project_perfection_execution import ArtifactExecutor


def main() -> int:
    parser=argparse.ArgumentParser(description="KRISHNA clean APK install/launch/restart verifier")
    parser.add_argument("apk")
    parser.add_argument("package_id")
    parser.add_argument("--output",default="project-perfection-apk-retest.json")
    args=parser.parse_args()

    result=ArtifactExecutor().apk(args.apk,args.package_id)
    Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    if not result.get("passed"):
        raise SystemExit("KRISHNA APK emulator retest failed")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
