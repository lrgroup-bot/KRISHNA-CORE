"""Dedicated BRAHMA inference sidecar: trusted HTTPS -> loopback Ollama.

Runs on a separate inference PC. No cloud APIs, model pulling, arbitrary URL
forwarding, shell command execution or filesystem read endpoints.
Operator supplies certificate and long secret token. No credentials in repo.
"""
from __future__ import annotations

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
from threading import BoundedSemaphore
from urllib import request

MAX_BYTES=32768
MAX_INPUT=12000
PERMITTED_ROLES=frozenset({"rishi_research","rishi_exam_author","rishi_exam_reviewer"})
LOOPBACK_OLLAMA="http://127.0.0.1:11434/api/generate"


def infer(payload, *, models, timeout=100, opener=request.urlopen):
    if not isinstance(payload,dict):
        raise ValueError("request object required")
    model=payload.get("model")
    role=payload.get("role")
    prompt=payload.get("prompt")
    if model not in models or role not in PERMITTED_ROLES:
        raise ValueError("model or research role not authorized")
    if not isinstance(prompt,str) or not 40<=len(prompt)<=MAX_INPUT:
        raise ValueError("bounded substantive research prompt required")
    n=int(payload.get("num_predict",384))
    context=int(payload.get("num_ctx",4096))
    if not 1<=n<=3072 or not 512<=context<=8192:
        raise ValueError("Ollama context/prediction limits exceeded")
    request_body={"model":model,"prompt":prompt,"stream":False,"think":False,
                  "keep_alive":"30s",
                  "options":{"num_ctx":context,"num_predict":n,"temperature":0.2}}
    raw=json.dumps(request_body).encode("utf-8")
    req=request.Request(LOOPBACK_OLLAMA,data=raw,
                        headers={"Content-Type":"application/json"},method="POST")
    with opener(req,timeout=timeout) as response:
        body=response.read(131073)
    if len(body)>131072:
        raise ValueError("oversized Ollama response")
    result=json.loads(body)
    if not isinstance(result,dict) or not isinstance(result.get("response"),str):
        raise RuntimeError("invalid local Ollama output")
    return {"model":model,"role":role,"response":result["response"][:60000],
            "done":result.get("done") is True,
            "knowledge_verified":False,"inference_local":True}


def handler_factory(*, secret, models, concurrency=1):
    if not isinstance(secret,str) or len(secret)<48:
        raise ValueError("long operator-owned secret required")
    if not models or not all(isinstance(m,str) and 1<=len(m)<=120 for m in models):
        raise ValueError("explicit installed local Ollama model allowlist required")
    if type(concurrency) is not int or not 1<=concurrency<=2:
        raise ValueError("safe concurrency must be 1..2")
    limiter=BoundedSemaphore(concurrency)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path!="/v1/infer":
                return self.reply(404,{"error":"not found"})
            provided=self.headers.get("Authorization","")
            expected="Bearer "+secret
            if not hmac.compare_digest(provided,expected):
                return self.reply(401,{"error":"authorization required"})
            size=self.headers.get("Content-Length")
            if not size or not size.isdecimal() or not 1<=int(size)<=MAX_BYTES:
                return self.reply(413,{"error":"bounded request required"})
            try:
                payload=json.loads(self.rfile.read(int(size)))
            except (ValueError,UnicodeError):
                return self.reply(400,{"error":"invalid request JSON"})
            if not limiter.acquire(blocking=False):
                return self.reply(429,{"error":"local inference busy; retry with backoff"})
            try:
                result=infer(payload,models=models)
                self.reply(200,result)
            except ValueError as exc:
                self.reply(400,{"error":str(exc)[:180]})
            except Exception as exc:
                self.reply(503,{"error":"local inference failed","type":type(exc).__name__})
            finally:
                limiter.release()

        def reply(self,code,payload):
            raw=json.dumps(payload,ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self,*_):
            # Never log request bodies, tokens, source excerpts or model output.
            pass
    return Handler


def main(argv=None):
    p=argparse.ArgumentParser(description="Independent private BRAHMA Ollama HTTPS gateway")
    p.add_argument("--bind",required=True,help="Dedicated inference PC LAN IPv4")
    p.add_argument("--port",type=int,default=18787)
    p.add_argument("--cert",type=Path,required=True)
    p.add_argument("--key",type=Path,required=True)
    p.add_argument("--token-file",type=Path,required=True)
    p.add_argument("--model",action="append",required=True,help="Already installed model (repeatable)")
    a=p.parse_args(argv)
    import ipaddress
    ip=ipaddress.ip_address(a.bind)
    lan=any(ip in net for net in (ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8")))
    if ip.version!=4 or not lan:
        p.error("Only explicit private LAN IPv4 or loopback is allowed")
    secret=a.token_file.read_text(encoding="utf-8").strip()
    host=ThreadingHTTPServer((a.bind,a.port),handler_factory(secret=secret,models=set(a.model)))
    ssl_ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.minimum_version=ssl.TLSVersion.TLSv1_2
    ssl_ctx.load_cert_chain(certfile=str(a.cert),keyfile=str(a.key))
    host.socket=ssl_ctx.wrap_socket(host.socket,server_side=True)
    print("BRAHMA local-only inference HTTPS gateway ready",flush=True)
    try:host.serve_forever(poll_interval=0.3)
    finally:host.server_close()

if __name__=="__main__":
    main()
