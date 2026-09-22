package com.krishna.mobile;

import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.*;
import android.net.*;
import android.util.Base64;
import org.json.*;
import java.io.*;
import java.net.*;
import java.util.Locale;

/** Persistent, battery-aware one-item background sync. No capture and no model work occurs here. */
public final class HawkeyeBackgroundSync {
  public static final int JOB_ID=0x4b485931;
  private HawkeyeBackgroundSync(){}

  public static void schedule(Context c){
    try{
      JobScheduler js=(JobScheduler)c.getSystemService(Context.JOB_SCHEDULER_SERVICE);
      JobInfo job=new JobInfo.Builder(JOB_ID,new ComponentName(c,HawkeyeSyncJobService.class))
        .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
        .setRequiresBatteryNotLow(true)
        .setPeriodic(15L*60L*1000L)
        .build();
      js.schedule(job);
    }catch(Exception ignored){}
  }

  public static JSONObject syncOne(Context c)throws Exception{
    JSONArray pending=HawkeyeEdgeMemory.pending(c,1);JSONObject out=new JSONObject();
    if(pending.length()==0){out.put("status","empty");return out;}
    JSONObject meta=pending.getJSONObject(0);byte[] payload=HawkeyeEdgeMemory.payloadBytes(c,meta);
    JSONObject body=new JSONObject();body.put("session_id",meta.optString("session_id"));
    body.put("data_b64",Base64.encodeToString(payload,Base64.NO_WRAP));body.put("content_type",meta.optString("content_type","application/octet-stream"));
    body.put("modality",meta.optString("modality","unknown"));body.put("goal",meta.optJSONObject("sensor_context")==null?"":meta.optJSONObject("sensor_context").optString("curator_goal",""));
    JSONObject sensors=meta.optJSONObject("sensor_context");if(sensors==null)sensors=new JSONObject();sensors=new JSONObject(sensors.toString());
    sensors.put("mobile_observation_id",meta.optString("observation_id"));sensors.put("mobile_payload_sha256",meta.optString("payload_sha256"));sensors.put("curator_selected",true);
    body.put("sensor_context",sensors);
    JSONObject response=post(c,"/api/hawkeye/evidence/ingest",body);
    JSONObject receipt=response.optJSONObject("pc_evidence");
    if(receipt!=null&&receipt.optBoolean("retained_pc",false)){
      boolean deleted=HawkeyeEdgeMemory.acknowledge(c,meta.optString("observation_id"));
      response.put("pc_acknowledged",true);response.put("mobile_deleted_after_ack",deleted);return response;
    }
    response.put("retained_local",true);return response;
  }

  static JSONObject post(Context c,String path,JSONObject body)throws Exception{
    android.content.SharedPreferences p=c.getSharedPreferences("k",0);
    String base=p.getString("core_url","").trim().replaceAll("/+$","");
    if(base.isEmpty()||!privateCoreUrl(base))throw new SecurityException("approved private Core URL unavailable");
    HttpURLConnection h=(HttpURLConnection)new URL(base+path).openConnection();h.setConnectTimeout(4000);h.setReadTimeout(120000);
    h.setRequestMethod("POST");h.setDoOutput(true);h.setRequestProperty("Content-Type","application/json");h.setRequestProperty("Accept","application/json");
    h.setRequestProperty("Authorization","Device "+p.getString("device_credential",""));h.setRequestProperty("X-Krishna-Device",p.getString("device_id","android"));
    try(OutputStream o=h.getOutputStream()){o.write(body.toString().getBytes("UTF-8"));}
    try{
      int code=h.getResponseCode();InputStream source=code<400?h.getInputStream():h.getErrorStream();
      if(source==null)throw new IOException("Core returned HTTP "+code);
      ByteArrayOutputStream b=new ByteArrayOutputStream();try(InputStream in=source){byte[] buf=new byte[8192];for(int n;(n=in.read(buf))>0;)b.write(buf,0,n);}
      JSONObject result=new JSONObject(b.toString("UTF-8"));if(code>=400&&!result.has("error"))result.put("error","HTTP "+code);return result;
    }finally{h.disconnect();}
  }

  static boolean privateCoreUrl(String value){
    try{
      URI u=new URI(value);String scheme=u.getScheme(),host=u.getHost();if(host==null||(!"http".equalsIgnoreCase(scheme)&&!"https".equalsIgnoreCase(scheme)))return false;
      String h=host.toLowerCase(Locale.US);if("localhost".equals(h)||h.endsWith(".ts.net"))return true;
      InetAddress ip=InetAddress.getByName(host);if(ip.isLoopbackAddress()||ip.isSiteLocalAddress()||ip.isLinkLocalAddress())return true;
      byte[] b=ip.getAddress();if(b.length==4){int a=b[0]&255,d=b[1]&255;if(a==100&&d>=64&&d<=127)return true;}
      else if(b.length==16){int a=b[0]&255;if((a&0xfe)==0xfc)return true;}
    }catch(Exception ignored){}
    return false;
  }
}
