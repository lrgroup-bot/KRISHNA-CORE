package com.krishna.mobile;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Local-only phone IMU context for HAWKEYE/BHOOMIPUTRA keyframes.
 *
 * This class does not claim SLAM or survey-grade pose. It records the latest
 * rotation-vector, accelerometer and gyroscope samples so multi-view evidence
 * can be correlated and handed to the existing PC-side spatial/photogrammetry
 * pipeline. No network request or API key is used.
 */
public final class HawkeyeSensorFusion implements SensorEventListener, AutoCloseable {
  private final SensorManager manager;
  private final Sensor accel;
  private final Sensor gyro;
  private final Sensor rotation;

  private final float[] accelValues=new float[]{Float.NaN,Float.NaN,Float.NaN};
  private final float[] gyroValues=new float[]{Float.NaN,Float.NaN,Float.NaN};
  private final float[] quaternion=new float[]{Float.NaN,Float.NaN,Float.NaN,Float.NaN};

  private volatile long accelAtNs=0L;
  private volatile long gyroAtNs=0L;
  private volatile long rotationAtNs=0L;
  private volatile int accelAccuracy=SensorManager.SENSOR_STATUS_UNRELIABLE;
  private volatile int gyroAccuracy=SensorManager.SENSOR_STATUS_UNRELIABLE;
  private volatile int rotationAccuracy=SensorManager.SENSOR_STATUS_UNRELIABLE;

  public HawkeyeSensorFusion(Context context){
    manager=(SensorManager)context.getSystemService(Context.SENSOR_SERVICE);
    accel=manager==null?null:manager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
    gyro=manager==null?null:manager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
    rotation=manager==null?null:manager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
    if(manager!=null){
      if(accel!=null)manager.registerListener(this,accel,SensorManager.SENSOR_DELAY_GAME);
      if(gyro!=null)manager.registerListener(this,gyro,SensorManager.SENSOR_DELAY_GAME);
      if(rotation!=null)manager.registerListener(this,rotation,SensorManager.SENSOR_DELAY_GAME);
    }
  }

  @Override public synchronized void onSensorChanged(SensorEvent event){
    if(event==null||event.sensor==null)return;
    int type=event.sensor.getType();
    if(type==Sensor.TYPE_ACCELEROMETER){
      copy3(event.values,accelValues);accelAtNs=event.timestamp;
    }else if(type==Sensor.TYPE_GYROSCOPE){
      copy3(event.values,gyroValues);gyroAtNs=event.timestamp;
    }else if(type==Sensor.TYPE_ROTATION_VECTOR){
      float[] q=new float[4];
      SensorManager.getQuaternionFromVector(q,event.values);
      System.arraycopy(q,0,quaternion,0,4);rotationAtNs=event.timestamp;
    }
  }

  @Override public void onAccuracyChanged(Sensor sensor,int accuracy){
    if(sensor==null)return;
    int type=sensor.getType();
    if(type==Sensor.TYPE_ACCELEROMETER)accelAccuracy=accuracy;
    else if(type==Sensor.TYPE_GYROSCOPE)gyroAccuracy=accuracy;
    else if(type==Sensor.TYPE_ROTATION_VECTOR)rotationAccuracy=accuracy;
  }

  public synchronized JSONObject snapshot()throws Exception{
    JSONObject out=new JSONObject();
    out.put("schema","hawkeye.mobile-sensor-fusion.v1");
    out.put("engine","ANDROID_SENSOR_MANAGER");
    out.put("local",true);
    out.put("api_key_required",false);
    out.put("timestamp_ms",System.currentTimeMillis());
    out.put("evidence_state","MEASURED");
    out.put("pose_authority",false);
    out.put("survey_grade",false);
    out.put("policy","IMU context only; do not treat as SLAM pose, depth, distance or survey-grade geometry.");

    JSONObject available=new JSONObject();
    available.put("accelerometer",accel!=null);
    available.put("gyroscope",gyro!=null);
    available.put("rotation_vector",rotation!=null);
    out.put("available",available);

    if(accelAtNs>0){
      JSONObject a=new JSONObject();
      a.put("m_s2",array3(accelValues));
      a.put("sensor_timestamp_ns",accelAtNs);
      a.put("accuracy",accelAccuracy);
      out.put("accelerometer",a);
    }
    if(gyroAtNs>0){
      JSONObject g=new JSONObject();
      g.put("rad_s",array3(gyroValues));
      g.put("sensor_timestamp_ns",gyroAtNs);
      g.put("accuracy",gyroAccuracy);
      out.put("gyroscope",g);
    }
    if(rotationAtNs>0){
      JSONObject r=new JSONObject();
      r.put("quaternion_wxyz",new JSONArray()
        .put((double)quaternion[0]).put((double)quaternion[1])
        .put((double)quaternion[2]).put((double)quaternion[3]));
      r.put("sensor_timestamp_ns",rotationAtNs);
      r.put("accuracy",rotationAccuracy);
      out.put("rotation_vector",r);
    }
    out.put("spatial_handoff_ready",rotationAtNs>0&&(accelAtNs>0||gyroAtNs>0));
    return out;
  }

  private static void copy3(float[] src,float[] dst){
    for(int i=0;i<3;i++)dst[i]=src!=null&&src.length>i?src[i]:Float.NaN;
  }

  private static JSONArray array3(float[] values){
    JSONArray a=new JSONArray();
    for(int i=0;i<3;i++)a.put(Float.isFinite(values[i])?(double)values[i]:JSONObject.NULL);
    return a;
  }

  @Override public void close(){
    if(manager!=null)manager.unregisterListener(this);
  }
}
