from __future__ import annotations

from http.cookies import SimpleCookie
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit
import ssl
import time

from .models import PrivacyFinding, PrivacyRiskClass


class _RecordingRedirect(HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.hops=[]
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append({"status":code,"from":req.full_url,"to":newurl})
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def _header(headers,name):
    value=headers.get(name)
    return str(value).strip() if value is not None else ""


def _cookie_findings(headers) -> list[dict]:
    rows=[]
    try:
        values=headers.get_all("Set-Cookie") or []
    except Exception:
        value=headers.get("Set-Cookie")
        values=[value] if value else []
    for raw in values[:50]:
        text=str(raw or "")
        low=text.lower()
        name=text.split("=",1)[0].strip()[:100] if "=" in text else "cookie"
        rows.append({
            "name":name,
            "secure":"; secure" in low or low.rstrip().endswith("secure"),
            "httponly":"; httponly" in low or low.rstrip().endswith("httponly"),
            "samesite":"lax" if "samesite=lax" in low else ("strict" if "samesite=strict" in low else ("none" if "samesite=none" in low else "unspecified")),
            "value_included":False,
        })
    return rows


def audit_web_endpoint(url: str, *, owned: bool=False, timeout: float=8.0) -> dict:
    target=str(url or "").strip()
    parts=urlsplit(target)
    if parts.scheme not in {"http","https"}:
        raise ValueError("web privacy audit requires http:// or https:// URL")
    redirect=_RecordingRedirect()
    opener=build_opener(redirect)
    req=Request(target,method="GET",headers={
        "User-Agent":"KRISHNA-KABACH-PrivacyGuardian/1",
        "Accept":"text/html,application/json;q=0.9,*/*;q=0.1",
    })
    started=time.perf_counter()
    error=None
    try:
        with opener.open(req,timeout=timeout) as resp:
            status=int(getattr(resp,"status",200) or 200)
            final_url=str(resp.geturl())
            headers=resp.headers
            # Read only a small prefix to avoid collecting unnecessary page content.
            resp.read(2048)
    except HTTPError as exc:
        status=int(exc.code)
        final_url=str(exc.geturl())
        headers=exc.headers
        error=f"HTTPError: {exc.code}"
    except (URLError,OSError,TimeoutError) as exc:
        return {
            "url":target,"owned":bool(owned),"ok":False,
            "error":f"{type(exc).__name__}: {exc}",
            "elapsed_ms":int((time.perf_counter()-started)*1000),
            "findings":[PrivacyFinding(
                test="web.endpoint.reachable",state="failed",
                summary="Endpoint could not be reached for privacy/security observation.",
                risk_class=PrivacyRiskClass.INCONCLUSIVE,
                evidence={"error_type":type(exc).__name__},
                recommendation="Verify the owned endpoint is running and reachable before interpreting privacy headers.",
                limitations=["No header/TLS conclusions are possible without a response."],
                source_methodology="HTTP Observatory-style defensive header observation",
            ).as_dict()],
        }

    final=urlsplit(final_url)
    https=final.scheme=="https"
    headers_lower={str(k).lower():str(v) for k,v in headers.items()}
    cookies=_cookie_findings(headers)
    csp=_header(headers,"Content-Security-Policy")
    hsts=_header(headers,"Strict-Transport-Security")
    xcto=_header(headers,"X-Content-Type-Options")
    xfo=_header(headers,"X-Frame-Options")
    refpol=_header(headers,"Referrer-Policy")
    permpol=_header(headers,"Permissions-Policy")
    coop=_header(headers,"Cross-Origin-Opener-Policy")
    corp=_header(headers,"Cross-Origin-Resource-Policy")
    coep=_header(headers,"Cross-Origin-Embedder-Policy")
    acao=_header(headers,"Access-Control-Allow-Origin")
    findings=[]

    def add(test,state,summary,risk=PrivacyRiskClass.LOW_EXPOSURE,evidence=None,recommendation="",limitations=None):
        findings.append(PrivacyFinding(
            test=test,state=state,summary=summary,risk_class=risk,
            evidence=evidence or {},recommendation=recommendation,
            limitations=list(limitations or []),
            source_methodology="HTTP Observatory-style defensive header observation",
        ).as_dict())

    add("web.https","enabled" if https else "disabled",
        "Endpoint uses HTTPS." if https else "Endpoint is not using HTTPS.",
        PrivacyRiskClass.LOW_EXPOSURE if https else (PrivacyRiskClass.MODERATE_EXPOSURE if owned else PrivacyRiskClass.INCONCLUSIVE),
        {"final_scheme":final.scheme,"redirect_hops":redirect.hops},
        "Use HTTPS for remotely reachable owned endpoints." if owned and not https else "",
        ["Loopback-only HTTP can be an intentional local deployment choice."] if not https else [])
    add("web.hsts","enabled" if hsts else "missing",
        "HSTS is present." if hsts else "HSTS is not present.",
        PrivacyRiskClass.LOW_EXPOSURE if hsts else (PrivacyRiskClass.MODERATE_EXPOSURE if owned and https else PrivacyRiskClass.INCONCLUSIVE),
        {"present":bool(hsts)})
    add("web.csp","enabled" if csp else "missing",
        "Content-Security-Policy is present." if csp else "Content-Security-Policy is not present.",
        PrivacyRiskClass.LOW_EXPOSURE if csp else (PrivacyRiskClass.MODERATE_EXPOSURE if owned else PrivacyRiskClass.INCONCLUSIVE),
        {"present":bool(csp)})
    add("web.referrer_policy","enabled" if refpol else "missing",
        "Referrer-Policy is explicit." if refpol else "Referrer-Policy is not explicit.",
        PrivacyRiskClass.LOW_EXPOSURE if refpol else (PrivacyRiskClass.MODERATE_EXPOSURE if owned else PrivacyRiskClass.INCONCLUSIVE),
        {"present":bool(refpol)})
    add("web.permissions_policy","enabled" if permpol else "missing",
        "Permissions-Policy is present." if permpol else "Permissions-Policy is not present.",
        PrivacyRiskClass.LOW_EXPOSURE if permpol else (PrivacyRiskClass.MODERATE_EXPOSURE if owned else PrivacyRiskClass.INCONCLUSIVE),
        {"present":bool(permpol)})
    add("web.x_content_type_options","nosniff" if xcto.lower()=="nosniff" else ("present" if xcto else "missing"),
        "X-Content-Type-Options is "+("nosniff." if xcto.lower()=="nosniff" else ("present." if xcto else "missing.")),
        PrivacyRiskClass.LOW_EXPOSURE if xcto.lower()=="nosniff" else (PrivacyRiskClass.MODERATE_EXPOSURE if owned else PrivacyRiskClass.INCONCLUSIVE),
        {"present":bool(xcto),"nosniff":xcto.lower()=="nosniff"})
    frame_protected=bool(xfo or "frame-ancestors" in csp.lower())
    add("web.frame_protection","enabled" if frame_protected else "missing",
        "Frame embedding protection is present." if frame_protected else "No X-Frame-Options/frame-ancestors protection was observed.",
        PrivacyRiskClass.LOW_EXPOSURE if frame_protected else (PrivacyRiskClass.MODERATE_EXPOSURE if owned else PrivacyRiskClass.INCONCLUSIVE),
        {"x_frame_options":bool(xfo),"csp_frame_ancestors":"frame-ancestors" in csp.lower()})
    cross={
        "coop":bool(coop),"corp":bool(corp),"coep":bool(coep),
        "cors_allow_origin":acao[:200] if acao else "",
    }
    add("web.cross_origin_policy","observed",
        "Cross-origin headers were inspected.",
        PrivacyRiskClass.LOW_EXPOSURE if any((coop,corp,coep)) else PrivacyRiskClass.INCONCLUSIVE,
        cross,
        limitations=["COOP/CORP/COEP are context-dependent and are not mandatory for every endpoint."])
    insecure_cookies=[x for x in cookies if https and (not x["secure"] or x["samesite"]=="unspecified")]
    add("web.cookies","observed",
        f"{len(cookies)} Set-Cookie header(s) observed; values were not retained.",
        PrivacyRiskClass.MODERATE_EXPOSURE if owned and insecure_cookies else PrivacyRiskClass.LOW_EXPOSURE,
        {"cookies":cookies,"potentially_weaker_count":len(insecure_cookies)},
        "Review Secure/HttpOnly/SameSite flags on owned authentication cookies." if insecure_cookies else "")
    return {
        "url":target,"final_url":final_url,"status":status,"owned":bool(owned),
        "ok":status<500 and not any(x["risk_class"]=="PRIVACY REGRESSION" for x in findings),
        "elapsed_ms":int((time.perf_counter()-started)*1000),
        "redirects":redirect.hops,
        "headers_present":sorted(headers_lower.keys()),
        "findings":findings,
        "error":error,
        "policy":"Owned endpoints may be gated; third-party endpoints are observed but not graded as if KRISHNA controls them.",
    }
