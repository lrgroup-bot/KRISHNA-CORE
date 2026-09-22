package com.krishna.mobile;

import android.content.Context;
import android.os.BatteryManager;
import android.os.PowerManager;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Lightweight deterministic Hawkeye evidence curator.
 * It does not run a vision model. It decides what is worth retaining/syncing,
 * rate-limits PC work, and deletes phone evidence only after PC acknowledgement.
 */
public final class HawkeyeEvidenceCuratorBot {
  public interface Uploader { JSONObject upload(JSONObject meta,byte[] jpeg)throws Exception; }

  static final long MOBILE_MAX_BYTES=128L*1024L*1024L;
  static final int MOBILE_MAX_ITEMS=48;
  static final long MOBILE_MAX_AGE_MS=24L*60L*60L*1000L;
  static final long KEEP_INTERVAL_MS=10_000L;
  static final long SYNC_INTERVAL_MS=12_000L;
  static final long LOW_POWER_SYNC_INTERVAL_MS=30_000L;

  private final Context context;
  private long lastSyncMs=0L;

  public HawkeyeEvidenceCuratorBot(Context context){this.context=context.getApplicationContext();}

  public synchronized JSONObject captureAndMaybeSync(String sessionId,byte[] jpeg,JSONObject sensors,
                                                     double quality,double novelty,String goal,Uploader uploader)throws Exception{
    long now=System.currentTimeMillis();String session=safe(sessionId);
    android.content.SharedPreferences prefs=context.getSharedPreferences("hawkeye_curator",0);
    long lastKeep=prefs.getLong("keep_"+session,0L);
    boolean first=lastKeep==0L;
    boolean important=importantGoal(goal);
    boolean usable=quality>=0.35;
    boolean enoughGap=now-lastKeep>=KEEP_INTERVAL_MS;
    boolean novel=novelty>=(important?0.055:0.085);
    boolean keep=usable&&(first||(enoughGap&&(novel||important&&quality>=0.55)));

    JSONObject decision=new JSONObject();
    decision.put("bot","HawkeyeEvidenceCuratorBot");decision.put("quality",clamp01(quality));
    decision.put("novelty",clamp01(novelty));decision.put("selected",keep);
    decision.put("policy","local-first-bounded-sync");

    if(keep){
      JSONObject enriched=sensors==null?new JSONObject():new JSONObject(sensors.toString());
      enriched.put("curator_selected",true);enriched.put("curator_quality",clamp01(quality));
      enriched.put("curator_novelty",clamp01(novelty));enriched.put("curator_goal",goal==null?"":goal);
      JSONObject meta=HawkeyeEdgeMemory.remember(context,session,"frame",jpeg,enriched,quality,"OBSERVED",
          important?"goal-relevant selected evidence":"novel selected evidence");
      prefs.edit().putLong("keep_"+session,now).apply();
      decision.put("observation_id",meta.optString("observation_id"));
    }else{
      decision.put("discarded_immediately",true);
      decision.put("reason",usable?(enoughGap?"low_novelty":"keep_interval"):"low_quality");
    }

    decision.put("storage",HawkeyeEdgeMemory.enforceBudget(context,MOBILE_MAX_BYTES,MOBILE_MAX_ITEMS,MOBILE_MAX_AGE_MS));
    JSONObject sync=syncOne(uploader);
    if(sync.optBoolean("pc_acknowledged",false)){
      sync.put("curator",decision);return sync;
    }
    decision.put("sync",sync);
    JSONObject out=new JSONObject();out.put("ok",true);out.put("stored_local",keep);
    out.put("curator",decision);out.put("pc_acknowledged",false);
    out.put("analysis",keep?"Selected evidence saved on mobile; curator will sync one bounded item when permitted."
                           :"Low-value frame discarded on mobile to protect storage and battery.");
    return out;
  }

  public synchronized JSONObject syncOne(Uploader uploader)throws Exception{
    JSONObject out=new JSONObject();out.put("bot","HawkeyeEvidenceCuratorBot");
    long now=System.currentTimeMillis(),interval=lowPower()?LOW_POWER_SYNC_INTERVAL_MS:SYNC_INTERVAL_MS;
    if(now-lastSyncMs<interval){out.put("status","rate_limited");out.put("next_after_ms",interval-(now-lastSyncMs));return out;}
    JSONArray pending=HawkeyeEdgeMemory.pending(context,1);
    if(pending.length()==0){out.put("status","empty");return out;}
    JSONObject meta=pending.getJSONObject(0);byte[] jpeg=HawkeyeEdgeMemory.imageBytes(context,meta);
    lastSyncMs=now;
    JSONObject response;
    try{response=uploader.upload(meta,jpeg);}
    catch(Exception e){out.put("status","pc_unreachable");out.put("retained_local",true);out.put("error",e.getClass().getSimpleName()+": "+String.valueOf(e.getMessage()));return out;}
    if(response==null)response=new JSONObject();
    if(response.has("error")){
      out.put("status","pc_rejected");out.put("retained_local",true);out.put("error",response.optString("error"));return out;
    }
    boolean deleted=HawkeyeEdgeMemory.acknowledge(context,meta.optString("observation_id"));
    response.put("pc_acknowledged",true);response.put("mobile_deleted_after_ack",deleted);
    response.put("mobile_observation_id",meta.optString("observation_id"));
    response.put("mobile_storage",HawkeyeEdgeMemory.stats(context));
    return response;
  }

  public JSONObject status()throws Exception{
    JSONObject out=HawkeyeEdgeMemory.stats(context);out.put("bot","HawkeyeEvidenceCuratorBot");
    out.put("mobile_max_bytes",MOBILE_MAX_BYTES);out.put("mobile_max_items",MOBILE_MAX_ITEMS);
    out.put("pending_ttl_ms",MOBILE_MAX_AGE_MS);out.put("keep_interval_ms",KEEP_INTERVAL_MS);
    out.put("sync_interval_ms",SYNC_INTERVAL_MS);out.put("low_power_sync_interval_ms",LOW_POWER_SYNC_INTERVAL_MS);
    out.put("heavy_model_on_phone",false);out.put("max_sync_items_per_tick",1);return out;
  }

  private boolean lowPower(){
    try{
      BatteryManager bm=(BatteryManager)context.getSystemService(Context.BATTERY_SERVICE);
      PowerManager pm=(PowerManager)context.getSystemService(Context.POWER_SERVICE);
      int battery=bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
      return battery>0&&battery<=20||pm.isPowerSaveMode();
    }catch(Exception e){return false;}
  }
  private static boolean importantGoal(String goal){
    String s=String.valueOf(goal==null?"":goal).toLowerCase(java.util.Locale.US);
    String[] terms={"diagnos","fault","circuit","pcb","motherboard","vehicle","truck","car","bus","bike","machine","motor","bearing","damage","broken","error"};
    for(String t:terms)if(s.contains(t))return true;return false;
  }
  private static double clamp01(double v){return Math.max(0,Math.min(1,v));}
  private static String safe(String s){return (s==null||s.isEmpty()?"field":s).replaceAll("[^A-Za-z0-9_-]","_");}
}
