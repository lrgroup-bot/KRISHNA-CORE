"""Read-only local R19 chat latency diagnostic; no credentials or paid cloud calls."""
import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

def request(url, payload, timeout):
    parsed=urlsplit(url)
    if parsed.scheme not in {'http','https'} or parsed.hostname not in {'localhost','127.0.0.1','::1'} or parsed.username or parsed.password:
        raise ValueError('Latency diagnostics support loopback endpoints only')
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {"ok": not bool(data.get('error')), "seconds": round(time.monotonic()-started, 3),
                "response": str(data.get("response") or data.get("reply") or data.get("text") or "")[:160],
                "provider": data.get("provider"), "error": data.get("error")}
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return {"ok": False, "seconds": round(time.monotonic()-started, 3),
                "error_type": type(exc).__name__, "error": str(exc)[:160]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", default="http://127.0.0.1:18781")
    parser.add_argument("--ollama", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="granite3.3:2b")
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()
    if not (1 <= args.samples <= 10):
        parser.error("--samples must be between 1 and 10")
    prompt = "Reply with exactly KRISHNA CHAT READY and nothing else."
    results = {"model": args.model, "samples": args.samples, "strict_zero_credit":
        os.getenv("KRISHNA_STRICT_ZERO_CREDIT", "1"), "tests": {}}
    for name, url, payload in (
        ("ollama", args.ollama.rstrip("/") + "/api/generate",
         {"model": args.model, "prompt": prompt, "stream": False,
          "options": {"num_ctx": 2048, "num_predict": 64, "temperature": 0}}),
        ("r19_chat", args.core.rstrip("/") + "/api/core/chat",
         {"message": prompt, "project": "general", "source": "pc"})):
        rows = [request(url, payload, 120) for _ in range(args.samples)]
        durations = [r["seconds"] for r in rows if r["ok"]]
        results["tests"][name] = {"samples": rows,
            "median_seconds": round(statistics.median(durations), 3) if durations else None,
            "exact_replies": sum(r["response"].strip() == "KRISHNA CHAT READY" for r in rows if r["ok"])}
    print(json.dumps(results, ensure_ascii=False, indent=2))
    a = results["tests"]["ollama"]["median_seconds"]
    b = results["tests"]["r19_chat"]["median_seconds"]
    if a is not None and b is not None:
        print("Core overhead (median seconds):", round(b-a, 3))
    return 0 if all(x['exact_replies']==args.samples and len(x["samples"]) == args.samples and all(y["ok"] for y in x["samples"])
                    for x in results["tests"].values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
