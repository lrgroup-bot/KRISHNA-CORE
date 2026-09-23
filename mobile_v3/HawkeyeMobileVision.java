package com.krishna.mobile;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Rect;

import com.google.android.gms.tasks.Tasks;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.objects.DetectedObject;
import com.google.mlkit.vision.objects.ObjectDetection;
import com.google.mlkit.vision.objects.ObjectDetector;
import com.google.mlkit.vision.objects.defaults.ObjectDetectorOptions;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * Local-only coarse object detection/tracking frontend for HAWKEYE.
 *
 * It supplies geometry/tracking evidence for overlays and auto-zoom. Semantic
 * identity/detail remains a separate HAWKEYE reasoning task; broad ML Kit labels
 * are never promoted as exact object identity.
 */
public final class HawkeyeMobileVision {
  private static final ObjectDetector DETECTOR = ObjectDetection.getClient(
    new ObjectDetectorOptions.Builder()
      .setDetectorMode(ObjectDetectorOptions.STREAM_MODE)
      .enableMultipleObjects()
      .enableClassification()
      .build()
  );

  private HawkeyeMobileVision(){}

  public static JSONObject detect(byte[] jpeg)throws Exception{
    JSONObject out=new JSONObject();
    out.put("schema","hawkeye.mobile-object-layer.v1");
    out.put("engine","ML_KIT_OBJECT_TRACKER");
    out.put("local",true);
    out.put("identity_authority",false);
    out.put("evidence_state","OBSERVED");

    Bitmap bitmap=BitmapFactory.decodeByteArray(jpeg,0,jpeg.length);
    if(bitmap==null){
      out.put("objects",new JSONArray());
      out.put("error","image decode failed");
      return out;
    }

    InputImage image=InputImage.fromBitmap(bitmap,0);
    List<DetectedObject> rows=Tasks.await(DETECTOR.process(image),1500,TimeUnit.MILLISECONDS);
    JSONArray objects=new JSONArray();
    double bestArea=-1.0;
    JSONObject primary=null;

    final double w=Math.max(1,bitmap.getWidth()),h=Math.max(1,bitmap.getHeight());
    for(DetectedObject item:rows){
      Rect r=item.getBoundingBox();
      double x=Math.max(0,Math.min(1,r.left/w));
      double y=Math.max(0,Math.min(1,r.top/h));
      double bw=Math.max(0,Math.min(1,(double)r.width()/w));
      double bh=Math.max(0,Math.min(1,(double)r.height()/h));
      JSONObject row=new JSONObject();
      row.put("bbox",new JSONArray().put(x).put(y).put(bw).put(bh));
      row.put("tracking_id",item.getTrackingId()==null?JSONObject.NULL:item.getTrackingId());
      JSONArray labels=new JSONArray();
      for(DetectedObject.Label label:item.getLabels()){
        JSONObject lr=new JSONObject();
        lr.put("text",label.getText());
        lr.put("confidence",label.getConfidence());
        labels.put(lr);
      }
      row.put("labels",labels);
      row.put("label",labels.length()>0?labels.getJSONObject(0).optString("text","object"):"object");
      row.put("classification_scope","coarse-local");
      objects.put(row);
      double area=bw*bh;
      if(area>bestArea){bestArea=area;primary=row;}
    }

    out.put("objects",objects);
    if(primary!=null)out.put("primary",primary);
    out.put("count",objects.length());
    return out;
  }
}
