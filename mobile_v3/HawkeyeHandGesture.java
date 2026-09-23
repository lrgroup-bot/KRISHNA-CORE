package com.krishna.mobile;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

import com.google.mediapipe.framework.image.BitmapImageBuilder;
import com.google.mediapipe.framework.image.MPImage;
import com.google.mediapipe.tasks.components.containers.Category;
import com.google.mediapipe.tasks.components.containers.NormalizedLandmark;
import com.google.mediapipe.tasks.core.BaseOptions;
import com.google.mediapipe.tasks.vision.core.RunningMode;
import com.google.mediapipe.tasks.vision.gesturerecognizer.GestureRecognizer;
import com.google.mediapipe.tasks.vision.gesturerecognizer.GestureRecognizerResult;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.List;

/** Local MediaPipe hand/finger landmarks + canned gesture recognition. */
public final class HawkeyeHandGesture {
  private static final String MODEL="gesture_recognizer.task";
  private static GestureRecognizer recognizer;

  private HawkeyeHandGesture(){}

  private static synchronized GestureRecognizer recognizer(Context c){
    if(recognizer!=null)return recognizer;
    BaseOptions base=BaseOptions.builder().setModelAssetPath(MODEL).build();
    GestureRecognizer.GestureRecognizerOptions options=
      GestureRecognizer.GestureRecognizerOptions.builder()
        .setBaseOptions(base)
        .setRunningMode(RunningMode.IMAGE)
        .setNumHands(2)
        .setMinHandDetectionConfidence(0.5f)
        .setMinHandPresenceConfidence(0.5f)
        .setMinTrackingConfidence(0.5f)
        .build();
    recognizer=GestureRecognizer.createFromOptions(c.getApplicationContext(),options);
    return recognizer;
  }

  public static JSONObject analyze(Context c,byte[] jpeg)throws Exception{
    JSONObject out=new JSONObject();
    out.put("schema","hawkeye.mobile-hand-gesture.v1");
    out.put("engine","MEDIAPIPE_GESTURE_RECOGNIZER");
    out.put("local",true);
    out.put("api_key_required",false);
    out.put("model_asset",MODEL);
    out.put("evidence_state","OBSERVED");

    Bitmap decoded=BitmapFactory.decodeByteArray(jpeg,0,jpeg.length);
    if(decoded==null){out.put("error","image decode failed");return out;}
    Bitmap bitmap=decoded.getConfig()==Bitmap.Config.ARGB_8888
      ? decoded : decoded.copy(Bitmap.Config.ARGB_8888,false);
    MPImage image=new BitmapImageBuilder(bitmap).build();
    try{
      GestureRecognizerResult result=recognizer(c).recognize(image);
      JSONArray hands=new JSONArray();
      String primary="None";double primaryScore=0.0;
      List<List<Category>> gestures=result.gestures();
      List<List<Category>> handed=result.handedness();
      List<List<NormalizedLandmark>> landmarks=result.landmarks();
      int count=Math.max(landmarks.size(),Math.max(gestures.size(),handed.size()));
      for(int i=0;i<count;i++){
        JSONObject hand=new JSONObject();
        String side="UNKNOWN";
        if(i<handed.size()&&!handed.get(i).isEmpty())side=handed.get(i).get(0).categoryName();
        hand.put("handedness",side);
        String gesture="None";double score=0.0;
        if(i<gestures.size()&&!gestures.get(i).isEmpty()){
          Category cat=gestures.get(i).get(0);
          gesture=cat.categoryName();score=cat.score();
          if(score>primaryScore){primaryScore=score;primary=gesture;}
        }
        hand.put("gesture",gesture);hand.put("confidence",score);
        JSONArray points=new JSONArray();
        if(i<landmarks.size()){
          int index=0;
          for(NormalizedLandmark p:landmarks.get(i)){
            JSONObject point=new JSONObject();
            point.put("index",index++);
            point.put("x",p.x());point.put("y",p.y());point.put("z",p.z());
            points.put(point);
          }
        }
        hand.put("landmarks",points);
        hands.put(hand);
      }
      out.put("hands",hands);
      out.put("hand_count",hands.length());
      out.put("primary_gesture",primary);
      out.put("primary_confidence",primaryScore);
      out.put("finger_landmarks",true);
      out.put("supported_canned_gestures",new JSONArray()
        .put("Closed_Fist").put("Open_Palm").put("Pointing_Up")
        .put("Thumb_Down").put("Thumb_Up").put("Victory").put("ILoveYou"));
      return out;
    }finally{
      image.close();
      if(bitmap!=decoded)bitmap.recycle();
      decoded.recycle();
    }
  }
}
