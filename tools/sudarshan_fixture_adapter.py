"""Offline smoke-check adapters for the SUDARSHAN contract.

These validate integration wiring only; they do NOT run REA or MiroFish.
"""
import argparse
import hashlib
import json

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("engine",choices=("REA","MiroFish","BRAHMAGYAN","VISHWAKARMA","UI_GUARDIAN","MRITYUNJAYA"))
    parser.add_argument("--fixture",required=True,help="explicit local fixture JSON")
    args=parser.parse_args(argv)
    with open(args.fixture,encoding="utf-8") as stream:
        fixture=json.load(stream)
    if not isinstance(fixture,dict) or fixture.get("engine")!=args.engine:
        raise ValueError("fixture engine mismatch")
    checks=fixture.get("checks")
    if not isinstance(checks,list) or not checks or not all(isinstance(c,dict) and
            isinstance(c.get("name"),str) and isinstance(c.get("passed"),bool) for c in checks):
        raise ValueError("checks must be nonempty list of named boolean results")
    passed=all(c["passed"] for c in checks)
    canonical=json.dumps(fixture,sort_keys=True).encode()
    output={"engine":args.engine,"status":"passed" if passed else "failed",
            "evidence_id":"sha256:"+hashlib.sha256(canonical).hexdigest(),
            "summary":str(len(checks))+" offline fixture checks; no real engine execution"}
    print(json.dumps(output))
    return 0 if passed else 1

if __name__=="__main__":
    raise SystemExit(main())
