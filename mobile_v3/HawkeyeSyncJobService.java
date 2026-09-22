package com.krishna.mobile;

import android.app.job.JobParameters;
import android.app.job.JobService;

public class HawkeyeSyncJobService extends JobService {
  @Override public boolean onStartJob(JobParameters params){
    new Thread(()->{
      boolean retry=false;
      try{org.json.JSONObject r=HawkeyeBackgroundSync.syncOne(this);retry=r.has("error")||r.optBoolean("retained_local",false);}
      catch(Exception e){retry=true;}
      final boolean again=retry;runOnUiThreadSafe(()->jobFinished(params,again));
    },"hawkeye-bg-sync").start();
    return true;
  }
  void runOnUiThreadSafe(Runnable r){new android.os.Handler(android.os.Looper.getMainLooper()).post(r);}
  @Override public boolean onStopJob(JobParameters params){return true;}
}
