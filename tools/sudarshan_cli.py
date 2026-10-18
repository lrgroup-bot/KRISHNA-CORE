"""CLI for a locally configured SUDARSHAN pipeline.

Usage: python -m tools.sudarshan_cli --config config.json --approve-local-run
Configuration is an explicit JSON document, never downloaded or executed from URLs.
"""
import argparse
import json
from pathlib import Path
from .sudarshan_runtime import run_pipeline

def main(argv=None):
    parser=argparse.ArgumentParser(description="Run approved local agent adapters")
    parser.add_argument("--config",required=True,help="local JSON configuration path")
    parser.add_argument("--approve-local-run",action="store_true",help="explicit approval for configured local commands")
    args=parser.parse_args(argv)
    if not args.approve_local_run:
        parser.error("explicit --approve-local-run required")
    path=Path(args.config).resolve(strict=True)
    if not path.is_file():
        parser.error("config must be a file")
    settings=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(settings,dict):
        parser.error("configuration must be an object")
    for field in ("project_id","feature_id","db_path","adapters"):
        if field not in settings:
            parser.error("missing configuration field: "+field)
    # Resolve storage relative to the configuration, not the process cwd.
    db=Path(settings["db_path"])
    if not db.is_absolute():
        db=path.parent/db
    output=run_pipeline(settings["project_id"],settings["feature_id"],True,
                        settings["adapters"],str(db))
    print(json.dumps(output,indent=2,sort_keys=True))
    return 0 if output["readiness"]["ready_for_human_review"] else 2

if __name__=="__main__":
    raise SystemExit(main())
