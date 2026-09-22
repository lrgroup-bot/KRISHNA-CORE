package com.krishna.mobile;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;

/**
 * Encrypted local-first Hawkeye evidence store.
 * Payload and metadata stay in app-private storage, encrypted with an Android-Keystore AES-GCM key.
 */
public final class HawkeyeEdgeMemory {
  private HawkeyeEdgeMemory(){}

  public static JSONObject remember(Context c,String session,String objectId,byte[] jpeg,JSONObject sensors,
                                    double quality,String evidenceState,String note)throws Exception{
    return rememberMedia(c,session,objectId,jpeg,"image/jpeg","image",sensors,quality,evidenceState,note);
  }

  public static JSONObject rememberMedia(Context c,String session,String objectId,byte[] payload,String contentType,String modality,
                                         JSONObject sensors,double quality,String evidenceState,String note)throws Exception{
    if(payload==null||payload.length==0)throw new IllegalArgumentException("empty Hawkeye evidence");
    String safe=safe(session);long now=System.currentTimeMillis();
    File dir=new File(c.getFilesDir(),"hawkeye-memory/"+safe);
    if(!dir.exists()&&!dir.mkdirs())throw new java.io.IOException("cannot create Hawkeye memory");
    String stem=now+"-"+safe(objectId)+"-"+safe(modality);
    File data=new File(dir,stem+".payload.enc");
    HawkeyeCrypto.encryptToFile(payload,data);
    JSONObject m=new JSONObject();
    m.put("observation_id","HAW-"+now+"-"+safe(objectId)+"-"+safe(modality));
    m.put("session_id",safe);m.put("object_id",safe(objectId));m.put("timestamp_ms",now);
    m.put("quality",clamp01(quality));m.put("evidence_state",validState(evidenceState));
    m.put("note",note==null?"":note);m.put("sensor_context",sensors==null?new JSONObject():sensors);
    m.put("payload_sha256",sha256(payload));m.put("payload_file",data.getName());m.put("payload_bytes",payload.length);
    m.put("content_type",cleanType(contentType));m.put("modality",safe(modality));
    m.put("sync_state","pending");m.put("retention","mobile_evidence_encrypted");
    m.put("encryption","AndroidKeyStore:AES-256-GCM");
    File meta=new File(dir,stem+".meta.enc");m.put("meta_file",meta.getName());
    HawkeyeCrypto.encryptToFile(m.toString().getBytes("UTF-8"),meta);
    return m;
  }

  public static JSONArray pending(Context c,int limit)throws Exception{
    JSONArray out=new JSONArray();ArrayList<File> files=metaFiles(c);
    files.sort(Comparator.comparingLong(File::lastModified));
    for(File f:files){
      if(out.length()>=Math.max(1,limit))break;
      try{
        JSONObject j=readMeta(f);
        if("pending".equals(j.optString("sync_state"))){j.put("meta_file",f.getName());out.put(j);}
      }catch(Exception ignored){}
    }
    return out;
  }

  public static byte[] payloadBytes(Context c,JSONObject meta)throws Exception{
    File f=payloadFile(c,meta);
    if(!f.isFile())throw new java.io.FileNotFoundException("Hawkeye evidence payload missing");
    byte[] raw=HawkeyeCrypto.decryptFile(f);
    String expected=meta.optString("payload_sha256","");
    if(!expected.isEmpty()&&!expected.equals(sha256(raw)))throw new SecurityException("Hawkeye evidence integrity mismatch");
    return raw;
  }

  public static byte[] imageBytes(Context c,JSONObject meta)throws Exception{return payloadBytes(c,meta);}

  public static boolean acknowledge(Context c,String observationId)throws Exception{
    String target=observationId==null?"":observationId.trim();if(target.isEmpty())return false;
    for(File f:metaFiles(c)){
      JSONObject j;
      try{j=readMeta(f);}catch(Exception ignored){continue;}
      if(!target.equals(j.optString("observation_id")))continue;
      File payload=payloadFile(c,j);
      boolean dataDeleted=!payload.exists()||payload.delete();
      boolean metaDeleted=f.delete();
      return dataDeleted&&metaDeleted;
    }
    return false;
  }

