package com.krishna.mobile;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.PowerManager;
import android.util.Base64;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * KRISHNA mobile-first edge orchestrator.
 *
 * Policy:
 *  - preprocess and retain evidence on the phone first;
 *  - never stream full-resolution camera frames by default;
 *  - deduplicate and rate-limit repeated observations;
 *  - keep routine semantic reasoning on verified zero-cost mobile cloud when allowed;
 *  - send only a compact frame/evidence packet to the PC for private/protected/heavy/failure escalation;
 *  - defer PC traffic under battery, thermal, memory, or network pressure.
 *
 * The phone is the acquisition/filtering/evidence worker and may use the direct
 * free-cloud router for non-sensitive reasoning. KRISHNA PC is an escalation
 * worker and authority boundary, not the default inference destination.
 */
public final class MobileEdgeBot {
  public static final String BOT_ID="KRISHNA_EDGE_BOT_V1";
  private static final String PREF="krishna_edge_bot";
  private static final long DEDUPE_WINDOW_MS=30000L;
  private static final long BUDGET_WINDOW_MS=60000L;

  private MobileEdgeBot(){}

  public static final class PreparedFrame {
    public final JSONObject result;
    public final byte[] uploadBytes;
    PreparedFrame(JSONObject result,byte[] uploadBytes){
      this.result=result;
      this.uploadBytes=uploadBytes;
    }
  }

  public static JSONObject status(Context c)throws Exception{
    JSONObject profile=HawkeyeDeviceProfiler.profile(c);
    JSONObject network=network(c);
    JSONObject policy=policy(profile,network);
    JSONObject out=new JSONObject();
    out.put("bot",BOT_ID);
    out.put("architecture","mobile-local-free-cloud-first-selective-pc");
    out.put("mobile_role","capture-filter-compress-dedupe-retain-free-cloud");
    out.put("pc_role","private-protected-heavy-failure-escalation-only");
    out.put("routine_cloud_role","verified-zero-price-direct-mobile");
    out.put("device",profile);
    out.put("network",network);
    out.put("policy",policy);
    out.put("raw_streaming_default",false);
    out.put("local_evidence_first",true);
    return out;
  }

  public static int recommendedSamplingMs(Context c){
    try{
      JSONObject s=status(c);
      return s.getJSONObject("policy").optInt("sampling_ms",6000);
    }catch(Exception e){return 8000;}
  }

  public static PreparedFrame prepareFrame(Context c,String session,byte[] jpeg,JSONObject sensors,String goal)throws Exception{
    if(jpeg==null||jpeg.length==0)throw new IllegalArgumentException("empty frame");

    JSONObject profile=HawkeyeDeviceProfiler.profile(c);
    JSONObject network=network(c);
    JSONObject p=policy(profile,network);
    int targetBytes=p.getInt("frame_target_bytes");
    int maxDimension=p.getInt("frame_max_dimension");
    int quality=p.getInt("jpeg_quality");
    int samplingMs=p.getInt("sampling_ms");

    byte[] compact=compactJpeg(jpeg,maxDimension,quality,targetBytes);
    String hash=sha256(compact);
    long now=System.currentTimeMillis();
    SharedPreferences prefs=c.getSharedPreferences(PREF,0);
    String lastHash=prefs.getString("last_hash","");
    long lastHashAt=prefs.getLong("last_hash_at",0);
    long lastUpload=prefs.getLong("last_upload_at",0);

    boolean duplicate=hash.equals(lastHash)&&(now-lastHashAt)<DEDUPE_WINDOW_MS;
    boolean rateLimited=(now-lastUpload)<samplingMs;
    boolean pcReachable=network.optBoolean("connected",false);
    boolean pressure=p.optBoolean("pressure",false);

    JSONObject remembered=HawkeyeEdgeMemory.remember(
      c,session,"edge-frame",compact,sensors,1.0,
      "OBSERVED",
      "KRISHNA mobile edge preprocessing; goal="+(goal==null?"":goal)
    );

    String route;
    byte[] upload=null;
    if(duplicate){
      route="LOCAL_DEDUP";
    }else if(rateLimited){
      route="LOCAL_RATE_LIMIT";
    }else if(pressure){
      route="LOCAL_DEFER";
    }else if(!pcReachable){
      route="LOCAL_OFFLINE";
    }else{
      route="PC_COMPACT_ESCALATION";
      upload=compact;
      prefs.edit().putLong("last_upload_at",now).apply();
    }

    prefs.edit().putString("last_hash",hash).putLong("last_hash_at",now).apply();

    JSONObject r=new JSONObject();
    r.put("ok",true);
    r.put("bot",BOT_ID);
    r.put("route",route);
    r.put("stored_local",true);
    r.put("observation_id",remembered.optString("observation_id"));
    r.put("original_bytes",jpeg.length);
    r.put("optimized_bytes",compact.length);
    r.put("saved_bytes",Math.max(0,jpeg.length-compact.length));
    r.put("traffic_reduction_percent",jpeg.length==0?0:Math.max(0,100.0-(compact.length*100.0/jpeg.length)));
    r.put("duplicate",duplicate);
    r.put("rate_limited",rateLimited);
    r.put("sampling_ms",samplingMs);
    r.put("network",network);
    r.put("policy",p);
    r.put("analysis",route.startsWith("PC_")
      ?"Mobile preprocessing complete; compact evidence selected for explicit PC escalation."
      :"Mobile preprocessing complete; evidence retained locally without PC transfer.");
    r.put("evidence_state","OBSERVED");
    r.put("confidence",1.0);
    return new PreparedFrame(r,upload);
  }

