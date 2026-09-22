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
 * Local-first Hawkeye visual working memory.
 * Stores compact observations/evidence metadata so the PC does not need every frame.
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
    m.put("session_id",safe); m.put("object_id",safe(objectId)); m.put("timestamp_ms",now);
    m.put("quality",Math.max(0,Math.min(1,quality)));
    m.put("evidence_state",validState(evidenceState));
    m.put("note",note==null?"":note);
    m.put("sensor_context",sensors==null?new JSONObject():sensors);
    m.put("image_sha256",sha256(jpeg)); m.put("image_file",image.getName());
    m.put("sync_state","pending"); m.put("retention","mobile_evidence");
    File meta=new File(dir,stem+".json");
    try(FileOutputStream o=new FileOutputStream(meta)){o.write(m.toString(2).getBytes("UTF-8"));}
    prune(dir,120);
    return m;
  }

  public static JSONArray pending(Context c,int limit)throws Exception{
    JSONArray out=new JSONArray(); File root=new File(c.getFilesDir(),"hawkeye-memory");
    if(!root.exists())return out;
    ArrayList<File> files=new ArrayList<>();
    collectJson(root,files); files.sort(Comparator.comparingLong(File::lastModified).reversed());
    for(File f:files){
      if(out.length()>=Math.max(1,limit))break;
      String s=new String(java.nio.file.Files.readAllBytes(f.toPath()),"UTF-8");
      JSONObject j=new JSONObject(s);
      if("pending".equals(j.optString("sync_state")))out.put(j);
    }
    return out;
  }

  private static void prune(File dir,int maxJson){
    File[] fs=dir.listFiles((d,n)->n.endsWith(".json")); if(fs==null||fs.length<=maxJson)return;
    java.util.Arrays.sort(fs,Comparator.comparingLong(File::lastModified));
    for(int i=0;i<fs.length-maxJson;i++){
      try{
        JSONObject j=new JSONObject(new String(java.nio.file.Files.readAllBytes(fs[i].toPath()),"UTF-8"));
        new File(dir,j.optString("image_file","")).delete(); fs[i].delete();
      }catch(Exception ignored){}
    }
  }
  private static void collectJson(File f,ArrayList<File> out){
    File[] fs=f.listFiles(); if(fs==null)return;
    for(File x:fs){if(x.isDirectory())collectJson(x,out);else if(x.getName().endsWith(".json"))out.add(x);}
  }
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
