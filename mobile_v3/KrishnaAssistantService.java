package com.krishna.mobile;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.*;
import android.service.voice.VoiceInteractionService;
import android.speech.*;
import java.util.ArrayList;
import java.util.Locale;

/**
 * System assistant entry point for KRISHNA Mobile.
 *
 * Android keeps the selected VoiceInteractionService available for assistant/hotword
 * work. KRISHNA still uses only the OS on-device recognizer and does not treat wake
 * detection as authentication.
 */
public final class KrishnaAssistantService extends VoiceInteractionService implements RecognitionListener {
  SpeechRecognizer recognizer;
  Handler handler;
  boolean listening=false,stopping=false;
  long cooldownUntil=0L;

  @Override public void onReady(){
    super.onReady();
    stopping=false;
    handler=new Handler(Looper.getMainLooper());
    startWake();
  }

  @Override public void onShutdown(){
    stopWake();
    super.onShutdown();
  }

  void startWake(){
    if(stopping||listening||System.currentTimeMillis()<cooldownUntil)return;
    if(Build.VERSION.SDK_INT<31||!SpeechRecognizer.isOnDeviceRecognitionAvailable(this))return;
    if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)return;
    try{
      if(recognizer==null){
        recognizer=SpeechRecognizer.createOnDeviceSpeechRecognizer(this);
        recognizer.setRecognitionListener(this);
      }
      Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
      i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
      i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,true);
      i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,getSharedPreferences("k",0).getString("wake_lang","or-IN"));
      i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,5);
      recognizer.startListening(i);
      listening=true;
      getSharedPreferences("krishna_wake",0).edit().putString("state","ASSISTANT_LISTENING").putLong("at",System.currentTimeMillis()).apply();
    }catch(Exception e){scheduleRestart(2200);}
  }

  void inspect(Bundle results){
    if(results==null)return;
    ArrayList<String> xs=results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
    if(xs==null)return;
    for(String raw:xs){
      String s=raw==null?"":raw.toLowerCase(Locale.ROOT).trim();
      if(!(s.contains("krishna")||s.contains("କୃଷ୍ଣ")||s.contains("कृष्ण")))continue;
      cooldownUntil=System.currentTimeMillis()+12000L;
      listening=false;
      try{recognizer.stopListening();}catch(Exception ignored){}
      Bundle args=new Bundle();
      args.putString("phrase",raw==null?"Krishna":raw);
      args.putString("mode",KrishnaWakeService.commandMode(raw));
      args.putBoolean("wake_is_authentication",false);
      showSession(args,0);
      scheduleRestart(12000L);
      return;
    }
  }

  void scheduleRestart(long delay){
    listening=false;
    if(stopping||handler==null)return;
    handler.removeCallbacksAndMessages(null);
    handler.postDelayed(()->{if(!stopping)startWake();},Math.max(800L,delay));
  }

  void stopWake(){
    stopping=true;listening=false;
    if(handler!=null)handler.removeCallbacksAndMessages(null);
    if(recognizer!=null){
      try{recognizer.cancel();}catch(Exception ignored){}
      try{recognizer.destroy();}catch(Exception ignored){}
      recognizer=null;
    }
  }

  @Override public void onReadyForSpeech(Bundle params){}
  @Override public void onBeginningOfSpeech(){}
  @Override public void onRmsChanged(float rmsdB){}
  @Override public void onBufferReceived(byte[] buffer){}
  @Override public void onEndOfSpeech(){listening=false;scheduleRestart(900);}
  @Override public void onError(int error){listening=false;scheduleRestart(error==SpeechRecognizer.ERROR_RECOGNIZER_BUSY?1800:900);}
  @Override public void onResults(Bundle results){inspect(results);listening=false;scheduleRestart(900);}
  @Override public void onPartialResults(Bundle partialResults){inspect(partialResults);}
  @Override public void onEvent(int eventType,Bundle params){}
}