  private static JSONObject policy(JSONObject profile,JSONObject network)throws Exception{
    JSONObject compute=profile.getJSONObject("compute");
    JSONObject runtime=profile.getJSONObject("runtime");
    String deviceProfile=profile.optString("profile","LIGHT");
    boolean metered=network.optBoolean("metered",true);
    boolean connected=network.optBoolean("connected",false);
    boolean saver=runtime.optBoolean("power_save",false);
    boolean lowMem=compute.optBoolean("low_memory",false);
    int battery=runtime.optInt("battery_percent",100);
    int thermal=runtime.optInt("thermal_status",PowerManager.THERMAL_STATUS_NONE);

    boolean severeThermal=thermal>=PowerManager.THERMAL_STATUS_SEVERE;
    boolean pressure=saver||lowMem||battery<=15||severeThermal;

    int maxDimension=720;
    int quality=58;
    int targetBytes=metered?80*1024:160*1024;
    int samplingMs=metered?7000:5000;

    if("NANO".equals(deviceProfile)||pressure){
      maxDimension=480; quality=45; targetBytes=56*1024; samplingMs=12000;
    }else if("LIGHT".equals(deviceProfile)){
      maxDimension=640; quality=52; targetBytes=metered?64*1024:112*1024; samplingMs=metered?9000:6500;
    }else if("PERFORMANCE".equals(deviceProfile)&&!metered){
      maxDimension=960; quality=62; targetBytes=192*1024; samplingMs=4500;
    }

    if(!connected)samplingMs=Math.max(samplingMs,9000);

    JSONObject p=new JSONObject();
    p.put("profile",deviceProfile);
    p.put("pressure",pressure);
    p.put("frame_max_dimension",maxDimension);
    p.put("jpeg_quality",quality);
    p.put("frame_target_bytes",targetBytes);
    p.put("sampling_ms",samplingMs);
    p.put("max_pc_frames_per_minute",Math.max(1,60000/samplingMs));
    p.put("full_resolution_upload",false);
    p.put("metered_network",metered);
    p.put("battery_percent",battery);
    p.put("thermal_status",thermal);
    return p;
  }

  private static JSONObject network(Context c)throws Exception{
    JSONObject j=new JSONObject();
    ConnectivityManager cm=(ConnectivityManager)c.getSystemService(Context.CONNECTIVITY_SERVICE);
    Network n=cm==null?null:cm.getActiveNetwork();
    NetworkCapabilities cap=n==null||cm==null?null:cm.getNetworkCapabilities(n);
    boolean connected=cap!=null&&cap.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
    boolean metered=cm==null||cm.isActiveNetworkMetered();
    j.put("connected",connected);
    j.put("metered",metered);
    j.put("wifi",cap!=null&&cap.hasTransport(NetworkCapabilities.TRANSPORT_WIFI));
    j.put("cellular",cap!=null&&cap.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR));
    j.put("ethernet",cap!=null&&cap.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET));
    return j;
  }

  private static byte[] compactJpeg(byte[] src,int maxDimension,int quality,int targetBytes)throws Exception{
    BitmapFactory.Options bounds=new BitmapFactory.Options();
    bounds.inJustDecodeBounds=true;
    BitmapFactory.decodeByteArray(src,0,src.length,bounds);
    int max=Math.max(bounds.outWidth,bounds.outHeight);
    int sample=1;
    while(max/sample>Math.max(320,maxDimension*2))sample*=2;

    BitmapFactory.Options opts=new BitmapFactory.Options();
    opts.inSampleSize=Math.max(1,sample);
    Bitmap decoded=BitmapFactory.decodeByteArray(src,0,src.length,opts);
    if(decoded==null)return src.length<=targetBytes?src:trimFallback(src,targetBytes);

    Bitmap work=decoded;
    int w=decoded.getWidth(),h=decoded.getHeight();
    int currentMax=Math.max(w,h);
    if(currentMax>maxDimension){
      double scale=maxDimension/(double)currentMax;
      work=Bitmap.createScaledBitmap(decoded,Math.max(1,(int)Math.round(w*scale)),Math.max(1,(int)Math.round(h*scale)),true);
      if(work!=decoded)decoded.recycle();
    }

    byte[] out=compress(work,quality);
    int q=quality;
    while(out.length>targetBytes&&q>32){
      q-=6;
      out=compress(work,q);
    }
    if(out.length>targetBytes&&Math.max(work.getWidth(),work.getHeight())>480){
      double scale=480.0/Math.max(work.getWidth(),work.getHeight());
      Bitmap smaller=Bitmap.createScaledBitmap(work,Math.max(1,(int)Math.round(work.getWidth()*scale)),Math.max(1,(int)Math.round(work.getHeight()*scale)),true);
      if(smaller!=work)work.recycle();
      work=smaller;
      out=compress(work,Math.max(32,q));
    }
    work.recycle();
    return out;
  }

  private static byte[] compress(Bitmap b,int quality)throws Exception{
    ByteArrayOutputStream o=new ByteArrayOutputStream();
    if(!b.compress(Bitmap.CompressFormat.JPEG,Math.max(30,Math.min(75,quality)),o))
      throw new IllegalStateException("jpeg compression failed");
    return o.toByteArray();
  }

  private static byte[] trimFallback(byte[] src,int targetBytes){
    // Never truncate an encoded image into an invalid JPEG. Fallback keeps the
    // original bytes; caller still applies rate/defer policy.
    return src;
  }

  private static String sha256(byte[] b)throws Exception{
    byte[] d=MessageDigest.getInstance("SHA-256").digest(b);
    StringBuilder s=new StringBuilder();
    for(byte x:d)s.append(String.format(Locale.US,"%02x",x&255));
    return s.toString();
  }

  public static String encode(byte[] b){
    return Base64.encodeToString(b,Base64.NO_WRAP);
  }
}
