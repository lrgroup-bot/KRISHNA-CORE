package com.krishna.mobile;

import android.content.*;
import android.os.Bundle;
import android.service.voice.*;

/** Bridges a KRISHNA assistant session into the normal full-screen mobile UI. */
public final class KrishnaAssistantSessionService extends VoiceInteractionSessionService {
  @Override public VoiceInteractionSession onNewSession(Bundle args){
    return new KrishnaAssistantSession(this);
  }
}

final class KrishnaAssistantSession extends VoiceInteractionSession {
  KrishnaAssistantSession(Context context){super(context);}

  @Override public void onPrepareShow(Bundle args,int showFlags){
    super.onPrepareShow(args,showFlags);
    setUiEnabled(false);
  }

  @Override public void onShow(Bundle args,int showFlags){
    super.onShow(args,showFlags);
    String phrase=args==null?"Krishna":args.getString("phrase","Krishna");
    String mode=args==null?"chat":args.getString("mode","chat");
    Intent i=new Intent(getContext(),MainActivity.class)
      .setAction(MainActivity.ACTION_ASSIST_COMMAND)
      .putExtra("phrase",phrase)
      .putExtra("mode",mode)
      .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP);
    if(android.os.Build.VERSION.SDK_INT>=26)startAssistantActivity(i);
    else startVoiceActivity(i);
  }
}
