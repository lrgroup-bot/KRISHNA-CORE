package com.krishna.mobile;

import com.google.android.gms.tasks.Tasks;
import com.google.mlkit.common.model.DownloadConditions;
import com.google.mlkit.nl.languageid.LanguageIdentification;
import com.google.mlkit.nl.languageid.LanguageIdentifier;
import com.google.mlkit.nl.translate.TranslateLanguage;
import com.google.mlkit.nl.translate.Translation;
import com.google.mlkit.nl.translate.Translator;
import com.google.mlkit.nl.translate.TranslatorOptions;

import org.json.JSONObject;

import java.util.concurrent.TimeUnit;

/**
 * Keyless, on-device text language detection + translation for HAWKEYE.
 *
 * Translation models are downloaded on demand (Wi-Fi by default) and inference
 * remains on device. No Gemini/cloud credential is used by this class.
 */
public final class HawkeyeLanguage {
  private static final LanguageIdentifier LANGUAGE_ID=LanguageIdentification.getClient();

  private HawkeyeLanguage(){}

  public static JSONObject translate(String text,String targetTag,boolean allowModelDownload)throws Exception{
    JSONObject out=new JSONObject();
    out.put("schema","hawkeye.mobile-translation.v1");
    out.put("engine","ML_KIT_ON_DEVICE_TRANSLATE");
    out.put("local_inference",true);
    out.put("api_key_required",false);
    out.put("attribution","Translation powered by Google ML Kit");

    String value=text==null?"":text.trim();
    if(value.isEmpty()){
      out.put("error","text is empty");
      return out;
    }
    if(value.length()>3000)value=value.substring(0,3000);

    String source=Tasks.await(LANGUAGE_ID.identifyLanguage(value),3,TimeUnit.SECONDS);
    if(source==null||"und".equals(source)){
      out.put("source_language","und");
      out.put("error","source language could not be identified");
      return out;
    }
    String sourceSupported=TranslateLanguage.fromLanguageTag(source);
    String targetSupported=TranslateLanguage.fromLanguageTag(targetTag==null?"":targetTag.trim().toLowerCase(java.util.Locale.US));
    if(sourceSupported==null){
      out.put("source_language",source);
      out.put("error","source language is not supported by ML Kit Translation");
      return out;
    }
    if(targetSupported==null){
      out.put("source_language",source);
      out.put("error","target language is not supported by ML Kit Translation");
      return out;
    }

    out.put("source_language",sourceSupported);
    out.put("target_language",targetSupported);
    if(sourceSupported.equals(targetSupported)){
      out.put("translated_text",value);
      out.put("model_downloaded_or_available",true);
      return out;
    }

    TranslatorOptions options=new TranslatorOptions.Builder()
      .setSourceLanguage(sourceSupported)
      .setTargetLanguage(targetSupported)
      .build();
    Translator translator=Translation.getClient(options);
    try{
      if(allowModelDownload){
        DownloadConditions conditions=new DownloadConditions.Builder().requireWifi().build();
        Tasks.await(translator.downloadModelIfNeeded(conditions),60,TimeUnit.SECONDS);
      }
      String translated=Tasks.await(translator.translate(value),8,TimeUnit.SECONDS);
      out.put("translated_text",translated==null?"":translated);
      out.put("model_downloaded_or_available",true);
      return out;
    }catch(Exception exc){
      out.put("model_downloaded_or_available",false);
      out.put("download_policy","Wi-Fi only unless implementation is explicitly changed");
      out.put("error",allowModelDownload
        ?"translation model unavailable or download/translation failed: "+exc.getClass().getSimpleName()
        :"translation model is not available locally");
      return out;
    }finally{
      translator.close();
    }
  }
}
