package com.krishna.mobile;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import java.io.*;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Android-Keystore backed AES-GCM encryption for Hawkeye evidence at rest. */
public final class HawkeyeCrypto {
  private static final String KEYSTORE="AndroidKeyStore";
  private static final String ALIAS="krishna_hawkeye_evidence_v1";
  private HawkeyeCrypto(){}

  static SecretKey key()throws Exception{
    KeyStore ks=KeyStore.getInstance(KEYSTORE);ks.load(null);
    java.security.Key existing=ks.getKey(ALIAS,null);
    if(existing instanceof SecretKey)return (SecretKey)existing;
    KeyGenerator gen=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,KEYSTORE);
    gen.init(new KeyGenParameterSpec.Builder(ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
      .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
      .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
      .setKeySize(256).build());
    return gen.generateKey();
  }

  public static void encryptToFile(byte[] plain,File target)throws Exception{
    Cipher c=Cipher.getInstance("AES/GCM/NoPadding");c.init(Cipher.ENCRYPT_MODE,key());
    byte[] iv=c.getIV(),sealed=c.doFinal(plain);
    if(iv==null||iv.length<12||iv.length>32)throw new GeneralSecurityException("invalid GCM IV");
    try(DataOutputStream out=new DataOutputStream(new FileOutputStream(target))){
      out.writeInt(0x48415731);out.writeByte(iv.length);out.write(iv);out.write(sealed);
    }
  }

  public static byte[] decryptFile(File source)throws Exception{
    try(DataInputStream in=new DataInputStream(new FileInputStream(source))){
      if(in.readInt()!=0x48415731)throw new GeneralSecurityException("invalid Hawkeye evidence header");
      int n=in.readUnsignedByte();if(n<12||n>32)throw new GeneralSecurityException("invalid GCM IV length");
      byte[] iv=new byte[n];in.readFully(iv);
      ByteArrayOutputStream b=new ByteArrayOutputStream();byte[] buf=new byte[8192];
      for(int r;(r=in.read(buf))>0;)b.write(buf,0,r);
      Cipher c=Cipher.getInstance("AES/GCM/NoPadding");
      c.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,iv));
      return c.doFinal(b.toByteArray());
    }
  }

  static final class GeneralSecurityException extends Exception{
    GeneralSecurityException(String m){super(m);}
  }
}
