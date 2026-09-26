package com.krishna.mobile;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.KeyStore;
import java.util.Locale;
import java.util.regex.Pattern;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Direct mobile zero-cost cloud route.
 *
 * No paid fallback. OpenRouter models are selected only after a live catalog
 * preflight reports zero prompt/completion pricing. The long-lived key is
 * encrypted by Android Keystore and is never exposed back to JavaScript.
 */
public final class MobileFreeCloudRouter {
  private static final String PREF="krishna_mobile_free_cloud";
  private static final String ALIAS="krishna.mobile.free.cloud.v1";
  private static final String OPENROUTER="https://openrouter.ai/api/v1";
  private static final long MODEL_CACHE_MS=5*60*1000L;
  private static final Pattern SECRET=Pattern.compile(
    "(?i)(password|passwd|pwd|api[ _-]?key|secret|access[ _-]?token|refresh[ _-]?token|authorization|credential|private key|otp|pin)"
  );
  private static final Pattern PRIVATE_CONTEXT=Pattern.compile(
    "(?i)([A-Z]:\\\\|/home/|/mnt/|my private|my file|my repo|krishna[- _]?(source|core|project)|kuber project|manibhadra|narad|brahmagyan|gyan-bhandar)"
  );
  private static final Pattern HOST_ACTION=Pattern.compile(
    "(?i)\\\\b(delete|remove|install|uninstall|execute|run|restart|stop|start|modify|edit|implement|merge|commit|push|deploy|build apk|change file|write file)\\\\b"
  );

  private MobileFreeCloudRouter(){}

  private static SharedPreferences prefs(Context c){return c.getSharedPreferences(PREF,0);}

  private static SecretKey key() throws Exception {
    KeyStore ks=KeyStore.getInstance("AndroidKeyStore");ks.load(null);
    if(ks.containsAlias(ALIAS))return ((KeyStore.SecretKeyEntry)ks.getEntry(ALIAS,null)).getSecretKey();
    KeyGenerator g=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
    g.init(new KeyGenParameterSpec.Builder(
      ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT
    ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
     .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
     .setRandomizedEncryptionRequired(true).build());
    return g.generateKey();
  }

  public static JSONObject provisionOpenRouter(Context c,String token)throws Exception{
    String t=token==null?"":token.trim();
    if(t.length()<16)throw new IllegalArgumentException("OpenRouter token is missing or too short");
    Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
    cipher.init(Cipher.ENCRYPT_MODE,key());
    byte[] encrypted=cipher.doFinal(t.getBytes("UTF-8"));
    prefs(c).edit()
      .putString("token",Base64.encodeToString(encrypted,Base64.NO_WRAP))
      .putString("iv",Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP))
      .remove("model_text").remove("model_vision").remove("model_verified_at").apply();
    return status(c);
  }

  public static JSONObject clear(Context c)throws Exception{
    prefs(c).edit().clear().apply();
    return status(c);
  }

