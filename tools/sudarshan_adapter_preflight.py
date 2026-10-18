"""Offline contract smoke checks for a real local adapter installation.

This checks executable presence and a configured --version command, but never
claims that a workflow or integration has been validated.
"""
import argparse
import json
import subprocess
from pathlib import Path

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True)
    args=parser.parse_args(argv)
    config=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if not isinstance(config,dict) or not isinstance(config.get("adapters"),dict):
        raise ValueError("manifest must contain adapters object")
    report={}
    for engine,entry in config["adapters"].items():
        if not isinstance(entry,dict) or not isinstance(entry.get("probe"),list):
            report[engine]={"status":"not_configured"}
            continue
        command=entry["probe"]
        if not command or not all(isinstance(x,str) for x in command):
            report[engine]={"status":"invalid_probe"}
            continue
        executable=Path(command[0])
        if not executable.is_absolute() or not executable.is_file():
            report[engine]={"status":"executable_missing"}
            continue
        try:
            result=subprocess.run(command,capture_output=True,text=True,timeout=10,
                                  shell=False,check=False)
            report[engine]={"status":"probe_ok" if result.returncode==0 else "probe_failed",
                            "returncode":result.returncode}
        except (OSError,subprocess.TimeoutExpired):
            report[engine]={"status":"probe_failed"}
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if report and all(v["status"]=="probe_ok" for v in report.values()) else 2

if __name__=="__main__":
    raise SystemExit(main())
