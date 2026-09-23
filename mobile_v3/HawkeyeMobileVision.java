package com.krishna.mobile;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Rect;

import com.google.android.gms.tasks.Tasks;
import com.google.android.gms.tasks.Task;
import com.google.mlkit.vision.barcode.BarcodeScanning;
import com.google.mlkit.vision.barcode.BarcodeScanner;
import com.google.mlkit.vision.barcode.common.Barcode;
import com.google.mlkit.vision.face.Face;
import com.google.mlkit.vision.face.FaceDetection;
import com.google.mlkit.vision.face.FaceDetector;
import com.google.mlkit.vision.face.FaceDetectorOptions;
import com.google.mlkit.vision.pose.Pose;
import com.google.mlkit.vision.pose.PoseDetection;
import com.google.mlkit.vision.pose.PoseDetector;
import com.google.mlkit.vision.pose.PoseLandmark;
import com.google.mlkit.vision.pose.defaults.PoseDetectorOptions;
import com.google.mlkit.vision.segmentation.subject.Subject;
import com.google.mlkit.vision.segmentation.subject.SubjectSegmentation;
import com.google.mlkit.vision.segmentation.subject.SubjectSegmentationResult;
import com.google.mlkit.vision.segmentation.subject.SubjectSegmenter;
import com.google.mlkit.vision.segmentation.subject.SubjectSegmenterOptions;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.devanagari.DevanagariTextRecognizerOptions;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;
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

  private static final TextRecognizer LATIN_OCR =
    TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
  private static final TextRecognizer DEVANAGARI_OCR =
    TextRecognition.getClient(new DevanagariTextRecognizerOptions.Builder().build());
  private static final BarcodeScanner BARCODES = BarcodeScanning.getClient();
  private static final FaceDetector FACES = FaceDetection.getClient(
    new FaceDetectorOptions.Builder()
      .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST)
      .enableTracking()
      .build()
  );
  private static final PoseDetector POSE = PoseDetection.getClient(
    new PoseDetectorOptions.Builder()
      .setDetectorMode(PoseDetectorOptions.STREAM_MODE)
      .build()
  );
  private static final SubjectSegmenter SUBJECTS = SubjectSegmentation.getClient(
    new SubjectSegmenterOptions.Builder()
      .enableMultipleSubjects(new SubjectSegmenterOptions.SubjectResultOptions.Builder().build())
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

  public static JSONObject analyzeRich(byte[] jpeg)throws Exception{
    JSONObject out=new JSONObject();
    out.put("schema","hawkeye.mobile-rich-perception.v1");
    out.put("engine","ML_KIT_LOCAL_RICH");
    out.put("local",true);
    out.put("cloud_required",false);
    out.put("evidence_state","OBSERVED");

    Bitmap bitmap=BitmapFactory.decodeByteArray(jpeg,0,jpeg.length);
    if(bitmap==null){
      out.put("error","image decode failed");
      return out;
    }
    final double w=Math.max(1,bitmap.getWidth()),h=Math.max(1,bitmap.getHeight());
    InputImage image=InputImage.fromBitmap(bitmap,0);

    Task<Text> latinTask=LATIN_OCR.process(image);
    Task<Text> devanagariTask=DEVANAGARI_OCR.process(image);
    Task<List<Barcode>> barcodeTask=BARCODES.process(image);
    Task<List<Face>> faceTask=FACES.process(image);
    Task<Pose> poseTask=POSE.process(image);
    Task<SubjectSegmentationResult> subjectTask=SUBJECTS.process(image);

    try{
      Tasks.await(Tasks.whenAllComplete(latinTask,devanagariTask,barcodeTask,faceTask,poseTask,subjectTask),3500,TimeUnit.MILLISECONDS);
    }catch(Exception ignored){}

    JSONObject ocr=new JSONObject();
    JSONArray blocks=new JSONArray();
    StringBuilder merged=new StringBuilder();
    appendTextResult(latinTask,blocks,merged,w,h,"latin");
    appendTextResult(devanagariTask,blocks,merged,w,h,"devanagari");
    String safeText=redactSensitive(merged.toString().trim());
    if(safeText.length()>3000)safeText=safeText.substring(0,3000);
    ocr.put("text",safeText);
    ocr.put("blocks",blocks);
    ocr.put("credential_redaction",true);
    out.put("ocr",ocr);

    JSONArray codes=new JSONArray();
    if(barcodeTask.isSuccessful()&&barcodeTask.getResult()!=null){
      for(Barcode code:barcodeTask.getResult()){
        JSONObject row=new JSONObject();
        row.put("format",code.getFormat());
        row.put("value_type",code.getValueType());
        row.put("value",safeBarcodeValue(code));
        Rect box=code.getBoundingBox();
        if(box!=null)row.put("bbox",norm(box,w,h));
        codes.put(row);
      }
    }
    out.put("barcodes",codes);

    JSONArray faces=new JSONArray();
    if(faceTask.isSuccessful()&&faceTask.getResult()!=null){
      for(Face face:faceTask.getResult()){
        JSONObject row=new JSONObject();
        row.put("bbox",norm(face.getBoundingBox(),w,h));
        row.put("tracking_id",face.getTrackingId()==null?JSONObject.NULL:face.getTrackingId());
        row.put("identity","UNKNOWN");
        row.put("biometric_web_search",false);
        faces.put(row);
      }
    }
    out.put("faces",faces);

    JSONArray pose=new JSONArray();
    if(poseTask.isSuccessful()&&poseTask.getResult()!=null){
      for(PoseLandmark p:poseTask.getResult().getAllPoseLandmarks()){
        if(p.getInFrameLikelihood()<0.35f)continue;
        JSONObject row=new JSONObject();
        row.put("type",p.getLandmarkType());
        row.put("x",Math.max(0,Math.min(1,p.getPosition().x/w)));
        row.put("y",Math.max(0,Math.min(1,p.getPosition().y/h)));
        row.put("likelihood",p.getInFrameLikelihood());
        pose.put(row);
      }
    }
    out.put("pose_landmarks",pose);

    JSONArray subjects=new JSONArray();
    if(subjectTask.isSuccessful()&&subjectTask.getResult()!=null){
      for(Subject subject:subjectTask.getResult().getSubjects()){
        JSONObject row=new JSONObject();
        row.put("bbox",new JSONArray()
          .put(Math.max(0,Math.min(1,subject.getStartX()/w)))
          .put(Math.max(0,Math.min(1,subject.getStartY()/h)))
          .put(Math.max(0,Math.min(1,subject.getWidth()/w)))
          .put(Math.max(0,Math.min(1,subject.getHeight()/h))));
        subjects.put(row);
      }
    }
    out.put("subjects",subjects);
    out.put("subject_model_ready",subjectTask.isSuccessful());

    JSONObject caps=new JSONObject();
    caps.put("ocr_latin",latinTask.isSuccessful());
    caps.put("ocr_devanagari",devanagariTask.isSuccessful());
    caps.put("barcode",barcodeTask.isSuccessful());
    caps.put("face_presence_tracking",faceTask.isSuccessful());
    caps.put("pose",poseTask.isSuccessful());
    caps.put("subject_segmentation",subjectTask.isSuccessful());
    caps.put("face_identity",false);
    caps.put("api_key_required",false);
    out.put("capabilities",caps);

    String guidance="Hold steady and center the important object.";
    if(blocks.length()>0&&safeText.length()<8)guidance="Move closer and hold steady so HAWKEYE can read the text.";
    if(subjects.length()>0){
      JSONObject b=subjects.getJSONObject(0);
      JSONArray q=b.getJSONArray("bbox");
      double x=q.getDouble(0),y=q.getDouble(1),bw=q.getDouble(2),bh=q.getDouble(3);
      if(x<0.02||y<0.02||x+bw>0.98||y+bh>0.98)guidance="Move slightly back or recenter; the main subject is clipped by the frame.";
    }
    out.put("recommended_next_scan",guidance);
    return out;
  }

  private static void appendTextResult(Task<Text> task,JSONArray blocks,StringBuilder merged,double w,double h,String script)throws Exception{
    if(!task.isSuccessful()||task.getResult()==null)return;
    Text text=task.getResult();
    String value=redactSensitive(text.getText());
    if(value!=null&&!value.trim().isEmpty()){
      if(merged.length()>0)merged.append("\n");
      merged.append(value.trim());
    }
    for(Text.TextBlock block:text.getTextBlocks()){
      Rect box=block.getBoundingBox();
      JSONObject row=new JSONObject();
      row.put("script",script);
      row.put("text",redactSensitive(block.getText()));
      if(box!=null)row.put("bbox",norm(box,w,h));
      blocks.put(row);
      if(blocks.length()>=40)break;
    }
  }

  private static JSONArray norm(Rect r,double w,double h)throws Exception{
    return new JSONArray()
      .put(Math.max(0,Math.min(1,r.left/w)))
      .put(Math.max(0,Math.min(1,r.top/h)))
      .put(Math.max(0,Math.min(1,r.width()/w)))
      .put(Math.max(0,Math.min(1,r.height()/h)));
  }

  private static String safeBarcodeValue(Barcode code){
    if(code==null)return "";
    if(code.getValueType()==Barcode.TYPE_WIFI)return "[WIFI CREDENTIAL REDACTED]";
    String value=code.getDisplayValue();
    if(value==null)value=code.getRawValue();
    value=redactSensitive(value==null?"":value);
    if(value.length()>512)value=value.substring(0,512);
    return value;
  }

  private static String redactSensitive(String value){
    String s=value==null?"":value;
    s=s.replaceAll("(?i)(password|passwd|pwd|pin|otp|api[_ -]?key|access[_ -]?token|session[_ -]?token)\\s*[:=]\\s*[^\\s,;]+","$1: [SECRET REDACTED]");
    s=s.replaceAll("(?i)authorization\\s*:\\s*bearer\\s+[A-Za-z0-9._~+\\-/=]{4,}","authorization: [SECRET REDACTED]");
    s=s.replaceAll("\\bAIza[0-9A-Za-z_-]{20,}\\b","[SECRET REDACTED]");
    return s;
  }

}
