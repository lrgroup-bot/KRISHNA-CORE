from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from email.message import EmailMessage


class NaradProviderError(RuntimeError):
    pass


def _json_request(url,method="POST",body=None,headers=None,timeout=45):
    data=None if body is None else json.dumps(body).encode("utf-8")
    req=urllib.request.Request(url,data=data,method=method,headers={"Accept":"application/json","Content-Type":"application/json",**(headers or {})})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=r.read().decode("utf-8","replace")
            return {"status":r.status,"ok":200<=r.status<300,"data":json.loads(raw) if raw.strip() else {}}
    except Exception as exc:
        raise NaradProviderError(f"{type(exc).__name__}: {exc}") from exc


class NaradProviderHub:
    """Concrete bounded provider operations for NARAD.

    Credential material is supplied as request headers by NaradCredentialVault and is
    never persisted here. All mutating operations are invoked only after PolicyKernel
    approval in NaradRuntime.
    """

    PROVIDERS=("telegram","discord","slack","whatsapp","gmail","google_drive","google_sheets","google_calendar")

    def providers(self):
        return list(self.PROVIDERS)

    def send(self,provider,operation,payload,headers=None):
        provider=str(provider or "").strip().lower()
        operation=str(operation or "").strip().lower()
        payload=dict(payload or {});headers=dict(headers or {})
        if provider=="telegram":return self._telegram(operation,payload,headers)
        if provider=="discord":return self._discord(operation,payload,headers)
        if provider=="slack":return self._slack(operation,payload,headers)
        if provider=="whatsapp":return self._whatsapp(operation,payload,headers)
        if provider=="gmail":return self._gmail(operation,payload,headers)
        if provider=="google_drive":return self._drive(operation,payload,headers)
        if provider=="google_sheets":return self._sheets(operation,payload,headers)
        if provider=="google_calendar":return self._calendar(operation,payload,headers)
        raise ValueError(f"unsupported NARAD provider: {provider}")

    @staticmethod
    def _bearer(headers):
        auth=headers.get("Authorization") or headers.get("authorization")
        if not auth:raise NaradProviderError("provider credential is required")
        return auth

    def _telegram(self,op,p,h):
        if op!="send_message":raise ValueError("telegram supports send_message")
        token=str(p.get("bot_token") or "").strip()
        if not token:
            auth=self._bearer(h)
            token=auth.split(" ",1)[1] if " " in auth else auth
        chat_id=str(p.get("chat_id") or "").strip();text=str(p.get("text") or "")
        if not chat_id or not text:raise ValueError("telegram chat_id and text are required")
        return _json_request(f"https://api.telegram.org/bot{token}/sendMessage",body={"chat_id":chat_id,"text":text})

    def _discord(self,op,p,h):
        if op!="send_message":raise ValueError("discord supports send_message")
        webhook=str(p.get("webhook_url") or "").strip()
        if not webhook.startswith("https://"):raise ValueError("discord webhook_url must use https")
        text=str(p.get("text") or "")
        if not text:raise ValueError("discord text is required")
        return _json_request(webhook,body={"content":text})

    def _slack(self,op,p,h):
        if op!="send_message":raise ValueError("slack supports send_message")
        channel=str(p.get("channel") or "").strip();text=str(p.get("text") or "")
        if not channel or not text:raise ValueError("slack channel and text are required")
        return _json_request("https://slack.com/api/chat.postMessage",body={"channel":channel,"text":text},headers={"Authorization":self._bearer(h)})

    def _whatsapp(self,op,p,h):
        if op!="send_message":raise ValueError("whatsapp supports send_message")
        phone_id=str(p.get("phone_number_id") or "").strip();to=str(p.get("to") or "").strip();text=str(p.get("text") or "")
        if not phone_id or not to or not text:raise ValueError("whatsapp phone_number_id, to and text are required")
        body={"messaging_product":"whatsapp","to":to,"type":"text","text":{"body":text}}
        return _json_request(f"https://graph.facebook.com/v23.0/{urllib.parse.quote(phone_id)}/messages",body=body,headers={"Authorization":self._bearer(h)})

    def _gmail(self,op,p,h):
        auth={"Authorization":self._bearer(h)}
        base="https://gmail.googleapis.com/gmail/v1/users/me/messages"
        if op=="send_email":
            to=str(p.get("to") or "").strip();subject=str(p.get("subject") or "").strip();text=str(p.get("text") or "")
            if not to or not subject:raise ValueError("gmail to and subject are required")
            msg=EmailMessage();msg["To"]=to;msg["Subject"]=subject;msg["From"]=str(p.get("from") or "me")
            in_reply_to=str(p.get("in_reply_to") or "").strip()
            references=str(p.get("references") or "").strip()
            if in_reply_to:msg["In-Reply-To"]=in_reply_to
            if references:msg["References"]=references
            msg.set_content(text)
            raw=base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii").rstrip("=")
            body={"raw":raw}
            thread_id=str(p.get("thread_id") or "").strip()
            if thread_id:body["threadId"]=thread_id
            return _json_request(base+"/send",body=body,headers=auth)
        if op=="list_messages":
            params={"maxResults":min(500,max(1,int(p.get("max_results") or 50)))}
            q=str(p.get("q") or "").strip()
            if q:params["q"]=q
            labels=p.get("label_ids") or []
            if labels:params["labelIds"]=[str(x) for x in labels]
            if bool(p.get("include_spam_trash",False)):params["includeSpamTrash"]="true"
            return _json_request(base+"?"+urllib.parse.urlencode(params,doseq=True),method="GET",headers=auth)
        message_id=str(p.get("message_id") or "").strip()
        if not message_id:raise ValueError("gmail message_id is required")
        safe=urllib.parse.quote(message_id,safe="")
        if op=="get_message":
            fmt=str(p.get("format") or "metadata").lower()
            if fmt not in {"minimal","full","raw","metadata"}:raise ValueError("unsupported gmail message format")
            params={"format":fmt}
            return _json_request(base+"/"+safe+"?"+urllib.parse.urlencode(params),method="GET",headers=auth)
        if op=="modify_labels":
            add=[str(x) for x in p.get("add_label_ids") or [] if str(x)]
            remove=[str(x) for x in p.get("remove_label_ids") or [] if str(x)]
            return _json_request(base+"/"+safe+"/modify",body={"addLabelIds":add,"removeLabelIds":remove},headers=auth)
        if op=="trash_message":
            return _json_request(base+"/"+safe+"/trash",body={},headers=auth)
        if op=="untrash_message":
            return _json_request(base+"/"+safe+"/untrash",body={},headers=auth)
        raise ValueError("gmail supports send_email, list_messages, get_message, modify_labels, trash_message, untrash_message")

    def _drive(self,op,p,h):
        if op=="list_files":
            q=urllib.parse.urlencode({"pageSize":min(100,max(1,int(p.get("page_size") or 20))),"fields":"files(id,name,mimeType,modifiedTime)"})
            return _json_request("https://www.googleapis.com/drive/v3/files?"+q,method="GET",headers={"Authorization":self._bearer(h)})
        if op=="create_folder":
            name=str(p.get("name") or "").strip()
            if not name:raise ValueError("drive folder name is required")
            return _json_request("https://www.googleapis.com/drive/v3/files",body={"name":name,"mimeType":"application/vnd.google-apps.folder"},headers={"Authorization":self._bearer(h)})
        raise ValueError("google_drive supports list_files or create_folder")

    def _sheets(self,op,p,h):
        if op!="append_values":raise ValueError("google_sheets supports append_values")
        sid=str(p.get("spreadsheet_id") or "").strip();rng=str(p.get("range") or "Sheet1!A1").strip();values=p.get("values")
        if not sid or not isinstance(values,list):raise ValueError("spreadsheet_id and values are required")
        url=f"https://sheets.googleapis.com/v4/spreadsheets/{urllib.parse.quote(sid)}/values/{urllib.parse.quote(rng,safe='!:$')}:append?valueInputOption=USER_ENTERED"
        return _json_request(url,body={"values":values},headers={"Authorization":self._bearer(h)})

    def _calendar(self,op,p,h):
        if op!="create_event":raise ValueError("google_calendar supports create_event")
        cal=str(p.get("calendar_id") or "primary")
        event=p.get("event")
        if not isinstance(event,dict) or not event.get("summary"):raise ValueError("calendar event with summary is required")
        url=f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(cal,safe='')}/events"
        return _json_request(url,body=event,headers={"Authorization":self._bearer(h)})
