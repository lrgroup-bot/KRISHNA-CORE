package com.krishna.mobile;

import android.content.Context;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.os.Build;
import android.util.Range;
import android.util.SizeF;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Set;

/** Read-only native camera capability inventory for HAWKEYE Active Vision. */
public final class HawkeyeCameraProfiler {
  private HawkeyeCameraProfiler(){}

  private static JSONArray ints(int[] values)throws Exception{
    JSONArray out=new JSONArray();
    if(values!=null)for(int v:values)out.put(v);
    return out;
  }

  private static JSONArray floats(float[] values)throws Exception{
    JSONArray out=new JSONArray();
    if(values!=null)for(float v:values)out.put((double)v);
    return out;
  }

  public static JSONObject profile(Context context)throws Exception{
    JSONObject out=new JSONObject();
    out.put("schema","hawkeye.camera-profile.v1");
    out.put("read_only",true);
    out.put("opens_camera",false);
    out.put("api_level",Build.VERSION.SDK_INT);
    JSONArray cameras=new JSONArray();
    int rear=0;
    CameraManager manager=(CameraManager)context.getSystemService(Context.CAMERA_SERVICE);
    if(manager==null){
      out.put("available",false);
      out.put("cameras",cameras);
      return out;
    }
    for(String id:manager.getCameraIdList()){
      CameraCharacteristics c=manager.getCameraCharacteristics(id);
      Integer facing=c.get(CameraCharacteristics.LENS_FACING);
      if(facing==null||facing!=CameraCharacteristics.LENS_FACING_BACK)continue;
      rear++;
      JSONObject row=new JSONObject();
      row.put("camera_id",id);
      row.put("facing","BACK");
      row.put("focal_lengths_mm",floats(c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)));
      Float minFocus=c.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE);
      row.put("minimum_focus_distance_diopters",minFocus==null?JSONObject.NULL:minFocus);
      Float maxDigital=c.get(CameraCharacteristics.SCALER_AVAILABLE_MAX_DIGITAL_ZOOM);
      row.put("max_digital_zoom",maxDigital==null?JSONObject.NULL:maxDigital);
      Boolean flash=c.get(CameraCharacteristics.FLASH_INFO_AVAILABLE);
      row.put("flash_available",Boolean.TRUE.equals(flash));
      row.put("af_modes",ints(c.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES)));
      row.put("ae_modes",ints(c.get(CameraCharacteristics.CONTROL_AE_AVAILABLE_MODES)));
      row.put("ois_modes",ints(c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION)));
      Integer orientation=c.get(CameraCharacteristics.SENSOR_ORIENTATION);
      row.put("sensor_orientation",orientation==null?JSONObject.NULL:orientation);
      SizeF sensor=c.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE);
      if(sensor!=null){
        row.put("sensor_width_mm",sensor.getWidth());
        row.put("sensor_height_mm",sensor.getHeight());
      }
      if(Build.VERSION.SDK_INT>=30){
        Range<Float> zoom=c.get(CameraCharacteristics.CONTROL_ZOOM_RATIO_RANGE);
        if(zoom!=null){
          JSONObject zr=new JSONObject();
          zr.put("min",zoom.getLower());zr.put("max",zoom.getUpper());
          row.put("zoom_ratio_range",zr);
        }
      }
      if(Build.VERSION.SDK_INT>=28){
        Set<String> physical=c.getPhysicalCameraIds();
        JSONArray ids=new JSONArray();
        for(String p:physical)ids.put(p);
        row.put("physical_camera_ids",ids);
        row.put("logical_multi_camera",!physical.isEmpty());
      }else{
        row.put("physical_camera_ids",new JSONArray());
        row.put("logical_multi_camera",false);
      }
      cameras.put(row);
    }
    out.put("available",rear>0);
    out.put("rear_camera_count",rear);
    out.put("cameras",cameras);
    out.put("active_control_authority","browser-media-track-capability-gated");
    out.put("note","Native profile is read-only; Android/WebView retains live camera ownership.");
    return out;
  }
}