  public static JSONObject enforceBudget(Context c,long maxBytes,int maxItems,long maxAgeMs)throws Exception{
    long now=System.currentTimeMillis();ArrayList<File> files=metaFiles(c);
    files.sort(Comparator.comparingLong(File::lastModified));
    int expired=0,pruned=0;
    for(File f:new ArrayList<>(files)){
      if(maxAgeMs<=0||now-f.lastModified()<=maxAgeMs)continue;
      deletePair(c,f);expired++;files.remove(f);
    }
    while(files.size()>Math.max(1,maxItems)||diskBytes(c)>Math.max(8L*1024*1024,maxBytes)){
      if(files.isEmpty())break;
      File oldest=files.remove(0);deletePair(c,oldest);pruned++;
    }
    JSONObject s=stats(c);s.put("expired_deleted",expired);s.put("budget_pruned",pruned);
    s.put("max_bytes",maxBytes);s.put("max_items",maxItems);return s;
  }

  public static JSONObject stats(Context c)throws Exception{
    ArrayList<File> files=metaFiles(c);int pending=0;long bytes=0;
    for(File f:files){
      bytes+=f.length();
      try{
        JSONObject j=readMeta(f);
        if("pending".equals(j.optString("sync_state")))pending++;
        File payload=payloadFile(c,j);if(payload.isFile())bytes+=payload.length();
      }catch(Exception ignored){}
    }
    JSONObject out=new JSONObject();out.put("items",files.size());out.put("pending",pending);out.put("bytes",bytes);
    out.put("encrypted_at_rest",true);out.put("cipher","AES-256-GCM");out.put("key_store","AndroidKeyStore");
    out.put("root","internal-app-storage/hawkeye-memory");return out;
  }

  private static ArrayList<File> metaFiles(Context c){
    ArrayList<File> out=new ArrayList<>();File root=new File(c.getFilesDir(),"hawkeye-memory");
    if(root.exists())collectMeta(root,out);return out;
  }
  private static void collectMeta(File f,ArrayList<File> out){
    File[] fs=f.listFiles();if(fs==null)return;
    for(File x:fs){if(x.isDirectory())collectMeta(x,out);else if(x.getName().endsWith(".meta.enc"))out.add(x);}
  }
  private static JSONObject readMeta(File f)throws Exception{
    return new JSONObject(new String(HawkeyeCrypto.decryptFile(f),"UTF-8"));
  }
  private static File payloadFile(Context c,JSONObject meta){
    return new File(new File(c.getFilesDir(),"hawkeye-memory/"+safe(meta.optString("session_id"))),meta.optString("payload_file"));
  }
  private static void deletePair(Context c,File metaFile){
    try{JSONObject j=readMeta(metaFile);File payload=payloadFile(c,j);if(payload.exists())payload.delete();}catch(Exception ignored){}
    if(metaFile.exists())metaFile.delete();
  }
  private static long diskBytes(Context c){
    long total=0;File root=new File(c.getFilesDir(),"hawkeye-memory");ArrayList<File> all=new ArrayList<>();collectAll(root,all);
    for(File f:all)total+=f.length();return total;
  }
  private static void collectAll(File f,ArrayList<File> out){
    if(f==null||!f.exists())return;File[] fs=f.listFiles();if(fs==null)return;
    for(File x:fs){if(x.isDirectory())collectAll(x,out);else out.add(x);}
  }
  private static double clamp01(double v){return Math.max(0,Math.min(1,v));}
  private static String validState(String s){
    if("MEASURED".equals(s)||"OBSERVED".equals(s)||"INFERRED".equals(s)||"PREDICTED".equals(s)||"UNKNOWN".equals(s))return s;
    return "OBSERVED";
  }
  private static String cleanType(String s){
    String v=s==null?"application/octet-stream":s.split(";",2)[0].trim().toLowerCase(java.util.Locale.US);
    if(v.startsWith("image/")||v.startsWith("audio/")||v.startsWith("video/"))return v;
    return "application/octet-stream";
  }
  private static String safe(String s){return (s==null||s.isEmpty()?"unknown":s).replaceAll("[^A-Za-z0-9_-]","_");}
  private static String sha256(byte[] b)throws Exception{
    byte[] d=MessageDigest.getInstance("SHA-256").digest(b);StringBuilder s=new StringBuilder();
    for(byte x:d)s.append(String.format(java.util.Locale.US,"%02x",x&255));return s.toString();
  }
}