  private static String token(Context c)throws Exception{
    SharedPreferences p=prefs(c);
    String enc=p.getString("token",""),iv=p.getString("iv","");
    if(enc.isEmpty()||iv.isEmpty())return "";
    Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
    cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(iv,Base64.NO_WRAP)));
    return new String(cipher.doFinal(Base64.decode(enc,Base64.NO_WRAP)),"UTF-8");
  }

  public static JSONObject status(Context c)throws Exception{
    SharedPreferences p=prefs(c);
    JSONObject out=new JSONObject();
    out.put("component","KRISHNA Mobile Direct Free Cloud");
    out.put("provider","openrouter");
    out.put("configured",!token(c).isEmpty());
    out.put("credential_storage","AndroidKeyStore AES-GCM");
    out.put("credential_exportable",false);
    out.put("automatic_paid_fallback",false);
    out.put("catalog_preflight","live zero-price required");
    out.put("text_model",p.getString("model_text",""));
    out.put("vision_model",p.getString("model_vision",""));
    out.put("pc_fallback","private/action/heavy/failure only");
    return out;
  }

  public static String routeChat(String text,int attachmentCount){
    String value=text==null?"":text.trim();
    if(attachmentCount>0)return "PC_ATTACHMENTS";
    if(value.length()>6000)return "PC_LARGE_CONTEXT";
    if(SECRET.matcher(value).find())return "PC_SENSITIVE";
    if(PRIVATE_CONTEXT.matcher(value).find())return "PC_PRIVATE_CONTEXT";
    if(HOST_ACTION.matcher(value).find())return "PC_ACTION";
    return "MOBILE_FREE_CLOUD";
  }

  private static HttpURLConnection open(String method,String path,String apiKey)throws Exception{
    HttpURLConnection c=(HttpURLConnection)new URL(OPENROUTER+path).openConnection();
    c.setConnectTimeout(7000);c.setReadTimeout(60000);
    c.setRequestMethod(method);
    c.setRequestProperty("Accept","application/json");
    c.setRequestProperty("Authorization","Bearer "+apiKey);
    c.setRequestProperty("X-Title","KRISHNA Mobile");
    return c;
  }

  private static String read(HttpURLConnection c)throws Exception{
    try{
      int code=c.getResponseCode();
      InputStream in=code<400?c.getInputStream():c.getErrorStream();
      if(in==null)throw new IllegalStateException("OpenRouter HTTP "+code+" returned no body");
      try(InputStream src=in;ByteArrayOutputStream out=new ByteArrayOutputStream()){
        byte[] b=new byte[8192];for(int n;(n=src.read(b))>0;)out.write(b,0,n);
        String body=out.toString("UTF-8");
        if(code>=400)throw new IllegalStateException("OpenRouter HTTP "+code+": "+body.substring(0,Math.min(800,body.length())));
        return body;
      }
    }finally{c.disconnect();}
  }

  private static boolean zero(JSONObject pricing,String name){
    if(pricing==null||!pricing.has(name)||pricing.isNull(name))return true;
    try{
      Object v=pricing.get(name);
      if(v instanceof Number)return Math.abs(((Number)v).doubleValue())<1e-15;
      return Math.abs(Double.parseDouble(String.valueOf(v)))<1e-15;
    }catch(Exception e){return false;}
  }

  private static boolean modality(JSONObject row,String wanted){
    JSONObject arch=row.optJSONObject("architecture");
    JSONArray inputs=arch==null?null:arch.optJSONArray("input_modalities");
    if(inputs==null)return "text".equals(wanted);
    for(int i=0;i<inputs.length();i++)if(wanted.equalsIgnoreCase(inputs.optString(i)))return true;
    return false;
  }

  private static String selectZeroModel(Context ctx,boolean vision)throws Exception{
    SharedPreferences p=prefs(ctx);long now=System.currentTimeMillis();
    String key=vision?"model_vision":"model_text";
    String cached=p.getString(key,"");
    long verified=p.getLong("model_verified_at",0);
    if(!cached.isEmpty()&&now-verified<MODEL_CACHE_MS)return cached;
    String apiKey=token(ctx);if(apiKey.isEmpty())throw new IllegalStateException("mobile OpenRouter key is not provisioned");
    HttpURLConnection c=open("GET","/models",apiKey);
    JSONObject data=new JSONObject(read(c));
    JSONArray rows=data.optJSONArray("data");if(rows==null)throw new IllegalStateException("OpenRouter model catalog missing data");
    String best="";long bestContext=-1;
    for(int i=0;i<rows.length();i++){
      JSONObject row=rows.optJSONObject(i);if(row==null)continue;
      JSONObject pricing=row.optJSONObject("pricing");
      if(!zero(pricing,"prompt")||!zero(pricing,"completion")||!zero(pricing,"request"))continue;
      if(!modality(row,"text"))continue;
      if(vision&&!modality(row,"image"))continue;
      String id=row.optString("id","").trim();if(id.isEmpty())continue;
      long context=row.optLong("context_length",0);
      if(id.endsWith(":free"))context+=1_000_000L;
      if(context>bestContext){best=id;bestContext=context;}
    }
    if(best.isEmpty())throw new IllegalStateException("no live zero-price "+(vision?"vision":"text")+" model is available");
    p.edit().putString(key,best).putLong("model_verified_at",now).apply();
    return best;
  }

  private static JSONObject complete(Context ctx,JSONArray content,String system,boolean vision)throws Exception{
    String apiKey=token(ctx),model=selectZeroModel(ctx,vision);
    if(apiKey.isEmpty())throw new IllegalStateException("mobile OpenRouter key is not provisioned");
    JSONObject body=new JSONObject();
    body.put("model",model);body.put("temperature",0.2);body.put("max_tokens",vision?1400:1200);
    JSONArray messages=new JSONArray();
    messages.put(new JSONObject().put("role","system").put("content",system));
    Object userContent=content.length()==1&&content.optJSONObject(0)!=null&&"text".equals(content.optJSONObject(0).optString("type"))
      ?content.optJSONObject(0).optString("text"):content;
    messages.put(new JSONObject().put("role","user").put("content",userContent));
    body.put("messages",messages);
    HttpURLConnection c=open("POST","/chat/completions",apiKey);
    c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");
    try(OutputStream out=c.getOutputStream()){out.write(body.toString().getBytes("UTF-8"));}
    JSONObject response=new JSONObject(read(c));
    JSONArray choices=response.optJSONArray("choices");
    String answer="";
    if(choices!=null&&choices.length()>0){
      JSONObject msg=choices.optJSONObject(0).optJSONObject("message");
      if(msg!=null)answer=msg.optString("content","");
    }
    if(answer.trim().isEmpty())throw new IllegalStateException("zero-price cloud returned an empty answer");
    return new JSONObject()
      .put("reply",answer.trim()).put("text",answer.trim())
      .put("provider","openrouter").put("model",model)
      .put("zero_cost_verified",true).put("automatic_paid_fallback",false)
      .put("execution","mobile-direct-free-cloud").put("avatar_state","TALKING");
  }

  public static JSONObject chat(Context ctx,String prompt)throws Exception{
    if(!"MOBILE_FREE_CLOUD".equals(routeChat(prompt,0)))throw new SecurityException("message is not eligible for direct mobile cloud");
    JSONArray content=new JSONArray().put(new JSONObject().put("type","text").put("text",prompt));
    return complete(ctx,content,
      "You are KRISHNA Mobile. Answer the user's ordinary non-sensitive question concisely. "+
      "You have no authority to claim files, apps, projects, purchases, or external systems were changed. "+
      "For device/project actions say they require KRISHNA PC.",false);
  }

  public static JSONObject analyzeImage(Context ctx,byte[] image,String contentType,String prompt)throws Exception{
    if(image==null||image.length==0||image.length>4*1024*1024)throw new IllegalArgumentException("bounded keyframe required");
    String type=contentType==null?"image/jpeg":contentType.split(";",2)[0].toLowerCase(Locale.US);
    if(!("image/jpeg".equals(type)||"image/png".equals(type)||"image/webp".equals(type)))throw new IllegalArgumentException("unsupported keyframe type");
    JSONArray content=new JSONArray();
    content.put(new JSONObject().put("type","text").put("text",prompt==null?"Analyze this selected non-sensitive keyframe.":prompt));
    content.put(new JSONObject().put("type","image_url").put("image_url",new JSONObject().put(
      "url","data:"+type+";base64,"+Base64.encodeToString(image,Base64.NO_WRAP)
    )));
    JSONObject out=complete(ctx,content,
      "You are HAWKEYE on KRISHNA Mobile. Distinguish observed facts from inference, state uncertainty, "+
      "do not identify unknown people, and suggest the best next camera view.",true);
    out.put("analysis",out.optString("reply",""));
    out.put("role","hawkeye_vision");out.put("selected_keyframe",true);
    return out;
  }
}
