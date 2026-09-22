package com.krishna.mobile;

import android.app.*;
import android.os.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.webkit.*;
import android.media.*;
import android.net.Uri;
import android.util.Base64;
import android.location.*;
import java.net.*;
import java.io.*;
import java.util.*;
import org.json.*;

public class MainActivity extends Activity {
  static final String CORE="/api/core/chat";
  static final String SPEAKER_ENGINE="LOCAL_VOICE_GATE_V3";
  static final int FILE_PICKER=73;
  WebView web;
  Bridge bridge;
  ValueCallback<Uri[]> fileCallback;

  static final String NOTIFY_CHANNEL="krishna_completed";
  String deviceId(){
    android.content.SharedPreferences p=getSharedPreferences("k",0);
    String id=p.getString("device_id","");
    if(id.isEmpty()){id="android-"+java.util.UUID.randomUUID();p.edit().putString("device_id",id).apply();}
    return id;
  }
  void ensureNotifications(){
    if(Build.VERSION.SDK_INT>=26){
      NotificationManager n=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
      n.createNotificationChannel(new NotificationChannel(NOTIFY_CHANNEL,"KRISHNA completed work",NotificationManager.IMPORTANCE_DEFAULT));
    }
  }
  void notifyCompleted(String text){
    Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,NOTIFY_CHANNEL):new Notification.Builder(this);
    b.setSmallIcon(android.R.drawable.stat_notify_more).setContentTitle("KRISHNA completed work").setContentText(text).setAutoCancel(true);
    ((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify((int)(System.currentTimeMillis()&0x7fffffff),b.build());
  }

  @Override public void onCreate(Bundle b){
    super.onCreate(b);
    ensureNotifications();
    if(Build.VERSION.SDK_INT>=33 && checkSelfPermission("android.permission.POST_NOTIFICATIONS")!=PackageManager.PERMISSION_GRANTED)
      requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"},42);
    if(Build.VERSION.SDK_INT>=23 && checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)
      requestPermissions(new String[]{android.Manifest.permission.RECORD_AUDIO},41);
    if(Build.VERSION.SDK_INT>=23 && checkSelfPermission(android.Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED)
      requestPermissions(new String[]{android.Manifest.permission.CAMERA},43);
    web=new WebView(this);
    web.getSettings().setJavaScriptEnabled(true);
    web.getSettings().setDomStorageEnabled(true);
    web.getSettings().setAllowFileAccess(true); // required only for android_asset shell
    web.getSettings().setAllowFileAccessFromFileURLs(false);
    web.getSettings().setAllowUniversalAccessFromFileURLs(false);
    web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    web.getSettings().setSafeBrowsingEnabled(true);
    web.removeJavascriptInterface("searchBoxJavaBridge_");
    web.removeJavascriptInterface("accessibility");
    web.removeJavascriptInterface("accessibilityTraversal");
    web.setWebViewClient(new WebViewClient(){
      boolean trusted(Uri u){return u!=null && "file".equalsIgnoreCase(u.getScheme()) && "/android_asset/index.html".equals(u.getPath());}
      @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
        if(request==null || !request.isForMainFrame())return false;
        return !trusted(request.getUrl());
      }
      @Override public boolean shouldOverrideUrlLoading(WebView view,String url){
        try{return !trusted(Uri.parse(url));}catch(Exception e){return true;}
      }
    });
    web.setWebChromeClient(new WebChromeClient(){
      @Override public void onPermissionRequest(PermissionRequest request){
        runOnUiThread(()->{
          ArrayList<String> allowed=new ArrayList<>();
          if(Build.VERSION.SDK_INT<23 || checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED){
            for(String r:request.getResources()) if(PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(r)) allowed.add(r);
          }
          if(Build.VERSION.SDK_INT<23 || checkSelfPermission(android.Manifest.permission.CAMERA)==PackageManager.PERMISSION_GRANTED){
            for(String r:request.getResources()) if(PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(r)) allowed.add(r);
          }
          if(allowed.isEmpty())request.deny();else request.grant(allowed.toArray(new String[0]));
        });
      }
      @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params){
        if(fileCallback!=null)fileCallback.onReceiveValue(null);
        fileCallback=callback;
        try{
          Intent pick=params.createIntent();
          startActivityForResult(pick,FILE_PICKER);
          return true;
        }catch(Exception e){
          fileCallback=null;
          return false;
        }
      }
    });
    bridge=new Bridge();
    web.addJavascriptInterface(bridge,"Krishna");
    setContentView(web);
    web.loadUrl("file:///android_asset/index.html");
  }

