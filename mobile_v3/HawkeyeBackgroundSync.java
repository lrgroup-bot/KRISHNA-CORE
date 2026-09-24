package com.krishna.mobile;

import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.*;
import android.util.Base64;
import org.json.*;
import java.io.*;
import java.net.*;

/**
 * Resumable Hawkeye evidence sync.
 * Large media is never sent over metered/cellular transport. A paired private
 * Core is required, chunks resume by byte offset, and the PC must SHA-256 verify
 * the complete object before the phone marks its encrypted copy synced.
 */
public final class HawkeyeBackgroundSync {
  public static final int JOB_ID=0x4b485931;
  static final int CHUNK_BYTES=512*1024;
  private HawkeyeBackgroundSync(){}

  public static void schedule(Context c){
    try{
      JobScheduler js=(JobScheduler)c.getSystemService(Context.JOB_SCHEDULER_SERVICE);
      JobInfo job=new JobInfo.Builder(JOB_ID,new ComponentName(c,HawkeyeSyncJobService.class))
        .setRequiredNetworkType(JobInfo.NETWORK_TYPE_UNMETERED)
        .setRequiresBatteryNotLow(true)
        .setPeriodic(15L*60L*1000L)
        .build();
      js.schedule(job);
    }catch(Exception ignored){}
  }

  public static JSONObject syncOne(Context c)throws Exception{
    JSONObject out=new JSONObject();
    out.put("policy","trusted-unmetered-private-core");
    out.put("cellular_large_upload",false);
    out.put("delete_after_verified_default",false);

    if(!KrishnaPrivateCore.trustedLanReady(c)){
      out.put("status","WAITING_FOR_TRUSTED_LAN");
      out.put("retained_local",true);
      return out;
    }
    if(!KrishnaPrivateCore.batteryReady(c)){
      out.put("status","PAUSED_BATTERY");
      out.put("minimum_battery_percent",25);
      out.put("retained_local",true);
      return out;
    }

    android.content.SharedPreferences p=c.getSharedPreferences("k",0);
    String device=p.getString("device_id","");
    String credential=p.getString("device_credential","");
    if(device.isEmpty()||credential.isEmpty()){
      out.put("status","PAIRING_REQUIRED");out.put("retained_local",true);return out;
    }

    JSONObject bootstrap=KrishnaPrivateCore.bootstrap(c,device,credential);
    if(bootstrap.optInt("http_status",0)!=200){
      out.put("status","PAIRING_REQUIRED");out.put("retained_local",true);
      out.put("bootstrap",bootstrap);return out;
    }
    String base=KrishnaPrivateCore.resolve(c);

    JSONArray pending=HawkeyeEdgeMemory.pending(c,1);
    if(pending.length()==0){out.put("status","empty");return out;}
    JSONObject meta=pending.getJSONObject(0);
    byte[] payload=HawkeyeEdgeMemory.payloadBytes(c,meta);
    String observation=meta.optString("observation_id","");
    String contentType=meta.optString("content_type","application/octet-stream");
    String modality=meta.optString("modality","unknown");

    JSONObject startBody=new JSONObject();
    startBody.put("observation_id",observation);
    startBody.put("session_id",meta.optString("session_id","mobile-evidence"));
    startBody.put("filename",observation+suffix(contentType));
    startBody.put("size_bytes",payload.length);
    startBody.put("sha256",meta.optString("payload_sha256",""));
    startBody.put("content_type",contentType);
    startBody.put("modality",modality);
    JSONObject metadata=new JSONObject();
    metadata.put("sensor_context",meta.optJSONObject("sensor_context")==null?new JSONObject():meta.optJSONObject("sensor_context"));
    metadata.put("quality",meta.optDouble("quality",0));
    metadata.put("evidence_state",meta.optString("evidence_state","OBSERVED"));
    metadata.put("note",meta.optString("note",""));
    metadata.put("mobile_timestamp_ms",meta.optLong("timestamp_ms",0));
    startBody.put("metadata",metadata);

    JSONObject start=post(c,base,"/api/hawkeye/media-sync/start",startBody);
    if(start.has("error"))return retained(out,"pc_rejected",start.optString("error"));
    String uploadId=start.optString("upload_id","");
    if(uploadId.isEmpty())return retained(out,"pc_rejected","missing upload_id");

    long offset=start.optLong("next_offset",0);
    if(start.optBoolean("verified",false)&&start.optBoolean("retained_pc",false))
      return finalizeMobile(c,meta,start);

    while(offset<payload.length){
      int n=(int)Math.min((long)CHUNK_BYTES,(long)payload.length-offset);
      byte[] chunk=java.util.Arrays.copyOfRange(payload,(int)offset,(int)offset+n);
      JSONObject b=new JSONObject();
      b.put("upload_id",uploadId);b.put("offset",offset);
      b.put("data_b64",Base64.encodeToString(chunk,Base64.NO_WRAP));
      JSONObject r=post(c,base,"/api/hawkeye/media-sync/chunk",b);
      if(r.has("error"))return retained(out,"transfer_error",r.optString("error"));
      long next=r.optLong("next_offset",-1);
      if(next<0||next>payload.length)return retained(out,"transfer_error","invalid resume offset");
      if(next==offset)return retained(out,"transfer_error","PC made no transfer progress");
      offset=next;
    }

    JSONObject doneBody=new JSONObject();doneBody.put("upload_id",uploadId);
    JSONObject done=post(c,base,"/api/hawkeye/media-sync/complete",doneBody);
    if(done.has("error"))return retained(out,"verify_error",done.optString("error"));
    if(!done.optBoolean("verified",false)||!done.optBoolean("retained_pc",false))
      return retained(out,"VERIFYING","PC has not verified retention yet");
    return finalizeMobile(c,meta,done);
  }

