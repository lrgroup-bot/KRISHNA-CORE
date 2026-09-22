package com.krishna.mobile;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;

/**
 * Local-first Hawkeye visual evidence store.
 * Raw visual evidence stays on the phone until the curator selects it and the PC acknowledges it.
 */
public final class HawkeyeEdgeMemory {
  private HawkeyeEdgeMemory(){}

  public static JSONObject remember(Context c,String session,String objectId,byte[] jpeg,JSONObject sensors,
                                    double quality,String evidenceState,String note)throws Exception{
    String safe=safe(session); long now=System.currentTimeMillis();
    File dir=new File(c.getFilesDir(),"hawkeye-memory/"+safe);
    if(!dir.exists()&&!dir.mkdirs())throw new java.io.IOException("cannot create Hawkeye memory");
    String stem=now+"-"+safe(objectId);
    File image=new File(dir,stem+".jpg");
    try(FileOutputStream o=new FileOutputStream(image)){o.write(jpeg);}
    JSONObject m=new JSONObject();
    m.put("observation_id","HAW-"+now+"-"+safe(objectId));
    m.put("session_id",safe);m.put("object_id",safe(objectId));m.put("timestamp_ms",now);
    m.put("quality",clamp01(quality));m.put("evidence_state",validState(evidenceState));
    m.put("note",note==null?"":note);m.put("sensor_context",sensors==null?new JSONObject():sensors);
    m.put("image_sha256",sha256(jpeg));m.put("image_file",image.getName());
    m.put("content_type","image/jpeg");m.put("sync_state","pending");m.put("retention","mobile_evidence");
    File meta=new File(dir,stem+".json");m.put("meta_file",meta.getName());
    try(FileOutputStream o=new FileOutputStream(meta)){o.write(m.toString(2).getBytes("UTF-8"));}
    return m;
  }

  public static JSONArray pending(Context c,int limit)throws Exception{
    JSONArray out=new JSONArray();ArrayList<File> files=jsonFiles(c);
    files.sort(Comparator.comparingLong(File::lastModified));
    for(File f:files){
      if(out.length()>=Math.max(1,limit))break;
      try{
        JSONObject j=readJson(f);
        if("pending".equals(j.optString("sync_state"))){j.put("meta_file",f.getName());out.put(j);}
      }catch(Exception ignored){}
    }
    return out;
  }

  public static byte[] imageBytes(Context c,JSONObject meta)throws Exception{
    File f=imageFile(c,meta);
    if(!f.isFile())throw new java.io.FileNotFoundException("Hawkeye evidence image missing");
    return java.nio.file.Files.readAllBytes(f.toPath());
  }

  public static boolean acknowledge(Context c,String observationId)throws Exception{
    String target=observationId==null?"":observationId.trim();if(target.isEmpty())return false;
    for(File f:jsonFiles(c)){
      JSONObject j;
      try{j=readJson(f);}catch(Exception ignored){continue;}
      if(!target.equals(j.optString("observation_id")))continue;
      File image=imageFile(c,j);
      boolean imageDeleted=!image.exists()||image.delete();
      boolean metaDeleted=f.delete();
      return imageDeleted&&metaDeleted;
    }
    return false;
  }

  public static JSONObject enforceBudget(Context c,long maxBytes,int maxItems,long maxAgeMs)throws Exception{
    long now=System.currentTimeMillis();ArrayList<File> files=jsonFiles(c);
    files.sort(Comparator.comparingLong(File::lastModified));
    int expired=0,pruned=0;
    for(File f:new ArrayList<>(files)){
      if(maxAgeMs<=0||now-f.lastModified()<=maxAgeMs)continue;
      deletePair(c,f);expired++;files.remove(f);
    }
    while(files.size()>Math.max(1,maxItems)||totalBytes(c)>Math.max(8L*1024*1024,maxBytes)){
      if(files.isEmpty())break;
      File oldest=files.remove(0);deletePair(c,oldest);pruned++;
    }
    JSONObject s=stats(c);s.put("expired_deleted",expired);s.put("budget_pruned",pruned);
    s.put("max_bytes",maxBytes);s.put("max_items",maxItems);return s;
  }

  public static JSONObject stats(Context c)throws Exception{
    ArrayList<File> files=jsonFiles(c);int pending=0;long bytes=0;
    for(File f:files){
      bytes+=f.length();
      try{
        JSONObject j=readJson(f);
        if("pending".equals(j.optString("sync_state")))pending++;
        File image=imageFile(c,j);if(image.isFile())bytes+=image.length();
      }catch(Exception ignored){}
    }
    JSONObject out=new JSONObject();out.put("items",files.size());out.put("pending",pending);out.put("bytes",bytes);
    out.put("root","internal-app-storage/hawkeye-memory");return out;
  }

  private static ArrayList<File> jsonFiles(Context c){
    ArrayList<File> out=new ArrayList<>();File root=new File(c.getFilesDir(),"hawkeye-memory");
    if(root.exists())collectJson(root,out);return out;
  }
  private static void collectJson(File f,ArrayList<File> out){
    File[] fs=f.listFiles();if(fs==null)return;
    for(File x:fs){if(x.isDirectory())collectJson(x,out);else if(x.getName().endsWith(".json"))out.add(x);}
  }
  private static JSONObject readJson(File f)throws Exception{
    return new JSONObject(new String(java.nio.file.Files.readAllBytes(f.toPath()),"UTF-8"));
  }
  private static File imageFile(Context c,JSONObject meta){
    return new File(new File(c.getFilesDir(),"hawkeye-memory/"+safe(meta.optString("session_id"))),meta.optString("image_file"));
  }
  private static void deletePair(Context c,File metaFile){
    try{JSONObject j=readJson(metaFile);File image=imageFile(c,j);if(image.exists())image.delete();}catch(Exception ignored){}
    if(metaFile.exists())metaFile.delete();
  }
  private static long totalBytes(Context c)throws Exception{return stats(c).optLong("bytes",0);}
  private static double clamp01(double v){return Math.max(0,Math.min(1,v));}
  private static String validState(String s){
    if("MEASURED".equals(s)||"OBSERVED".equals(s)||"INFERRED".equals(s)||"PREDICTED".equals(s)||"UNKNOWN".equals(s))return s;
    return "OBSERVED";
  }
  private static String safe(String s){return (s==null||s.isEmpty()?"unknown":s).replaceAll("[^A-Za-z0-9_-]","_");}
  private static String sha256(byte[] b)throws Exception{
    byte[] d=MessageDigest.getInstance("SHA-256").digest(b);StringBuilder s=new StringBuilder();
    for(byte x:d)s.append(String.format(java.util.Locale.US,"%02x",x&255));return s.toString();
  }
}
