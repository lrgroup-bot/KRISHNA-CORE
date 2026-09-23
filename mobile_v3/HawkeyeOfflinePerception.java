package com.krishna.mobile;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import org.json.JSONObject;

/**
 * Tiny offline phone-only visual probe.
 * It intentionally does not pretend to be semantic object recognition: it
 * measures image quality/light/edge/change locally and exposes whether an
 * optional semantic model is actually installed.
 */
public final class HawkeyeOfflinePerception {
  private HawkeyeOfflinePerception(){}

  public static JSONObject analyze(Context c,String session,byte[] image)throws Exception{
    JSONObject out=new JSONObject();
    out.put("schema","hawkeye.mobile-offline-perception.v1");
    out.put("engine","ANDROID_LOCAL_LIGHTWEIGHT_PROBE");
    out.put("internet_required",false);
    out.put("pc_required",false);
    out.put("evidence_state","OBSERVED");
    out.put("semantic_model_configured",false);
    out.put("semantic_policy","No object/fault identity is fabricated when a local semantic model is absent.");

    Bitmap b=BitmapFactory.decodeByteArray(image,0,image.length);
    if(b==null){
      out.put("decodable_image",false);
      out.put("analysis","Image retained locally, but the lightweight offline probe could not decode it.");
      return out;
    }
    out.put("decodable_image",true);
    int w=b.getWidth(),h=b.getHeight();
    int sx=Math.max(1,w/64),sy=Math.max(1,h/64);
    long n=0;double sum=0,sum2=0,edges=0;long edgeN=0;
    for(int y=0;y<h;y+=sy){
      double prev=-1;
      for(int x=0;x<w;x+=sx){
        int p=b.getPixel(x,y);
        double lum=0.2126*Color.red(p)+0.7152*Color.green(p)+0.0722*Color.blue(p);
        sum+=lum;sum2+=lum*lum;n++;
        if(prev>=0){edges+=Math.abs(lum-prev);edgeN++;}
        prev=lum;
      }
    }
    double mean=n==0?0:sum/n;
    double variance=n==0?0:Math.max(0,(sum2/n)-mean*mean);
    double contrast=Math.sqrt(variance);
    double edge=edgeN==0?0:edges/edgeN;
    String sig=signature(b);

    SharedPreferences p=c.getSharedPreferences("hawkeye_offline_probe",0);
    String key=safe(session);
    String old=p.getString("sig_"+key,"");
    double change=old.isEmpty()?0.0:(double)hamming(old,sig)/Math.max(1,sig.length());
    p.edit().putString("sig_"+key,sig).apply();

    out.put("width",w);out.put("height",h);
    out.put("brightness_mean",round(mean));
    out.put("contrast_std",round(contrast));
    out.put("edge_energy",round(edge));
    out.put("temporal_change_ratio",round(change));
    out.put("low_light",mean<45.0);
    out.put("low_contrast",contrast<18.0);
    out.put("visible_change_detected",!old.isEmpty()&&change>=0.18);
    String quality=(mean<25||contrast<10)?"LOW":"USABLE";
    out.put("capture_quality",quality);
    out.put("analysis",
      "Offline local probe: capture="+quality+
      ", brightness="+round(mean)+", contrast="+round(contrast)+
      ", visible_change="+(!old.isEmpty()&&change>=0.18)+
      ". Semantic scene/fault identification waits for a verified local model or later PC analysis.");
    return out;
  }

  private static String signature(Bitmap b){
    StringBuilder s=new StringBuilder(64);
    int w=b.getWidth(),h=b.getHeight();
    double total=0;double[] v=new double[64];int k=0;
    for(int gy=0;gy<8;gy++)for(int gx=0;gx<8;gx++){
      int x=Math.min(w-1,Math.max(0,(int)((gx+0.5)*w/8.0)));
      int y=Math.min(h-1,Math.max(0,(int)((gy+0.5)*h/8.0)));
      int p=b.getPixel(x,y);
      double lum=0.2126*Color.red(p)+0.7152*Color.green(p)+0.0722*Color.blue(p);
      v[k++]=lum;total+=lum;
    }
    double mean=total/64.0;
    for(double x:v)s.append(x>=mean?'1':'0');
    return s.toString();
  }

  private static int hamming(String a,String b){
    int n=Math.min(a.length(),b.length()),d=Math.abs(a.length()-b.length());
    for(int i=0;i<n;i++)if(a.charAt(i)!=b.charAt(i))d++;
    return d;
  }
  private static double round(double v){return Math.round(v*1000.0)/1000.0;}
  private static String safe(String s){return (s==null||s.isEmpty()?"field":s).replaceAll("[^A-Za-z0-9_-]","_");}
}