  static JSONObject retained(JSONObject out,String status,String error)throws Exception{
    out.put("status",status);out.put("retained_local",true);
    if(error!=null&&!error.isEmpty())out.put("error",error);
    return out;
  }

  static JSONObject finalizeMobile(Context c,JSONObject meta,JSONObject response)throws Exception{
    boolean delete=c.getSharedPreferences("hawkeye_sync",0).getBoolean("delete_after_verified",false);
    String observation=meta.optString("observation_id","");
    String receipt=response.optString("pc_receipt_id",response.optString("upload_id",""));
    boolean localUpdated;
    if(delete)localUpdated=HawkeyeEdgeMemory.acknowledge(c,observation);
    else localUpdated=HawkeyeEdgeMemory.markSynced(c,observation,receipt);
    response.put("pc_acknowledged",true);
    response.put("mobile_deleted_after_ack",delete&&localUpdated);
    response.put("mobile_retained_after_ack",!delete&&localUpdated);
    response.put("delete_after_verified",delete);
    response.put("mobile_observation_id",observation);
    response.put("mobile_storage",HawkeyeEdgeMemory.stats(c));
    return response;
  }

  static JSONObject post(Context c,String base,String path,JSONObject body)throws Exception{
    if(!KrishnaPrivateCore.privateCoreUrl(base))throw new SecurityException("approved private Core URL unavailable");
    android.content.SharedPreferences p=c.getSharedPreferences("k",0);
    HttpURLConnection h=(HttpURLConnection)new URL(base+path).openConnection();
    h.setConnectTimeout(5000);h.setReadTimeout(120000);
    h.setRequestMethod("POST");h.setDoOutput(true);
    h.setRequestProperty("Content-Type","application/json");h.setRequestProperty("Accept","application/json");
    h.setRequestProperty("Authorization","Device "+p.getString("device_credential",""));
    h.setRequestProperty("X-Krishna-Device",p.getString("device_id","android"));
    try(OutputStream o=h.getOutputStream()){o.write(body.toString().getBytes("UTF-8"));}
    try{
      int code=h.getResponseCode();InputStream source=code<400?h.getInputStream():h.getErrorStream();
      if(source==null)throw new IOException("Core returned HTTP "+code);
      ByteArrayOutputStream b=new ByteArrayOutputStream();
      try(InputStream in=source){byte[] buf=new byte[8192];for(int n;(n=in.read(buf))>0;)b.write(buf,0,n);}
      JSONObject result=new JSONObject(b.toString("UTF-8"));
      if(code>=400&&!result.has("error"))result.put("error","HTTP "+code);
      result.put("http_status",code);return result;
    }finally{h.disconnect();}
  }

  static String suffix(String contentType){
    String t=contentType==null?"":contentType.toLowerCase(java.util.Locale.US);
    if(t.contains("jpeg"))return ".jpg";if(t.contains("png"))return ".png";if(t.contains("webp"))return ".webp";
    if(t.contains("mp4"))return ".mp4";if(t.contains("webm"))return ".webm";if(t.contains("ogg"))return ".ogg";
    return ".bin";
  }
}
