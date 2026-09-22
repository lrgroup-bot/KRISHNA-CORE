package com.krishna.mobile;

import android.app.ActivityManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.hardware.Sensor;
import android.hardware.SensorManager;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.os.BatteryManager;
import android.os.Build;
import android.os.PowerManager;
import android.os.StatFs;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.util.List;

/**
 * Capability-first device discovery for Hawkeye.
 * Never assumes features from a handset model name.
 */
public final class HawkeyeDeviceProfiler {
  private HawkeyeDeviceProfiler(){}

  public static JSONObject profile(Context context) throws Exception {
    JSONObject root=new JSONObject();
    root.put("schema","hawkeye.device-capability.v1");
    root.put("manufacturer",Build.MANUFACTURER);
    root.put("model",Build.MODEL);
    root.put("device",Build.DEVICE);
    root.put("android_api",Build.VERSION.SDK_INT);
    root.put("hardware",Build.HARDWARE);
    root.put("cameras",cameras(context));
    root.put("sensors",sensors(context));
    root.put("compute",compute(context));
    root.put("runtime",runtime(context));
    root.put("features",features(context));
    root.put("profile",selectProfile(root));
    return root;
  }

  private static JSONArray cameras(Context c)throws Exception{
    JSONArray out=new JSONArray();
    CameraManager cm=(CameraManager)c.getSystemService(Context.CAMERA_SERVICE);
    for(String id:cm.getCameraIdList()){
      CameraCharacteristics x=cm.getCameraCharacteristics(id);
      JSONObject j=new JSONObject();
      j.put("id",id);
      Integer facing=x.get(CameraCharacteristics.LENS_FACING);
      j.put("facing",facing==null?JSONObject.NULL:facing);
      Integer level=x.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL);
      j.put("hardware_level",level==null?JSONObject.NULL:level);
      int[] caps=x.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES);
      JSONArray ca=new JSONArray();
      boolean raw=false,depth=false,logical=false,highRes=false,offline=false;
      if(caps!=null)for(int v:caps){
        ca.put(v);
        raw|=v==CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_RAW;
        depth|=v==CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT;
        logical|=v==CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA;
        if(Build.VERSION.SDK_INT>=31)offline|=v==CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_OFFLINE_PROCESSING;
        if(Build.VERSION.SDK_INT>=31)highRes|=v==CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_ULTRA_HIGH_RESOLUTION_SENSOR;
      }
      j.put("capability_ids",ca);
      j.put("raw",raw); j.put("depth_output",depth); j.put("logical_multi_camera",logical);
      j.put("ultra_high_resolution",highRes); j.put("offline_processing",offline);
      j.put("physical_camera_count",x.getPhysicalCameraIds().size());
      Boolean flash=x.get(CameraCharacteristics.FLASH_INFO_AVAILABLE);
      j.put("flash",Boolean.TRUE.equals(flash));
      float[] apertures=x.get(CameraCharacteristics.LENS_INFO_AVAILABLE_APERTURES);
      JSONArray ap=new JSONArray(); if(apertures!=null)for(float v:apertures)ap.put(v); j.put("apertures",ap);
      int[] ois=x.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION);
      j.put("ois_modes",ois==null?new JSONArray():new JSONArray(ois));
      int[] stabilization=x.get(CameraCharacteristics.CONTROL_AVAILABLE_VIDEO_STABILIZATION_MODES);
      j.put("video_stabilization_modes",stabilization==null?new JSONArray():new JSONArray(stabilization));
      out.put(j);
    }
    return out;
  }

  private static JSONArray sensors(Context c){
    JSONArray out=new JSONArray();
    SensorManager sm=(SensorManager)c.getSystemService(Context.SENSOR_SERVICE);
    List<Sensor> sensors=sm.getSensorList(Sensor.TYPE_ALL);
    for(Sensor s:sensors){
      JSONObject j=new JSONObject();
      try{
        j.put("type",s.getType()); j.put("name",s.getName()); j.put("vendor",s.getVendor());
        j.put("version",s.getVersion()); j.put("power_ma",s.getPower()); j.put("max_range",s.getMaximumRange());
        out.put(j);
      }catch(Exception ignored){}
    }
    return out;
  }

  private static JSONObject compute(Context c)throws Exception{
    JSONObject j=new JSONObject();
    ActivityManager am=(ActivityManager)c.getSystemService(Context.ACTIVITY_SERVICE);
    ActivityManager.MemoryInfo mi=new ActivityManager.MemoryInfo(); am.getMemoryInfo(mi);
    j.put("cpu_cores",Runtime.getRuntime().availableProcessors());
    j.put("ram_total_bytes",mi.totalMem); j.put("ram_available_bytes",mi.availMem);
    j.put("low_memory",mi.lowMemory);
    StatFs fs=new StatFs(c.getFilesDir().getAbsolutePath());
    j.put("storage_available_bytes",fs.getAvailableBytes());
    j.put("storage_total_bytes",fs.getTotalBytes());
    return j;
  }

  private static JSONObject runtime(Context c)throws Exception{
    JSONObject j=new JSONObject();
    BatteryManager bm=(BatteryManager)c.getSystemService(Context.BATTERY_SERVICE);
    PowerManager pm=(PowerManager)c.getSystemService(Context.POWER_SERVICE);
    j.put("battery_percent",bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY));
    j.put("charging",bm.isCharging());
    j.put("power_save",pm.isPowerSaveMode());
    if(Build.VERSION.SDK_INT>=29)j.put("thermal_status",pm.getCurrentThermalStatus());
    return j;
  }

  private static JSONObject features(Context c)throws Exception{
    PackageManager p=c.getPackageManager(); JSONObject j=new JSONObject();
    j.put("camera_any",p.hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY));
    j.put("gps",p.hasSystemFeature(PackageManager.FEATURE_LOCATION_GPS));
    j.put("bluetooth_le",p.hasSystemFeature(PackageManager.FEATURE_BLUETOOTH_LE));
    j.put("usb_host",p.hasSystemFeature(PackageManager.FEATURE_USB_HOST));
    if(Build.VERSION.SDK_INT>=31)j.put("uwb",p.hasSystemFeature(PackageManager.FEATURE_UWB));
    return j;
  }

  private static String selectProfile(JSONObject root){
    try{
      JSONObject c=root.getJSONObject("compute"),r=root.getJSONObject("runtime");
      long ram=c.optLong("ram_total_bytes",0); int battery=r.optInt("battery_percent",100);
      int thermal=r.optInt("thermal_status",0); boolean saver=r.optBoolean("power_save",false);
      if(saver||battery<=15||thermal>=PowerManager.THERMAL_STATUS_SEVERE)return "NANO";
      if(ram<4L*1024*1024*1024)return "LIGHT";
      if(ram<8L*1024*1024*1024)return "BALANCED";
      return "PERFORMANCE";
    }catch(Exception e){return "LIGHT";}
  }

  public static File persist(Context c,JSONObject profile)throws Exception{
    File dir=new File(c.getFilesDir(),"hawkeye-device");
    if(!dir.exists()&&!dir.mkdirs())throw new java.io.IOException("cannot create Hawkeye device store");
    File f=new File(dir,"capabilities.json");
    try(java.io.FileOutputStream o=new java.io.FileOutputStream(f)){o.write(profile.toString(2).getBytes("UTF-8"));}
    return f;
  }
}
