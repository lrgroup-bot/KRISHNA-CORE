package com.krishna.mobile;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;

/**
 * Bounded on-device runtime healer for KRISHNA Mobile.
 *
 * Mrutyunjaya can recover volatile/runtime state only. He cannot rewrite the APK,
 * source code, credentials, permissions, security policy, or trusted device identity.
 */
public final class MrityunjayaMobileHealer {
  public static final String VERSION="mrityunjaya-mobile-v1";
  static final long COOLDOWN_MS=2500L;
  static final long BURST_WINDOW_MS=60000L;
  static final int MAX_HEALS_PER_WINDOW=4;
  static final long CIRCUIT_BREAK_MS=120000L;

  public interface Listener {
    void onState(String state,JSONObject snapshot);
  }

  final Context app;
  final SharedPreferences prefs;
  final Handler main=new Handler(Looper.getMainLooper());
  final Listener listener;
  final Map<String,Long> lastHealByKind=new HashMap<>();
  final ArrayDeque<Long> healTimes=new ArrayDeque<>();
  long circuitOpenUntil=0L;
  String pendingKind="";
  boolean healing=false;

  public MrityunjayaMobileHealer(Context context,Listener listener){
    this.app=context.getApplicationContext();
    this.listener=listener;
    this.prefs=app.getSharedPreferences("mrityunjaya_mobile",Context.MODE_PRIVATE);
    long saved=prefs.getLong("circuit_open_until",0L);
    circuitOpenUntil=Math.max(0L,saved);
  }

  static String clean(String value,int max){
    String s=value==null?"":value.replaceAll("[\\r\\n\\t]+"," ").trim();
    return s.length()>max?s.substring(0,max):s;
  }

  synchronized void prune(long now){
    while(!healTimes.isEmpty()&&now-healTimes.peekFirst()>BURST_WINDOW_MS)healTimes.removeFirst();
  }

  synchronized boolean circuitOpen(long now){
    if(circuitOpenUntil>0L&&now>=circuitOpenUntil){
      circuitOpenUntil=0L;
      prefs.edit().remove("circuit_open_until").apply();
    }
    return circuitOpenUntil>now;
  }

  synchronized JSONObject snapshot(String state,String note){
    JSONObject out=new JSONObject();
    try{
      long now=System.currentTimeMillis();
      prune(now);
      out.put("name","MRUTYUNJAYA");
      out.put("version",VERSION);
      out.put("state",state);
      out.put("healing",healing);
      out.put("pending_kind",pendingKind);
      out.put("note",clean(note,400));
      out.put("fault_count",prefs.getLong("fault_count",0L));
      out.put("heal_count",prefs.getLong("heal_count",0L));
      out.put("recovered_count",prefs.getLong("recovered_count",0L));
      out.put("failed_heal_count",prefs.getLong("failed_heal_count",0L));
      out.put("last_fault_kind",prefs.getString("last_fault_kind",""));
      out.put("last_fault_detail",prefs.getString("last_fault_detail",""));
      out.put("last_action",prefs.getString("last_action",""));
      out.put("last_event_at",prefs.getLong("last_event_at",0L));
      out.put("recent_heals",healTimes.size());
      out.put("circuit_open",circuitOpen(now));
      out.put("circuit_open_until",circuitOpenUntil);
      out.put("automatic",true);
      out.put("authority","runtime-recovery-only");
      out.put("source_mutation",false);
      out.put("security_policy_mutation",false);
      out.put("credential_mutation",false);
      out.put("apk_mutation",false);
      JSONArray scope=new JSONArray();
      scope.put("ui-shell").put("webview-renderer").put("javascript-runtime")
        .put("private-core-link").put("camera-session").put("volatile-mobile-state");
      out.put("recoverable_scope",scope);
    }catch(Exception ignored){}
    return out;
  }

  void emit(String state,String note){
    JSONObject snap=snapshot(state,note);
    Log.i("MRUTYUNJAYA_MOBILE",snap.toString());
    if(listener!=null)try{listener.onState(state,snap);}catch(Exception ignored){}
  }

  public synchronized JSONObject status(){
    return snapshot(healing?"HEALING":"HEALTHY","");
  }

  public synchronized void fault(String kind,String detail){
    long now=System.currentTimeMillis();
    String k=clean(kind,80),d=clean(detail,800);
    prefs.edit()
      .putLong("fault_count",prefs.getLong("fault_count",0L)+1L)
      .putString("last_fault_kind",k)
      .putString("last_fault_detail",d)
      .putLong("last_event_at",now)
      .apply();
    emit("FAULT",k+(d.isEmpty()?"":" · "+d));
  }

  public boolean recover(String kind,String detail,String action,Runnable repair){
    final long now=System.currentTimeMillis();
    final String k=clean(kind,80),a=clean(action,120);
    synchronized(this){
      fault(k,detail);
      prune(now);
      if(circuitOpen(now)){
        emit("SAFE_MODE","Recovery circuit is temporarily open");
        return false;
      }
      Long last=lastHealByKind.get(k);
      if(last!=null&&now-last<COOLDOWN_MS){
        emit("COOLDOWN",k);
        return false;
      }
      if(healTimes.size()>=MAX_HEALS_PER_WINDOW){
        circuitOpenUntil=now+CIRCUIT_BREAK_MS;
        prefs.edit().putLong("circuit_open_until",circuitOpenUntil).apply();
        emit("SAFE_MODE","Repeated recovery loop blocked");
        return false;
      }
      lastHealByKind.put(k,now);
      healTimes.addLast(now);
      healing=true;
      pendingKind=k;
      prefs.edit()
        .putLong("heal_count",prefs.getLong("heal_count",0L)+1L)
        .putString("last_action",a)
        .putLong("last_event_at",now)
        .apply();
    }
    emit("HEALING",a.isEmpty()?k:a);
    main.post(()->{
      try{
        if(repair!=null)repair.run();
      }catch(Throwable t){
        failed(k,t.getClass().getSimpleName()+": "+String.valueOf(t.getMessage()));
      }
    });
    return true;
  }

  public synchronized void recovered(String kind,String detail){
    String k=clean(kind,80);
    boolean matched=healing&&(pendingKind.isEmpty()||pendingKind.equals(k)||"ui-shell".equals(k));
    if(!matched){
      healthy(detail);
      return;
    }
    healing=false;
    pendingKind="";
    prefs.edit()
      .putLong("recovered_count",prefs.getLong("recovered_count",0L)+1L)
      .putString("last_action","verified-recovered:"+k)
      .putLong("last_event_at",System.currentTimeMillis())
      .apply();
    emit("RECOVERED",clean(detail,400));
  }

  public synchronized void failed(String kind,String detail){
    healing=false;
    pendingKind="";
    prefs.edit()
      .putLong("failed_heal_count",prefs.getLong("failed_heal_count",0L)+1L)
      .putString("last_action","recovery-failed:"+clean(kind,80))
      .putString("last_fault_detail",clean(detail,800))
      .putLong("last_event_at",System.currentTimeMillis())
      .apply();
    emit("FAILED",clean(detail,400));
  }

  public synchronized void healthy(String detail){
    if(!healing)emit("HEALTHY",clean(detail,240));
  }

  /** Android Studio/debug-only state reset; no credentials or KRISHNA identity are touched. */
  public synchronized JSONObject resetVolatileState(){
    lastHealByKind.clear();
    healTimes.clear();
    circuitOpenUntil=0L;
    healing=false;
    pendingKind="";
    prefs.edit().clear().apply();
    emit("HEALTHY","volatile healer state reset");
    return status();
  }
}
