from pathlib import Path


def insert_once(text, marker, addition, *, after=True, label="patch"):
    if addition.strip() in text:
        return text, False
    if marker not in text:
        raise RuntimeError(f"{label}: marker not found")
    replacement = marker + addition if after else addition + marker
    return text.replace(marker, replacement, 1), True


def patch_server():
    path=Path("core/krishna_core/server.py")
    text=path.read_text(encoding="utf-8")
    changed=False

    text,c=insert_once(
        text,
        "from .hawkeye_media_sync import HawkeyeMediaSyncStore\n",
        "from .lr_mail_gateway import LRMailGateway\n",
        label="server import",
    );changed|=c
    text,c=insert_once(
        text,
        "_hawkeye_media_sync = HawkeyeMediaSyncStore(RUNTIME_ROOT)\n",
        "_lr_mail_gateway = LRMailGateway()\n",
        label="server gateway instance",
    );changed|=c

    route_marker='''        if path == "/api/mobile/connection":\n            return self._json(200, {**mobile_link_state(),"remote_policy":_remote_policy.status()})\n'''
    routes='''        if path == "/api/lr-mail/status":\n            return self._json(200,_lr_mail_gateway.status())\n        if path == "/api/lr-mail/summary":\n            raw=(query.get("limit") or ["100"])[0]\n            try:limit=max(1,min(int(raw),100))\n            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})\n            try:return self._json(200,_lr_mail_gateway.summary(limit))\n            except RuntimeError as exc:return self._json(503,{"error":str(exc)})\n        if path == "/api/lr-mail/messages":\n            raw_limit=(query.get("limit") or ["50"])[0]\n            raw_position=(query.get("position") or ["0"])[0]\n            text=str((query.get("text") or [""])[0])[:500]\n            try:\n                limit=max(1,min(int(raw_limit),100));position=max(0,int(raw_position))\n            except (TypeError,ValueError):return self._json(400,{"error":"invalid mail list cursor/limit"})\n            try:return self._json(200,_lr_mail_gateway.list(limit,position,text))\n            except RuntimeError as exc:return self._json(503,{"error":str(exc)})\n        if path == "/api/lr-mail/message":\n            message_id=str((query.get("id") or [""])[0]).strip()\n            if not message_id:return self._json(400,{"error":"id is required"})\n            try:return self._json(200,_lr_mail_gateway.get(message_id))\n            except ValueError as exc:return self._json(400,{"error":str(exc)})\n            except RuntimeError as exc:return self._json(503,{"error":str(exc)})\n\n'''
    if routes.strip() not in text:
        if route_marker not in text:raise RuntimeError("server routes: mobile connection marker not found")
        text=text.replace(route_marker,routes+route_marker,1);changed=True

    if changed:path.write_text(text,encoding="utf-8")
    return changed


def patch_main_activity():
    path=Path("mobile_v3/MainActivity.java")
    text=path.read_text(encoding="utf-8")
    marker='''    @JavascriptInterface public String status(){return call("/api/status",null);}\n'''
    addition='''    void emitLrMailResult(String callback,String result){\n      final String safe=result==null?"{}":result;\n      runOnUiThread(()->{\n        try{\n          if(web!=null&&webReady)web.evaluateJavascript(\n            "window."+callback+"&&window."+callback+"("+JSONObject.quote(safe)+")",null);\n        }catch(Exception ignored){}\n      });\n    }\n    @JavascriptInterface public void lrMailStatusAsync(){\n      new Thread(()->emitLrMailResult("onLrMailStatus",call("/api/lr-mail/status",null)),"krishna-lr-mail-status").start();\n    }\n    @JavascriptInterface public void lrMailSummaryAsync(int limit){\n      final int bounded=Math.max(1,Math.min(limit,100));\n      new Thread(()->emitLrMailResult("onLrMailSummary",call("/api/lr-mail/summary?limit="+bounded,null)),"krishna-lr-mail-summary").start();\n    }\n    @JavascriptInterface public void lrMailListAsync(int limit,int position,String text){\n      final int bounded=Math.max(1,Math.min(limit,100));\n      final int pos=Math.max(0,position);\n      final String q=text==null?"":text.trim();\n      new Thread(()->{\n        try{\n          String url="/api/lr-mail/messages?limit="+bounded+"&position="+pos+"&text="+URLEncoder.encode(q,"UTF-8");\n          emitLrMailResult("onLrMailList",call(url,null));\n        }catch(Exception e){emitLrMailResult("onLrMailList",error(e));}\n      },"krishna-lr-mail-list").start();\n    }\n    @JavascriptInterface public void lrMailMessageAsync(String messageId){\n      final String id=messageId==null?"":messageId.trim();\n      new Thread(()->{\n        try{\n          if(id.isEmpty())throw new IllegalArgumentException("message id is required");\n          emitLrMailResult("onLrMailMessage",call("/api/lr-mail/message?id="+URLEncoder.encode(id,"UTF-8"),null));\n        }catch(Exception e){emitLrMailResult("onLrMailMessage",error(e));}\n      },"krishna-lr-mail-message").start();\n    }\n'''
    if addition.strip() in text:return False
    if marker not in text:raise RuntimeError("MainActivity bridge marker not found")
    text=text.replace(marker,marker+addition,1)
    path.write_text(text,encoding="utf-8")
    return True


def main():
    changed=[]
    if patch_server():changed.append("core/krishna_core/server.py")
    if patch_main_activity():changed.append("mobile_v3/MainActivity.java")
    print("patched:",", ".join(changed) if changed else "already applied")


if __name__=="__main__":
    main()
