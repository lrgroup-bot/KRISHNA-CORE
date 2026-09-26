package com.krishna.mobile;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.*;
import android.speech.*;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Locale;

/**
 * Local-only always-listening wake service.
 * Uses Android's on-device SpeechRecognizer when the OS exposes one.
 * Wake detection is activation only; owner voice/device authorization remains separate.
 */
public final class KrishnaWakeService extends Service implements RecognitionListener {
  public static final String ACTION_WAKE="com.krishna.mobile.KRISHNA_WAKE";
  public static final String ACTION_START="com.krishna.mobile.KRISHNA_WAKE_START";
  public static final String ACTION_STOP="com.krishna.mobile.KRISHNA_WAKE_STOP";
  static final String CHANNEL="krishna_wake";
  SpeechRecognizer recognizer;
  Handler handler;
  boolean listening=false,stopping=false;
  long cooldownUntil=0L;

  @Override public void onCreate(){
    super.onCreate();handler=new Handler(Looper.getMainLooper());ensureChannel();
  }

  void ensureChannel(){
    if(Build.VERSION.SDK_INT>=26){
      NotificationManager n=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
      n.createNotificationChannel(new NotificationChannel(CHANNEL,"KRISHNA wake word",NotificationManager.IMPORTANCE_LOW));
    }
  }
  Notification notification(String text){
    Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,CHANNEL):new Notification.Builder(this);
    return b.setSmallIcon(android.R.drawable.ic_btn_speak_now).setContentTitle("KRISHNA listening").setContentText(text).setOngoing(true).build();
  }

  public static String commandMode(String raw){
    String s=raw==null?"":raw.toLowerCase(Locale.ROOT).trim();
    boolean photo=s.contains("photo")||s.contains("picture")||s.contains("selfie")||
      s.contains("capture me")||s.contains("take my")||s.contains("फोटो")||s.contains("तस्वीर")||
      s.contains("ଫଟୋ")||s.contains("ମୋ ଫଟୋ");
    if(photo)return "photographer";
    boolean see=s.contains(" dekh")||s.contains("dekho")||s.contains("देख")||s.contains("ଦେଖ")||
      s.contains("watch")||s.contains("see")||s.contains("look")||s.contains("camera")||s.contains("hawkeye");
    if(see)return "hawkeye";
    return "chat";
  }

  public static JSONObject capability(Context c){
    JSONObject o=new JSONObject();
    try{
      boolean perm=Build.VERSION.SDK_INT<23||c.checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED;
      boolean onDevice=Build.VERSION.SDK_INT>=31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(c);
      o.put("engine","ANDROID_ON_DEVICE_SPEECH_RECOGNIZER");
      o.put("record_audio_permission",perm);
      o.put("on_device_recognition",onDevice);
      o.put("local_only",true);
      o.put("wake_phrases",new org.json.JSONArray().put("Krishna").put("କୃଷ୍ଣ").put("कृष्ण"));
      o.put("direct_camera_examples",new org.json.JSONArray().put("Krishna dekh").put("watch Krishna").put("see Krishna"));
      o.put("photographer_examples",new org.json.JSONArray().put("Krishna take my photo").put("Krishna photo"));
      o.put("wake_is_authentication",false);
      o.put("available",perm&&onDevice);
      o.put("state",c.getSharedPreferences("krishna_wake",0).getString("state","STOPPED"));
    }catch(Exception e){try{o.put("available",false);o.put("error",e.getMessage());}catch(Exception ignored){}}
    return o;
  }

  @Override public int onStartCommand(Intent intent,int flags,int startId){
    String action=intent==null?ACTION_START:intent.getAction();
    if(ACTION_STOP.equals(action)){stopWake();stopSelf();return START_NOT_STICKY;}
    if(Build.VERSION.SDK_INT<31||!SpeechRecognizer.isOnDeviceRecognitionAvailable(this)){
      state("UNAVAILABLE_ON_DEVICE");stopSelf();return START_NOT_STICKY;
    }
    if(Build.VERSION.SDK_INT>=23&&checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){
      state("MIC_PERMISSION_REQUIRED");stopSelf();return START_NOT_STICKY;
    }
    startForeground(0x4b57,notification("Local wake word · activation only"));
    startWake();
    return START_STICKY;
  }

  void startWake(){
    if(stopping||listening||System.currentTimeMillis()<cooldownUntil)return;
    try{
      if(recognizer==null){
        recognizer=SpeechRecognizer.createOnDeviceSpeechRecognizer(this);
        recognizer.setRecognitionListener(this);
      }
      Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
      i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
      i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,true);
      String lang=getSharedPreferences("k",0).getString("wake_lang","or-IN");
      i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,lang);
      i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,5);
      recognizer.startListening(i);listening=true;state("LISTENING");
    }catch(Exception e){state("ERROR:"+e.getClass().getSimpleName());scheduleRestart(2500);}
  }

  void inspect(Bundle results){
    if(results==null)return;
    ArrayList<String> xs=results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
    if(xs==null)return;
    for(String raw:xs){
      String s=raw==null?"":raw.toLowerCase(Locale.ROOT).trim();
      if(s.contains("krishna")||s.contains("କୃଷ୍ଣ")||s.contains("कृष्ण")){
        cooldownUntil=System.currentTimeMillis()+18000L;
        state("WAKE_DETECTED");
        try{recognizer.stopListening();}catch(Exception ignored){}
        listening=false;
        Intent wake=new Intent(ACTION_WAKE);wake.setPackage(getPackageName());wake.putExtra("phrase",raw);wake.putExtra("mode",commandMode(raw));sendBroadcast(wake);
        scheduleRestart(18000L);
        return;
      }
    }
  }

  void scheduleRestart(long delay){
    listening=false;
    if(stopping)return;
    handler.removeCallbacksAndMessages(null);
    handler.postDelayed(()->{if(!stopping)startWake();},Math.max(800,delay));
  }
  void state(String s){getSharedPreferences("krishna_wake",0).edit().putString("state",s).putLong("at",System.currentTimeMillis()).apply();}

  void stopWake(){
    stopping=true;listening=false;handler.removeCallbacksAndMessages(null);
    if(recognizer!=null){try{recognizer.cancel();}catch(Exception ignored){}try{recognizer.destroy();}catch(Exception ignored){}recognizer=null;}
    state("STOPPED");
  }
  @Override public void onDestroy(){stopWake();super.onDestroy();}
  @Override public IBinder onBind(Intent intent){return null;}

  @Override public void onReadyForSpeech(Bundle p){state("LISTENING");}
  @Override public void onBeginningOfSpeech(){}
  @Override public void onRmsChanged(float rmsdB){}
  @Override public void onBufferReceived(byte[] buffer){}
  @Override public void onEndOfSpeech(){listening=false;scheduleRestart(900);}
  @Override public void onError(int error){listening=false;scheduleRestart(error==SpeechRecognizer.ERROR_RECOGNIZER_BUSY?1800:900);}
  @Override public void onResults(Bundle results){inspect(results);listening=false;scheduleRestart(900);}
  @Override public void onPartialResults(Bundle partialResults){inspect(partialResults);}
  @Override public void onEvent(int eventType,Bundle params){}
}
