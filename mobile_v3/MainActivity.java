package com.krishna.mobile;

import android.app.*;
import android.app.role.RoleManager;
import android.os.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.webkit.*;
import android.media.*;
import android.net.Uri;
import android.util.Base64;
import android.location.*;
import android.provider.MediaStore;
import androidx.browser.customtabs.CustomTabsIntent;
import java.net.*;
import java.io.*;
import java.util.*;
import org.json.*;

public class MainActivity extends Activity {
  static final String CORE="/api/core/chat";
  static final String SPEAKER_ENGINE="LOCAL_VOICE_GATE_V3";
  static final int FILE_PICKER=73;
  static final int ASSISTANT_ROLE_REQUEST=74;
  public static final String ACTION_ASSIST_COMMAND="com.krishna.mobile.ASSIST_COMMAND";
  WebView web;
  Bridge bridge;
  HawkeyeSensorFusion hawkeyeSensors;
  ValueCallback<Uri[]> fileCallback;
  boolean webReady=false;
  String pendingAssistPhrase=null,pendingAssistMode=null;
  BroadcastReceiver wakeReceiver=new BroadcastReceiver(){
    @Override public void onReceive(Context context,Intent intent){
      if(intent==null||!KrishnaWakeService.ACTION_WAKE.equals(intent.getAction()))return;
      String phrase=intent.getStringExtra("phrase");
      String mode=intent.getStringExtra("mode");
      receiveAssistantCommand(mode,phrase);
    }
  };

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

  boolean assistantRoleHeld(){
    if(Build.VERSION.SDK_INT<29)return false;
    try{
      RoleManager rm=getSystemService(RoleManager.class);
      return rm!=null&&rm.isRoleAvailable(RoleManager.ROLE_ASSISTANT)&&rm.isRoleHeld(RoleManager.ROLE_ASSISTANT);
    }catch(Exception ignored){return false;}
  }