  @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
    super.onActivityResult(requestCode,resultCode,data);
    if(requestCode==FILE_PICKER && fileCallback!=null){
      Uri[] result=WebChromeClient.FileChooserParams.parseResult(resultCode,data);
      fileCallback.onReceiveValue(result);
      fileCallback=null;
    }
  }

  void emitAsync(String kind,String detail){
    if(bridge==null)return;
    new Thread(()->bridge.event(kind,detail)).start();
  }
  @Override protected void onResume(){super.onResume();emitAsync("mobile_foreground","KRISHNA Mobile entered foreground");}
  @Override protected void onPause(){emitAsync("mobile_background","KRISHNA Mobile entered background");super.onPause();}

  public class Bridge {
    Bridge(){ensureCredential();deviceId();}
    String token(){return getSharedPreferences("k",0).getString("device_credential","");}
    String credentialHash()throws Exception{
      byte[] digest=java.security.MessageDigest.getInstance("SHA-256").digest(token().getBytes("UTF-8"));
      StringBuilder s=new StringBuilder();for(byte b:digest)s.append(String.format(java.util.Locale.US,"%02x",b&255));return s.toString();
    }
    void ensureCredential(){
      if(token().isEmpty()){
        String id=java.util.UUID.randomUUID().toString()+"-"+java.util.UUID.randomUUID().toString();
        getSharedPreferences("k",0).edit().putString("device_credential",id).apply();
      }
    }
    @JavascriptInterface public String status(){return call("/api/status",null);}
    @JavascriptInterface public String connection(){return call("/api/mobile/connection",null);}
    @JavascriptInterface public String resume(long after){
      String raw=call("/api/mobile/resume?after="+after,null);
      try{
        JSONObject d=new JSONObject(raw);JSONArray a=d.optJSONArray("events");
        if(a!=null)for(int i=0;i<a.length();i++){
          JSONObject e=a.getJSONObject(i);
          if("task.completed".equals(e.optString("type"))){
            JSONObject p=e.optJSONObject("payload");if(p!=null)notifyCompleted(p.optString("summary","KRISHNA completed the task"));
          }
        }
      }catch(Exception ignored){}
      return raw;
    }
    @JavascriptInterface public String pairingRequest(){
      try{
        JSONObject b=new JSONObject();b.put("device_id",deviceId());b.put("name","KRISHNA Mobile");b.put("credential_sha256",credentialHash());
        return callUnauthed("/api/mobile/pair/request",b.toString());
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public void savePairingToken(String value){
      if(value!=null&&!value.isEmpty())getSharedPreferences("k",0).edit().putString("device_credential",value).apply();
    }
    @JavascriptInterface public String event(String kind,String detail){
      return call("/api/core/event","{\"source\":\"mobile\",\"kind\":"+JSONObject.quote(kind)+",\"detail\":"+JSONObject.quote(detail)+",\"project\":\"system\"}");
    }
    @JavascriptInterface public String state(){return call("/api/core/state",null);}

    @JavascriptInterface public String hawkeyeLearnCapture(String utterance,String sourceType,String sourceRef,String modalitiesJson,String subject,String analysis,double confidence,String evidenceState,String audioObservationsJson){
      try{
        JSONObject body=new JSONObject();
        body.put("utterance",utterance==null?"":utterance);
        body.put("source_type",sourceType==null?"mobile":sourceType);
        body.put("source_ref",sourceRef==null?"":sourceRef);
        body.put("modalities",new JSONArray(modalitiesJson==null||modalitiesJson.trim().isEmpty()?"[]":modalitiesJson));
        body.put("subject",subject==null?"":subject);
        body.put("analysis",analysis==null?"":analysis);
        body.put("confidence",Math.max(0,Math.min(1,confidence)));
        body.put("evidence_state",evidenceState==null?"UNKNOWN":evidenceState);
        body.put("audio_observations",new JSONObject(audioObservationsJson==null||audioObservationsJson.trim().isEmpty()?"{}":audioObservationsJson));
        return call("/api/hawkeye/learn/capture",body.toString());
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeMode(){
      try{
        JSONObject d=new JSONObject();
        boolean pc=false;
        try{JSONObject x=new JSONObject(connection());pc=!x.has("error")&&x.optBoolean("connected",false);}catch(Exception ignored){}
        d.put("mode",pc?"HAWKEYE_LOCAL":"HAWKEYE_FIELD");
        d.put("pc_connected",pc);
        d.put("internet_required",false);
        d.put("field_capture_local",true);
        return d.toString();
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String hawkeyeOfflineFrame(String sessionId,String dataB64,String contentType,String sensorJson,String goal){
      try{
        File dir=new File(getFilesDir(),"hawkeye-field");if(!dir.exists()&&!dir.mkdirs())throw new IOException("cannot create Hawkeye field store");
        String safe=(sessionId==null?"field":sessionId).replaceAll("[^A-Za-z0-9_-]","_");
        File sd=new File(dir,safe);if(!sd.exists()&&!sd.mkdirs())throw new IOException("cannot create Hawkeye session");
        long now=System.currentTimeMillis();
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);
        try(FileOutputStream out=new FileOutputStream(new File(sd,now+".jpg"))){out.write(bytes);}
        JSONObject meta=new JSONObject();meta.put("timestamp_ms",now);meta.put("goal",goal==null?"":goal);
        meta.put("content_type",contentType==null?"image/jpeg":contentType);
        meta.put("sensor_context",new JSONObject(sensorJson==null||sensorJson.trim().isEmpty()?"{}":sensorJson));
        try(FileOutputStream out=new FileOutputStream(new File(sd,now+".json"))){out.write(meta.toString(2).getBytes("UTF-8"));}
        JSONObject d=new JSONObject();d.put("ok",true);d.put("mode","HAWKEYE_FIELD");d.put("stored_local",true);
        d.put("analysis","Offline field capture saved. Core AI analysis will sync when KRISHNA is reachable; on-device model adapters can replace this capture-only fallback.");
        return d.toString();
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String bhumiputraStart(String purpose,String sceneHint){
      try{
        JSONObject body=new JSONObject();
        body.put("project","KRISHNA");
        body.put("purpose",purpose==null||purpose.trim().isEmpty()?"live field scan":purpose.trim());
        body.put("scene_hint",sceneHint==null||sceneHint.trim().isEmpty()?"auto":sceneHint.trim());
        return call("/api/bhumiputra/live/start",body.toString());
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String bhumiputraFrame(String sessionId,String dataB64,String contentType,String sensorJson,String goal){
      try{
        JSONObject body=new JSONObject();
        body.put("session_id",sessionId);
        body.put("data_b64",dataB64);
        body.put("content_type",contentType==null||contentType.isEmpty()?"image/jpeg":contentType);
        body.put("goal",goal==null?"":goal);
        JSONObject sensors=new JSONObject(sensorJson==null||sensorJson.trim().isEmpty()?"{}":sensorJson);
        body.put("sensor_context",sensors);
        return call("/api/bhumiputra/live/frame",body.toString());
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String bhumiputraState(String sessionId){
      try{return call("/api/bhumiputra/live/state?session_id="+URLEncoder.encode(sessionId,"UTF-8"),null);}
      catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String ensureChat(){
      try{
        android.content.SharedPreferences p=getSharedPreferences("k",0);
        String project=p.getString("active_project","KRISHNA");
        if(project==null||project.trim().isEmpty()||"general".equalsIgnoreCase(project))project="KRISHNA";
        String chatId=p.getString("active_chat","");
        if(!chatId.isEmpty()){
          JSONObject ok=new JSONObject();ok.put("ok",true);ok.put("project",project);ok.put("chat_id",chatId);return ok.toString();
        }
        JSONObject body=new JSONObject();body.put("project",project);body.put("title","KRISHNA Mobile");
        JSONObject made=new JSONObject(call("/api/chats/create",body.toString()));
        if(made.has("error"))return made.toString();
        chatId=made.optString("chat_id","");
        if(chatId.isEmpty())throw new IllegalStateException("Core did not return a chat id");
        p.edit().putString("active_project",project).putString("active_chat",chatId).apply();
        JSONObject ok=new JSONObject();ok.put("ok",true);ok.put("project",project);ok.put("chat_id",chatId);return ok.toString();
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String chat(String m){return chatWithAttachments(m,"[]");}
    @JavascriptInterface public String chatWithAttachments(String m,String attachmentIdsJson){
      try{
        JSONObject ready=new JSONObject(ensureChat());if(ready.has("error"))return ready.toString();
        String project=ready.optString("project","KRISHNA"),chatId=ready.optString("chat_id","");
        JSONArray ids=new JSONArray(attachmentIdsJson==null?"[]":attachmentIdsJson);
        if(ids.length()>3)throw new IllegalArgumentException("at most 3 attachments per request");
        JSONObject body=new JSONObject();body.put("message",m);body.put("project",project);body.put("chat_id",chatId);body.put("source","mobile");body.put("mode","chat");body.put("attachment_ids",ids);
        return call(CORE,body.toString());
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String attach(String name,String contentType,String dataB64){
      try{
        JSONObject ready=new JSONObject(ensureChat());if(ready.has("error"))return ready.toString();
        JSONObject body=new JSONObject();body.put("chat_id",ready.optString("chat_id"));body.put("name",name);body.put("content_type",contentType);body.put("data_b64",dataB64);
        return call("/api/attachments",body.toString());
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public void log(String e){call("/api/mobile-log","{\"event\":"+JSONObject.quote(e)+"}");}

    @JavascriptInterface public boolean voiceEnrolled(){
      String fp=getSharedPreferences("k",0).getString("voiceprint","");
      return fp.startsWith("v3:");
    }
    @JavascriptInterface public String enrollVoice(){
      try{
        String fp=VoicePrint.capture(MainActivity.this,3200);
        getSharedPreferences("k",0).edit().putString("voiceprint",fp).putString("speaker_engine",SPEAKER_ENGINE).putBoolean("voice_enrolled",true).apply();
        event("voice_enrolled","Local owner voice gate enrolled; device authentication remains authoritative");
        return "{\"ok\":true,\"engine\":\""+SPEAKER_ENGINE+"\",\"security_authority\":\"device_credential\"}";
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String verifyVoice(){
      try{
        String enrolled=getSharedPreferences("k",0).getString("voiceprint","");
        if(!enrolled.startsWith("v3:"))return "{\"error\":\"owner voice gate is not enrolled\"}";
        String sample=VoicePrint.capture(MainActivity.this,1800);
        double score=VoicePrint.similarity(enrolled,sample);
        boolean matched=score>=0.58;
        event(matched?"voice_gate_matched":"voice_gate_rejected","Local owner voice gate score "+String.format(java.util.Locale.US,"%.3f",score));
        JSONObject d=new JSONObject();d.put("matched",matched);d.put("score",score);d.put("security_authority","device_credential");return d.toString();
      }catch(Exception e){return error(e);}
    }

    boolean secureCloudUrl(String value){
      try{
        URI u=new URI(value);
        return "https".equalsIgnoreCase(u.getScheme()) && u.getHost()!=null && u.getUserInfo()==null;
      }catch(Exception ignored){return false;}
    }
    @JavascriptInterface public String configureCloudUrl(String value){
      try{
        value=value==null?"":value.trim().replaceAll("/+$","");
        if(!value.isEmpty()&&!secureCloudUrl(value))throw new SecurityException("Cloud gateway must use HTTPS");
        getSharedPreferences("k",0).edit().putString("cloud_url",value).apply();
        JSONObject d=new JSONObject();d.put("ok",true);d.put("cloud_url",value);d.put("authority","not-a-mobile-control-route");d.put("note","Public cloud URLs are never used for KRISHNA Mobile device-authenticated Core control.");return d.toString();
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String cloudUrl(){return getSharedPreferences("k",0).getString("cloud_url","");}

    boolean privateCoreUrl(String value){
      try{
        URI u=new URI(value);String scheme=u.getScheme(),host=u.getHost();
        if(host==null||(!"http".equalsIgnoreCase(scheme)&&!"https".equalsIgnoreCase(scheme)))return false;
        String h=host.toLowerCase(java.util.Locale.US);
        if("localhost".equals(h)||h.endsWith(".ts.net"))return true;
        InetAddress ip=InetAddress.getByName(host);
        if(ip.isLoopbackAddress()||ip.isSiteLocalAddress()||ip.isLinkLocalAddress())return true;
        byte[] b=ip.getAddress();
        if(b.length==4){
          int a=b[0]&255,d=b[1]&255;
          if(a==100&&d>=64&&d<=127)return true; // Tailscale/CGNAT overlay range
        }else if(b.length==16){
          int a=b[0]&255;
          if((a&0xfe)==0xfc)return true; // IPv6 ULA
        }
      }catch(Exception ignored){}
      return false;
    }
    String discoverLanCore(){
      DatagramSocket s=null;
      try{
        s=new DatagramSocket();s.setBroadcast(true);s.setSoTimeout(1200);
        byte[] q="KRISHNA_DISCOVER_V1".getBytes("UTF-8");
        s.send(new DatagramPacket(q,q.length,InetAddress.getByName("255.255.255.255"),8767));
        byte[] buf=new byte[1024];DatagramPacket p=new DatagramPacket(buf,buf.length);s.receive(p);
        JSONObject d=new JSONObject(new String(p.getData(),0,p.getLength(),"UTF-8"));
        if(!"KRISHNA_CORE".equals(d.optString("service")))return "";
        int port=d.optInt("port",8766);
        String host=p.getAddress().getHostAddress();
        String candidate="http://"+host+":"+port;
        if(!privateCoreUrl(candidate))return "";
        getSharedPreferences("k",0).edit().putString("core_url",candidate).apply();
        return candidate;
      }catch(Exception ignored){return "";}
      finally{if(s!=null)s.close();}
    }
    String coreBase()throws Exception{
      String base=getSharedPreferences("k",0).getString("core_url","").trim();
      if(base.isEmpty())base=discoverLanCore();
      if(base.isEmpty())
        throw new IllegalStateException("KRISHNA Core is unreachable. Use LAN or an approved private overlay such as Tailscale.");
      if(!privateCoreUrl(base))
        throw new SecurityException("Core URL is outside KRISHNA private-network policy");
      return base.replaceAll("/+$","");
    }
    @JavascriptInterface public String configureCoreUrl(String value){
      try{
        value=value==null?"":value.trim();
        if(!privateCoreUrl(value))throw new SecurityException("KRISHNA Mobile accepts only LAN/private-overlay Core URLs");
        value=value.replaceAll("/+$","");
        getSharedPreferences("k",0).edit().putString("core_url",value).apply();
        JSONObject d=new JSONObject();d.put("ok",true);d.put("core_url",value);d.put("policy","private-network-only");return d.toString();
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String coreUrl(){
      try{return coreBase();}catch(Exception e){return "";}
    }
    HttpURLConnection conn(String path)throws Exception{
      String base=coreBase();
      HttpURLConnection c=(HttpURLConnection)new URL(base+path).openConnection();
      c.setConnectTimeout(4000);c.setReadTimeout(120000);
      c.setRequestProperty("Authorization","Device "+token());
      c.setRequestProperty("X-Krishna-Device",deviceId());
      c.setRequestProperty("Accept","application/json");
      return c;
    }
    String callUnauthed(String path,String body){
      try{
        String base=coreBase();
        HttpURLConnection c=(HttpURLConnection)new URL(base+path).openConnection();
        c.setConnectTimeout(4000);c.setReadTimeout(10000);c.setRequestProperty("X-Krishna-Device",deviceId());
        c.setRequestMethod("POST");c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");
        try(OutputStream out=c.getOutputStream()){out.write(body.getBytes("UTF-8"));}
        return read(c);
      }catch(Exception e){return error(e);}
    }
    String call(String path,String body){
      try{
        HttpURLConnection c=conn(path);
        if(body!=null){c.setRequestMethod("POST");c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");try(OutputStream out=c.getOutputStream()){out.write(body.getBytes("UTF-8"));}}
        return read(c);
      }catch(Exception e){return error(e);}
    }
    String read(HttpURLConnection c)throws Exception{
      try{
        int code=c.getResponseCode();
        InputStream source=code<400?c.getInputStream():c.getErrorStream();
        if(source==null)return "{\"error\":\"HTTP "+code+" returned no response body\"}";
        try(InputStream in=source;ByteArrayOutputStream o=new ByteArrayOutputStream()){
          byte[]b=new byte[8192];for(int n;(n=in.read(b))>0;)o.write(b,0,n);return o.toString("UTF-8");
        }
      }finally{c.disconnect();}
    }
    String error(Exception e){return "{\"error\":"+JSONObject.quote(e.getClass().getSimpleName()+": "+String.valueOf(e.getMessage()))+"}";}
  }
}

class VoicePrint{
  static String capture(Context c,int ms)throws Exception{
    int rate=16000,bs=AudioRecord.getMinBufferSize(rate,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);
    AudioRecord a=new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,rate,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,Math.max(bs,4096));
    short[]b=new short[1024];long end=System.currentTimeMillis()+ms;double eSum=0,zSum=0,pSum=0,e2=0;int frames=0;
    try{
      a.startRecording();
      while(System.currentTimeMillis()<end){
        int n=a.read(b,0,b.length);if(n<=1)continue;
        double energy=0,peak=0,z=0;
        for(int i=0;i<n;i++){double v=Math.abs((double)b[i])/32768.0;energy+=v;if(v>peak)peak=v;if(i>0&&((b[i]>=0)!=(b[i-1]>=0)))z++;}
        double e=energy/n,zc=z/(n-1);eSum+=e;zSum+=zc;pSum+=peak;e2+=e*e;frames++;
      }
    }finally{try{a.stop();}catch(Exception ignored){}a.release();}
    if(frames<4)throw new IllegalStateException("not enough voice audio");
    double meanE=eSum/frames,meanZ=zSum/frames,meanP=pSum/frames,varE=Math.sqrt(Math.max(0,e2/frames-meanE*meanE));
    return String.format(java.util.Locale.US,"v3:%.6f,%.6f,%.6f,%.6f",meanE,meanZ,meanP,varE);
  }
  static double similarity(String enrolled,String sample){
    double[]a=parse(enrolled),b=parse(sample);if(a==null||b==null)return 0;
    double de=rel(a[0],b[0],.025),dz=Math.min(1,Math.abs(a[1]-b[1])/.18),dp=rel(a[2],b[2],.08),dv=rel(a[3],b[3],.018);
    double distance=.32*de+.34*dz+.18*dp+.16*dv;
    return Math.max(0,1-Math.min(1,distance));
  }
  static double rel(double a,double b,double floor){return Math.min(1,Math.abs(a-b)/Math.max(floor,Math.max(Math.abs(a),Math.abs(b))));}
  static double[] parse(String s){
    try{if(s==null||!s.startsWith("v3:"))return null;String[]p=s.substring(3).split(",");if(p.length!=4)return null;return new double[]{Double.parseDouble(p[0]),Double.parseDouble(p[1]),Double.parseDouble(p[2]),Double.parseDouble(p[3])};}
    catch(Exception e){return null;}
  }
}