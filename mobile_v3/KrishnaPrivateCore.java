package com.krishna.mobile;

import android.content.Context;
import android.content.SharedPreferences;
import android.net.*;
import android.os.BatteryManager;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.util.Locale;

/** Private Core discovery/resolution shared by conversation and Hawkeye sync. */
public final class KrishnaPrivateCore {
  private KrishnaPrivateCore(){}

  public static boolean privateCoreUrl(String value){
    try{
      URI u=new URI(value);String scheme=u.getScheme(),host=u.getHost();
      if(host==null||(!"http".equalsIgnoreCase(scheme)&&!"https".equalsIgnoreCase(scheme)))return false;
      String h=host.toLowerCase(Locale.US);
      if("localhost".equals(h)||h.endsWith(".ts.net"))return true;
      InetAddress ip=InetAddress.getByName(host);
      if(ip.isLoopbackAddress()||ip.isSiteLocalAddress()||ip.isLinkLocalAddress())return true;
      byte[] b=ip.getAddress();
      if(b.length==4){
        int a=b[0]&255,d=b[1]&255;
        if(a==100&&d>=64&&d<=127)return true; // Tailscale/CGNAT
      }else if(b.length==16){
        int a=b[0]&255;if((a&0xfe)==0xfc)return true; // IPv6 ULA
      }
    }catch(Exception ignored){}
    return false;
  }

  static String clean(String value){return value==null?"":value.trim().replaceAll("/+$","");}

  public static boolean health(String base){
    base=clean(base);if(!privateCoreUrl(base))return false;
    HttpURLConnection h=null;
    try{
      h=(HttpURLConnection)new URL(base+"/health").openConnection();
      h.setConnectTimeout(1500);h.setReadTimeout(2000);
      h.setRequestProperty("Accept","application/json");
      if(h.getResponseCode()!=200)return false;
      try(InputStream in=h.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){
        byte[] b=new byte[2048];for(int n;(n=in.read(b))>0;)out.write(b,0,n);
        return new JSONObject(out.toString("UTF-8")).optBoolean("ok",false);
      }
    }catch(Exception ignored){return false;}
    finally{if(h!=null)h.disconnect();}
  }

  public static String discoverLan(Context c){
    DatagramSocket s=null;
    try{
      s=new DatagramSocket();s.setBroadcast(true);s.setSoTimeout(1400);
      byte[] q="KRISHNA_DISCOVER_V1".getBytes("UTF-8");
      s.send(new DatagramPacket(q,q.length,InetAddress.getByName("255.255.255.255"),8767));
      byte[] buf=new byte[1024];DatagramPacket p=new DatagramPacket(buf,buf.length);s.receive(p);
      JSONObject d=new JSONObject(new String(p.getData(),0,p.getLength(),"UTF-8"));
      if(!"KRISHNA_CORE".equals(d.optString("service")))return "";
      String candidate="http://"+p.getAddress().getHostAddress()+":"+d.optInt("port",8766);
      if(!privateCoreUrl(candidate)||!health(candidate))return "";
      c.getSharedPreferences("k",0).edit().putString("lan_core_url",candidate).putString("core_url",candidate).apply();
      return candidate;
    }catch(Exception ignored){return "";}
    finally{if(s!=null)s.close();}
  }

  public static String resolve(Context c)throws Exception{
    SharedPreferences p=c.getSharedPreferences("k",0);
    String remote=clean(p.getString("private_remote_url",""));
    if(privateCoreUrl(remote)&&health(remote))return remote;
    String base=clean(p.getString("core_url",""));
    if(privateCoreUrl(base)&&health(base))return base;
    String lan=clean(p.getString("lan_core_url",""));
    if(privateCoreUrl(lan)&&health(lan))return lan;
    lan=discoverLan(c);
    if(!lan.isEmpty())return lan;
    throw new IllegalStateException("KRISHNA Core is unreachable on trusted LAN/private overlay");
  }

  public static JSONObject bootstrap(Context c,String deviceId,String credential)throws Exception{
    String base=resolve(c);HttpURLConnection h=null;
    try{
      h=(HttpURLConnection)new URL(base+"/api/mobile/bootstrap").openConnection();
      h.setConnectTimeout(3000);h.setReadTimeout(8000);h.setRequestProperty("Accept","application/json");
      h.setRequestProperty("X-Krishna-Device",deviceId);h.setRequestProperty("Authorization","Device "+credential);
      int code=h.getResponseCode();InputStream src=code<400?h.getInputStream():h.getErrorStream();
      ByteArrayOutputStream out=new ByteArrayOutputStream();
      if(src!=null)try(InputStream in=src){byte[] b=new byte[4096];for(int n;(n=in.read(b))>0;)out.write(b,0,n);}
      JSONObject result=out.size()==0?new JSONObject():new JSONObject(out.toString("UTF-8"));
      result.put("http_status",code);
      if(code==200){
        String remote=clean(result.optString("private_remote_url",""));
        if(!remote.isEmpty()&&privateCoreUrl(remote)){
          c.getSharedPreferences("k",0).edit().putString("private_remote_url",remote).putString("core_url",remote).apply();
        }
      }
      return result;
    }finally{if(h!=null)h.disconnect();}
  }

  public static boolean unmeteredTrustedNetwork(Context c){
    try{
      ConnectivityManager cm=(ConnectivityManager)c.getSystemService(Context.CONNECTIVITY_SERVICE);
      Network n=cm.getActiveNetwork();if(n==null)return false;
      NetworkCapabilities caps=cm.getNetworkCapabilities(n);if(caps==null)return false;
      if(!caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET))return false;
      if(cm.isActiveNetworkMetered())return false;
      boolean privateTransport=caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
        ||caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
        ||caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN);
      if(!privateTransport)return false;
      if(caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)
          && !caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN))return false;
      return true;
    }catch(Exception e){return false;}
  }

  public static boolean trustedLanReady(Context c){
    if(!unmeteredTrustedNetwork(c))return false;
    // Same-LAN proof requires KRISHNA's UDP responder to be reachable on the
    // current broadcast domain. This prevents bulk media sync from starting
    // merely because the phone is on unrelated unmetered Wi-Fi.
    return !discoverLan(c).isEmpty();
  }

  public static boolean batteryReady(Context c){
    try{
      BatteryManager bm=(BatteryManager)c.getSystemService(Context.BATTERY_SERVICE);
      int pct=bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
      return pct<=0||pct>=25;
    }catch(Exception e){return true;}
  }
}