  void requestAssistantRole(boolean rememberPrompt){
    if(Build.VERSION.SDK_INT<29)return;
    try{
      RoleManager rm=getSystemService(RoleManager.class);
      if(rm==null||!rm.isRoleAvailable(RoleManager.ROLE_ASSISTANT)||rm.isRoleHeld(RoleManager.ROLE_ASSISTANT))return;
      if(rememberPrompt)getSharedPreferences("k",0).edit().putBoolean("assistant_role_prompted",true).apply();
      startActivityForResult(rm.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT),ASSISTANT_ROLE_REQUEST);
    }catch(Exception ignored){}
  }

  void maybeRequestAssistantRole(){
    if(getSharedPreferences("k",0).getBoolean("assistant_role_prompted",false))return;
    requestAssistantRole(true);
  }

  void receiveAssistantCommand(String mode,String phrase){
    pendingAssistMode=(mode==null||mode.trim().isEmpty())?"chat":mode.trim().toLowerCase(java.util.Locale.ROOT);
    pendingAssistPhrase=(phrase==null||phrase.trim().isEmpty())?"Krishna":phrase.trim();
    dispatchPendingAssistantCommand();
  }

  void dispatchPendingAssistantCommand(){
    if(!webReady||web==null||pendingAssistMode==null)return;
    final String mode=pendingAssistMode,phrase=pendingAssistPhrase==null?"Krishna":pendingAssistPhrase;
    pendingAssistMode=null;pendingAssistPhrase=null;
    runOnUiThread(()->web.evaluateJavascript(
      "window.onAssistantCommand&&window.onAssistantCommand("+JSONObject.quote(mode)+","+JSONObject.quote(phrase)+")",null));
  }

  void handleAssistIntent(Intent intent){
    if(intent==null||!ACTION_ASSIST_COMMAND.equals(intent.getAction()))return;
    receiveAssistantCommand(intent.getStringExtra("mode"),intent.getStringExtra("phrase"));
  }

  void startWakeIfReady(){
    if(assistantRoleHeld()){stopWakeService();return;}
    boolean enrolled=getSharedPreferences("k",0).getString("voiceprint","").startsWith("v3:");
    boolean mic=Build.VERSION.SDK_INT<23||checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED;
    if(!enrolled||!mic)return;
    Intent i=new Intent(this,KrishnaWakeService.class).setAction(KrishnaWakeService.ACTION_START);
    try{if(Build.VERSION.SDK_INT>=26)startForegroundService(i);else startService(i);}catch(Exception ignored){}
  }
  void stopWakeService(){
    try{
      Intent i=new Intent(this,KrishnaWakeService.class).setAction(KrishnaWakeService.ACTION_STOP);
      startService(i);
    }catch(Exception ignored){stopService(new Intent(this,KrishnaWakeService.class));}
  }

  @Override public void onCreate(Bundle b){
    super.onCreate(b);
    ensureNotifications();
    hawkeyeSensors=new HawkeyeSensorFusion(this);
    HawkeyeBackgroundSync.schedule(this);
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
      @Override public void onPageFinished(WebView view,String url){
        super.onPageFinished(view,url);
        webReady=true;
        dispatchPendingAssistantCommand();
      }
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
    IntentFilter wakeFilter=new IntentFilter(KrishnaWakeService.ACTION_WAKE);
    if(Build.VERSION.SDK_INT>=33)registerReceiver(wakeReceiver,wakeFilter,Context.RECEIVER_NOT_EXPORTED);
    else registerReceiver(wakeReceiver,wakeFilter);
    setContentView(web);
    handleAssistIntent(getIntent());
    web.loadUrl("file:///android_asset/index.html");
    new Handler(Looper.getMainLooper()).postDelayed(this::maybeRequestAssistantRole,900);
    startWakeIfReady();
  }

  @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
    super.onActivityResult(requestCode,resultCode,data);
    if(requestCode==ASSISTANT_ROLE_REQUEST){startWakeIfReady();return;}
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
  @Override protected void onResume(){super.onResume();getSharedPreferences("k",0).edit().putBoolean("activity_foreground",true).apply();emitAsync("mobile_foreground","KRISHNA Mobile entered foreground");startWakeIfReady();if(bridge!=null)new Thread(()->{bridge.autoBootstrap();bridge.hawkeyeSyncEvidence();},"krishna-mobile-resume").start();}
  @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);handleAssistIntent(intent);}
  @Override protected void onPause(){getSharedPreferences("k",0).edit().putBoolean("activity_foreground",false).apply();emitAsync("mobile_background","KRISHNA Mobile entered background");super.onPause();}
  @Override protected void onDestroy(){try{unregisterReceiver(wakeReceiver);}catch(Exception ignored){}try{if(hawkeyeSensors!=null)hawkeyeSensors.close();}catch(Exception ignored){}super.onDestroy();}

  public class Bridge {
    final HawkeyeEvidenceCuratorBot hawkeyeCurator;
    Bridge(){ensureCredential();deviceId();hawkeyeCurator=new HawkeyeEvidenceCuratorBot(MainActivity.this);new Thread(this::autoBootstrap,"krishna-auto-bootstrap").start();}
    void autoBootstrap(){
      try{
        JSONObject boot=KrishnaPrivateCore.bootstrap(MainActivity.this,deviceId(),token());
        int code=boot.optInt("http_status",0);
        if(code==401){
          JSONObject requested=new JSONObject(pairingRequest());
          if(!requested.has("error"))getSharedPreferences("k",0).edit().putString("pair_request_id",requested.optString("request_id","")).apply();
        }else if(code==200){
          getSharedPreferences("k",0).edit().putBoolean("paired_ready",true).remove("pair_request_id").apply();
        }
      }catch(Exception ignored){}
    }
    @JavascriptInterface public String bootstrapConnection(){
      try{
        JSONObject boot=KrishnaPrivateCore.bootstrap(MainActivity.this,deviceId(),token());
        if(boot.optInt("http_status",0)==401){
          JSONObject requested=new JSONObject(pairingRequest());
          boot.put("pairing_requested",!requested.has("error"));
          if(requested.has("request_id"))boot.put("request_id",requested.optString("request_id"));
        }
        return boot.toString();
      }catch(Exception e){return error(e);}
    }
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
    @JavascriptInterface public String hawkeyeSensorSnapshot(){
      try{return hawkeyeSensors==null?new JSONObject().put("available",false).toString():hawkeyeSensors.snapshot().toString();}
      catch(Exception e){return error(e);}
    }
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

    @JavascriptInterface public String edgeBotStatus(){
      try{return MobileEdgeBot.status(MainActivity.this).toString();}
      catch(Exception e){return error(e);}
    }
    @JavascriptInterface public int edgeSamplingMs(){
      return MobileEdgeBot.recommendedSamplingMs(MainActivity.this);
    }

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

    @JavascriptInterface public String hawkeyeObserveLearning(String payloadJson){
      try{
        JSONObject body=new JSONObject(payloadJson==null||payloadJson.trim().isEmpty()?"{}":payloadJson);
        return call("/api/hawkeye/learn/capture",body.toString());
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeResearchObservation(String observationId){
      try{
        final String oid=observationId==null?"":observationId.trim();
        if(oid.isEmpty())throw new IllegalArgumentException("observation_id is required");
        new Thread(()->{
          String raw;
          try{
            JSONObject body=new JSONObject();body.put("observation_id",oid);
            raw=call("/api/hawkeye/learn/research",body.toString());
          }catch(Exception e){
            try{raw=new JSONObject().put("error",e.getClass().getSimpleName()+": "+e.getMessage()).toString();}
            catch(Exception ignored){raw="{\"error\":\"HAWKEYE research failed\"}";}
          }
          final String result=raw;
          runOnUiThread(()->{
            try{
              web.evaluateJavascript(
                "window.HawkeyeObserverUI&&window.HawkeyeObserverUI.onResearchResult("+
                JSONObject.quote(result)+")",null
              );
            }catch(Exception ignored){}
          });
        },"hawkeye-rishi-research").start();
        return new JSONObject()
          .put("queued",true)
          .put("observation_id",oid)
          .put("raw_media_uploaded",false)
          .put("cloud_default","local_only")
          .toString();
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeDetectObjects(String dataB64){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);
        if(bytes.length>2*1024*1024)throw new IllegalArgumentException("local object frame exceeds 2 MB");
        return HawkeyeMobileVision.detect(bytes).toString();
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeRichPerception(String dataB64){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);
        if(bytes.length>3*1024*1024)throw new IllegalArgumentException("local rich-perception frame exceeds 3 MB");
        return HawkeyeMobileVision.analyzeRich(bytes).toString();
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeHandGesture(String dataB64){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);
        if(bytes.length==0||bytes.length>3*1024*1024)throw new IllegalArgumentException("hand gesture frame exceeds bounded size");
        return HawkeyeHandGesture.analyze(MainActivity.this,bytes).toString();
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeTranslateText(String text,String targetTag,boolean allowModelDownload){
      try{return HawkeyeLanguage.translate(text,targetTag,allowModelDownload).toString();}
      catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeFreeCloudStatus(){
      try{return call("/api/hawkeye/free-cloud/status",null);}
      catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeFreeCloudAnalyze(String dataB64,String contentType,String prompt,String metadataJson,String provider,String openrouterRole,String preferredModel,boolean includeReviews){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);
        if(bytes.length==0||bytes.length>4*1024*1024)throw new IllegalArgumentException("free-cloud keyframe must be 1 byte to 4 MB");
        JSONObject metadata=new JSONObject(metadataJson==null||metadataJson.trim().isEmpty()?"{}":metadataJson);
        if(!metadata.optBoolean("cloud_approved",false))throw new SecurityException("free-cloud mode requires explicit owner approval");
        metadata.put("selected_keyframe",true);
        JSONObject body=new JSONObject();
        body.put("data_b64",Base64.encodeToString(bytes,Base64.NO_WRAP));
        body.put("content_type",contentType==null||contentType.trim().isEmpty()?"image/jpeg":contentType);
        body.put("prompt",prompt==null?"":prompt);
        body.put("metadata",metadata);
        body.put("provider",provider==null||provider.trim().isEmpty()?"auto":provider.trim());
        body.put("openrouter_role",openrouterRole==null||openrouterRole.trim().isEmpty()?"hawkeye_vision":openrouterRole.trim());
        body.put("preferred_model",preferredModel==null?"":preferredModel.trim());
        body.put("include_reviews",includeReviews);
        return call("/api/hawkeye/free-cloud/analyze",body.toString());
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeFreeCloudFinding(String sessionId,String goal,String findingJson){
      try{
        JSONObject finding=new JSONObject(findingJson==null||findingJson.trim().isEmpty()?"{}":findingJson);
        String localSession=sessionId==null||sessionId.trim().isEmpty()?"field":sessionId.trim();
        String task=goal==null?"":goal.trim();
        String pcSession=resolvePcHawkeyeSession(localSession,task);
        JSONObject body=new JSONObject();
        body.put("session_id",pcSession);
        body.put("mobile_session_id",localSession);
        body.put("goal",task);
        body.put("finding",finding);
        JSONObject result=new JSONObject(call("/api/hawkeye/free-cloud/finding",body.toString()));
        if(!result.has("error")){
          result.put("mobile_session_id",localSession);
          result.put("pc_session_id",pcSession);
        }
        return result.toString();
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeGeminiStatus(){
      try{return call("/api/hawkeye/gemini/status",null);}
      catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeGeminiAnalyze(String dataB64,String contentType,String prompt,String metadataJson){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);
        if(bytes.length==0||bytes.length>4*1024*1024)throw new IllegalArgumentException("Gemini keyframe must be 1 byte to 4 MB");
        JSONObject metadata=new JSONObject(metadataJson==null||metadataJson.trim().isEmpty()?"{}":metadataJson);
        if(!metadata.optBoolean("cloud_approved",false))throw new SecurityException("Gemini mode requires explicit owner approval");
        metadata.put("selected_keyframe",true);
        JSONObject body=new JSONObject();
        body.put("data_b64",Base64.encodeToString(bytes,Base64.NO_WRAP));
        body.put("content_type",contentType==null||contentType.trim().isEmpty()?"image/jpeg":contentType);
        body.put("prompt",prompt==null?"":prompt);
        body.put("metadata",metadata);
        return call("/api/hawkeye/gemini/analyze",body.toString());
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeGeminiLiveToken(String metadataJson){
      try{
        JSONObject metadata=new JSONObject(metadataJson==null||metadataJson.trim().isEmpty()?"{}":metadataJson);
        if(!metadata.optBoolean("cloud_approved",false)||!metadata.optBoolean("user_explicit",false))
          throw new SecurityException("Gemini Live requires an explicit owner action");
        JSONObject body=new JSONObject();body.put("metadata",metadata);
        return call("/api/hawkeye/gemini/live/token",body.toString());
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String openResearchBrowser(String value){
      try{
        String url=value==null?"":value.trim();
        URI uri=new URI(url);
        if(!"https".equalsIgnoreCase(uri.getScheme())||uri.getHost()==null||uri.getUserInfo()!=null)
          throw new SecurityException("HAWKEYE research browser accepts HTTPS public URLs only");
        runOnUiThread(()->{
          try{
            CustomTabsIntent tab=new CustomTabsIntent.Builder().setShowTitle(true).build();
            tab.launchUrl(MainActivity.this,Uri.parse(url));
          }catch(Exception e){
            MainActivity.this.startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(url)));
          }
        });
        JSONObject out=new JSONObject();out.put("ok",true);out.put("url",url);
        out.put("browser","user-default-custom-tab");
        out.put("krishna_js_bridge_exposed",false);
        return out.toString();
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String openResearchQuery(String query){
      try{
        String q=query==null?"":query.trim();
        if(q.isEmpty())throw new IllegalArgumentException("research query is empty");
        String url="https://www.google.com/search?q="+URLEncoder.encode(q,"UTF-8");
        return openResearchBrowser(url);
      }catch(Exception e){return error(e);}
    }

    boolean sensitiveCaptureKey(String key){
      String k=String.valueOf(key==null?"":key).toLowerCase(java.util.Locale.US).replace("-","_").replace(" ","_");
      return k.contains("password")||k.equals("passwd")||k.equals("pwd")||k.equals("pin")||k.equals("otp")||
        k.contains("api_key")||k.contains("token")||k.contains("authorization")||k.contains("credential")||k.contains("secret");
    }

    String redactCaptureText(String value){
      String s=String.valueOf(value==null?"":value);
      s=s.replaceAll("(?i)(password|passwd|pwd|pin|otp|api[_ -]?key|access[_ -]?token|session[_ -]?token|authorization|credential|secret)\\s*[:=]\\s*[^\\s,;]+","$1: [SECRET REDACTED]");
      s=s.replaceAll("(?i)bearer\\s+[A-Za-z0-9._~+\\-/=]{4,}","Bearer [SECRET REDACTED]");
      String googleKeyPrefix="AI"+"za";
      s=s.replaceAll("\\b"+googleKeyPrefix+"[0-9A-Za-z_-]{20,}\\b","[SECRET REDACTED]");
      return s;
    }

    Object sanitizeCaptureMetadata(String key,Object value)throws Exception{
      if(value==null||value==JSONObject.NULL)return JSONObject.NULL;
      if(sensitiveCaptureKey(key))return "[SECRET REDACTED]";
      if(value instanceof JSONObject){
        JSONObject src=(JSONObject)value,dst=new JSONObject();
        java.util.Iterator<String> it=src.keys();
        while(it.hasNext()){
          String child=it.next();
          dst.put(child,sanitizeCaptureMetadata(child,src.opt(child)));
        }
        return dst;
      }
      if(value instanceof JSONArray){
        JSONArray src=(JSONArray)value,dst=new JSONArray();
        for(int i=0;i<src.length();i++)dst.put(sanitizeCaptureMetadata(key,src.opt(i)));
        return dst;
      }
      if(value instanceof String)return redactCaptureText((String)value);
      return value;
    }

    @JavascriptInterface public String saveHawkeyeCapture(String dataB64,String mimeType,String kind,String metadataJson){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);
        String type=mimeType==null?"":mimeType.split(";",2)[0].trim().toLowerCase(java.util.Locale.US);
        String k=kind==null?"image":kind.trim().toLowerCase(java.util.Locale.US);
        boolean image=k.equals("image")&&("image/jpeg".equals(type)||"image/png".equals(type)||"image/webp".equals(type));
        boolean video=k.equals("video")&&("video/mp4".equals(type)||"video/webm".equals(type));
        if(!image&&!video)throw new IllegalArgumentException("unsupported HAWKEYE capture type");
        int max=image?12*1024*1024:20*1024*1024;
        if(bytes.length==0||bytes.length>max)throw new IllegalArgumentException("HAWKEYE capture exceeds bounded size");

        String ext="image/png".equals(type)?".png":("image/webp".equals(type)?".webp":("video/mp4".equals(type)?".mp4":("video/webm".equals(type)?".webm":".jpg")));
        JSONObject metadata=(JSONObject)sanitizeCaptureMetadata("",new JSONObject(metadataJson==null||metadataJson.trim().isEmpty()?"{}":metadataJson));
        boolean photographer=image&&metadata.optBoolean("photographer_mode",false);
        String base=(photographer?"KRISHNA_PHOTO_":"KRISHNA_HAWKEYE_")+System.currentTimeMillis();
        metadata.put("saved_at",System.currentTimeMillis());
        metadata.put("raw_cloud_upload",false);
        metadata.put("privacy","user-requested local capture; no automatic cloud upload");

        // Keep a separate encrypted app-private sync record. Gallery storage is
        // user-visible; the sync copy is what can safely resume/verify later.
        JSONObject syncSensors=new JSONObject(metadata.toString());
        syncSensors.put("user_requested_capture",true);
        syncSensors.put("gallery_copy",true);
        syncSensors.put("sync_policy","same-lan-unmetered-resumable");
        JSONObject syncMeta=HawkeyeEdgeMemory.rememberMedia(
          MainActivity.this,
          "gallery-capture",
          base,
          bytes,
          type,
          image?"image":"video",
          syncSensors,
          1.0,
          "OBSERVED",
          "user-requested Hawkeye capture queued for verified PC sync"
        );
        HawkeyeEdgeMemory.enforceBudget(MainActivity.this,128L*1024L*1024L,48,24L*60L*60L*1000L);

        JSONObject out=new JSONObject();
        out.put("sync_observation_id",syncMeta.optString("observation_id"));
        out.put("sync_state","WAITING_FOR_TRUSTED_LAN");
        out.put("cellular_large_upload",false);
        if(Build.VERSION.SDK_INT>=29){
          android.content.ContentResolver resolver=getContentResolver();
          ContentValues cv=new ContentValues();
          cv.put(MediaStore.MediaColumns.DISPLAY_NAME,base+ext);
          cv.put(MediaStore.MediaColumns.MIME_TYPE,type);
          cv.put(MediaStore.MediaColumns.RELATIVE_PATH,(image?Environment.DIRECTORY_PICTURES:Environment.DIRECTORY_MOVIES)+"/KRISHNA/"+(photographer?"Photos":"HAWKEYE"));
          cv.put(MediaStore.MediaColumns.IS_PENDING,1);
          Uri collection=image?MediaStore.Images.Media.EXTERNAL_CONTENT_URI:MediaStore.Video.Media.EXTERNAL_CONTENT_URI;
          Uri uri=resolver.insert(collection,cv);
          if(uri==null)throw new IOException("MediaStore insert failed");
          try(OutputStream os=resolver.openOutputStream(uri)){if(os==null)throw new IOException("MediaStore stream unavailable");os.write(bytes);}
          cv.clear();cv.put(MediaStore.MediaColumns.IS_PENDING,0);resolver.update(uri,cv,null,null);

          Uri metaUri=null;
          if(!photographer){
            ContentValues side=new ContentValues();
            side.put(MediaStore.MediaColumns.DISPLAY_NAME,base+".json");
            side.put(MediaStore.MediaColumns.MIME_TYPE,"application/json");
            side.put(MediaStore.MediaColumns.RELATIVE_PATH,Environment.DIRECTORY_DOWNLOADS+"/KRISHNA/HAWKEYE");
            metaUri=resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI,side);
            if(metaUri!=null)try(OutputStream os=resolver.openOutputStream(metaUri)){if(os!=null)os.write(metadata.toString(2).getBytes("UTF-8"));}
          }
          out.put("uri",uri.toString());out.put("metadata_uri",metaUri==null?JSONObject.NULL:metaUri.toString());
          out.put("gallery_visible",true);out.put("photographer_mode",photographer);
        }else{
          File root=new File(getExternalFilesDir(image?Environment.DIRECTORY_PICTURES:Environment.DIRECTORY_MOVIES),"KRISHNA/"+(photographer?"Photos":"HAWKEYE"));
          if(!root.exists()&&!root.mkdirs())throw new IOException("capture directory unavailable");
          File media=new File(root,base+ext),meta=new File(root,base+".json");
          try(FileOutputStream os=new FileOutputStream(media)){os.write(bytes);}
          try(FileOutputStream os=new FileOutputStream(meta)){os.write(metadata.toString(2).getBytes("UTF-8"));}
          out.put("path",media.getAbsolutePath());out.put("metadata_path",meta.getAbsolutePath());out.put("gallery_visible",false);
        }
        out.put("ok",true);out.put("kind",k);out.put("mime_type",type);out.put("bytes",bytes.length);
        return out.toString();
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeMode(){
      try{
        JSONObject d=MobileEdgeBot.status(MainActivity.this);
        boolean pc=false;
        try{JSONObject x=new JSONObject(connection());pc=!x.has("error")&&x.optBoolean("connected",false);}catch(Exception ignored){}
        d.put("mode",pc?"HAWKEYE_EDGE_PC":"HAWKEYE_FIELD");
        d.put("pc_connected",pc);
        d.put("internet_required",false);
        d.put("field_capture_local",true);
        d.put("selective_pc_offload",true);
        return d.toString();
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String hawkeyeOfflineFrame(String sessionId,String dataB64,String contentType,String sensorJson,String goal){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);JSONObject sensors=new JSONObject(sensorJson==null||sensorJson.trim().isEmpty()?"{}":sensorJson);
        JSONObject local=HawkeyeOfflinePerception.analyze(MainActivity.this,sessionId,bytes);
        sensors.put("curator_selected",true);sensors.put("curator_goal",goal==null?"":goal);sensors.put("offline_capture",true);
        sensors.put("offline_perception",local);
        double quality="LOW".equals(local.optString("capture_quality"))?0.25:0.65;
        JSONObject meta=HawkeyeEdgeMemory.rememberMedia(MainActivity.this,sessionId,"offline-frame",bytes,contentType,"image",sensors,quality,"OBSERVED",local.optString("analysis","offline local probe"));
        HawkeyeEdgeMemory.enforceBudget(MainActivity.this,128L*1024L*1024L,48,24L*60L*60L*1000L);
        JSONObject d=new JSONObject();d.put("ok",true);d.put("mode","HAWKEYE_FIELD");d.put("stored_local",true);d.put("encrypted_at_rest",true);
        d.put("observation_id",meta.optString("observation_id"));d.put("offline_perception",local);
        d.put("analysis",local.optString("analysis")+" Encrypted evidence saved; bounded sync will retry when KRISHNA is reachable.");
        return d.toString();
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String bhumiputraStart(String purpose,String sceneHint){
      try{
        JSONObject body=new JSONObject();
        body.put("project","KRISHNA");
        body.put("purpose",purpose==null||purpose.trim().isEmpty()?"live field scan":purpose.trim());
        body.put("scene_hint",sceneHint==null||sceneHint.trim().isEmpty()?"auto":sceneHint.trim());
        String raw=call("/api/bhumiputra/live/start",body.toString());
        try{
          JSONObject d=new JSONObject(raw);String sid=d.optString("session_id","");
          if(!sid.isEmpty())getSharedPreferences("hawkeye_sync",0).edit().putString("pc_"+sid,sid).apply();
        }catch(Exception ignored){}
        return raw;
      }catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeCurateFrame(String sessionId,String dataB64,String contentType,String sensorJson,String goal,double quality,double novelty){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);
        if(bytes.length>2*1024*1024)throw new IllegalArgumentException("mobile curated frame exceeds 2 MB");
        JSONObject sensors=new JSONObject(sensorJson==null||sensorJson.trim().isEmpty()?"{}":sensorJson);
        final String type=contentType==null||contentType.isEmpty()?"image/jpeg":contentType;
        final String task=goal==null?"":goal;
        JSONObject out=hawkeyeCurator.captureAndMaybeSync(sessionId,bytes,sensors,quality,novelty,task,
          (meta,jpeg)->uploadCuratedEvidence(meta,jpeg,type,task));
        return out.toString();
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String hawkeyeCurateMedia(String sessionId,String dataB64,String contentType,String modality,String sensorJson,String goal,double quality){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);JSONObject sensors=new JSONObject(sensorJson==null||sensorJson.trim().isEmpty()?"{}":sensorJson);
        final String task=goal==null?"":goal;
        JSONObject out=hawkeyeCurator.captureMedia(sessionId,bytes,contentType,modality,sensors,quality,task,(meta,payload)->uploadCuratedEvidence(meta,payload,meta.optString("content_type",contentType),task));
        return out.toString();
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String hawkeyeSyncEvidence(){
      try{return HawkeyeBackgroundSync.syncOne(MainActivity.this).toString();}
      catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String hawkeyeEvidenceStatus(){
      try{return hawkeyeCurator.status().toString();}catch(Exception e){return error(e);}
    }

    @JavascriptInterface public String hawkeyeReference(String referenceId){
      try{return call("/api/hawkeye/reference/item?reference_id="+URLEncoder.encode(referenceId==null?"":referenceId,"UTF-8"),null);}
      catch(Exception e){return error(e);}
    }

    JSONObject uploadCuratedEvidence(JSONObject meta,byte[] payload,String contentType,String fallbackGoal)throws Exception{
      if(!KrishnaPrivateCore.trustedLanReady(MainActivity.this)){
        JSONObject held=new JSONObject();
        held.put("status","WAITING_FOR_TRUSTED_LAN");held.put("retained_local",true);
        held.put("cellular_large_upload",false);held.put("raw_cloud_upload",false);
        return held;
      }
      JSONObject sensors=meta.optJSONObject("sensor_context");if(sensors==null)sensors=new JSONObject();sensors=new JSONObject(sensors.toString());
      sensors.put("mobile_observation_id",meta.optString("observation_id"));sensors.put("mobile_payload_sha256",meta.optString("payload_sha256"));sensors.put("curator_selected",true);
      String localSession=meta.optString("session_id","field"),goal=sensors.optString("curator_goal",fallbackGoal==null?"":fallbackGoal),pcSession=resolvePcHawkeyeSession(localSession,goal);
      JSONObject body=new JSONObject();body.put("session_id",pcSession);body.put("data_b64",Base64.encodeToString(payload,Base64.NO_WRAP));
      body.put("content_type",contentType==null||contentType.isEmpty()?"application/octet-stream":contentType);body.put("modality",meta.optString("modality","unknown"));
      body.put("goal",goal);body.put("sensor_context",sensors);
      JSONObject result=new JSONObject(call("/api/hawkeye/evidence/ingest",body.toString()));
      if(result.has("error")&&result.optString("error").toLowerCase(java.util.Locale.US).contains("live session not found")){
        getSharedPreferences("hawkeye_sync",0).edit().remove("pc_"+localSession).apply();pcSession=createPcHawkeyeSession(localSession,goal);body.put("session_id",pcSession);
        result=new JSONObject(call("/api/hawkeye/evidence/ingest",body.toString()));
      }
      if(!result.has("error")){
        String returned=result.optString("pc_session_id",pcSession);
        if(!returned.isEmpty())getSharedPreferences("hawkeye_sync",0).edit().putString("pc_"+localSession,returned).apply();
        result.put("mobile_session_id",localSession);result.put("pc_session_id",returned);
      }return result;
    }
    String resolvePcHawkeyeSession(String localSession,String goal)throws Exception{
      android.content.SharedPreferences p=getSharedPreferences("hawkeye_sync",0);
      String mapped=p.getString("pc_"+localSession,"");if(!mapped.isEmpty())return mapped;
      if(localSession!=null&&!localSession.startsWith("offline-")){p.edit().putString("pc_"+localSession,localSession).apply();return localSession;}
      return createPcHawkeyeSession(localSession,goal);
    }
    String createPcHawkeyeSession(String localSession,String goal)throws Exception{
      JSONObject body=new JSONObject();body.put("project","KRISHNA");body.put("purpose",goal==null||goal.trim().isEmpty()?"mobile curated evidence":goal.trim());body.put("scene_hint","auto");
      JSONObject d=new JSONObject(call("/api/hawkeye/live/start",body.toString()));
      if(d.has("error"))throw new IOException(d.optString("error"));
      String sid=d.optString("session_id","");if(sid.isEmpty())throw new IOException("PC did not create Hawkeye session");
      getSharedPreferences("hawkeye_sync",0).edit().putString("pc_"+localSession,sid).apply();return sid;
    }

    @JavascriptInterface public String bhumiputraFrame(String sessionId,String dataB64,String contentType,String sensorJson,String goal){
      try{
        byte[] bytes=Base64.decode(dataB64,Base64.DEFAULT);
        JSONObject sensors=new JSONObject(sensorJson==null||sensorJson.trim().isEmpty()?"{}":sensorJson);
        MobileEdgeBot.PreparedFrame prepared=MobileEdgeBot.prepareFrame(MainActivity.this,sessionId,bytes,sensors,goal);
        JSONObject edge=prepared.result;
        if(prepared.uploadBytes==null)return edge.toString();

        JSONObject body=new JSONObject();
        body.put("session_id",sessionId);
        body.put("data_b64",MobileEdgeBot.encode(prepared.uploadBytes));
        body.put("content_type","image/jpeg");
        body.put("goal",goal==null?"":goal);
        body.put("sensor_context",sensors);
        body.put("edge_bot",MobileEdgeBot.BOT_ID);
        body.put("edge_policy",edge.optJSONObject("policy"));
        body.put("original_bytes",edge.optInt("original_bytes"));
        body.put("optimized_bytes",edge.optInt("optimized_bytes"));

        JSONObject pc=new JSONObject(call("/api/bhumiputra/live/frame",body.toString()));
        if(pc.has("error")){
          edge.put("route","LOCAL_PC_UNREACHABLE");
          edge.put("pc_error",pc.optString("error"));
          edge.put("analysis","PC analysis was unavailable; compact evidence remains stored on the mobile device.");
          return edge.toString();
        }
        pc.put("edge_bot",MobileEdgeBot.BOT_ID);
        pc.put("edge_route","PC_COMPACT");
        pc.put("original_bytes",edge.optInt("original_bytes"));
        pc.put("optimized_bytes",edge.optInt("optimized_bytes"));
        pc.put("traffic_reduction_percent",edge.optDouble("traffic_reduction_percent"));
        pc.put("stored_local",true);
        return pc.toString();
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
        startWakeIfReady();
        JSONObject out=new JSONObject();out.put("ok",true);out.put("engine",SPEAKER_ENGINE);out.put("security_authority","device_credential");
        out.put("wake",KrishnaWakeService.capability(MainActivity.this));return out.toString();
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String wakeStatus(){
      try{
        JSONObject out=KrishnaWakeService.capability(MainActivity.this);
        out.put("assistant_role_held",assistantRoleHeld());
        out.put("assistant_service","KrishnaAssistantService");
        out.put("background_direct_launch",assistantRoleHeld());
        return out.toString();
      }catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String assistantStatus(){
      try{return new JSONObject().put("available",Build.VERSION.SDK_INT>=29).put("role_held",assistantRoleHeld()).put("system_consent_required",true).toString();}
      catch(Exception e){return error(e);}
    }
    @JavascriptInterface public String requestAssistantMode(){
      requestAssistantRole(true);
      return assistantStatus();
    }
    @JavascriptInterface public String wakeStart(){
      startWakeIfReady();
      return wakeStatus();
    }
    @JavascriptInterface public String wakeStop(){
      stopWakeService();
      return wakeStatus();
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

    boolean privateCoreUrl(String value){return KrishnaPrivateCore.privateCoreUrl(value);}
    String discoverLanCore(){return KrishnaPrivateCore.discoverLan(MainActivity.this);}
    String coreBase()throws Exception{return KrishnaPrivateCore.resolve(MainActivity.this);}
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