package com.guardianlab.chat
import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import org.json.JSONObject
import java.io.*
import java.security.KeyStore
import javax.crypto.*
import javax.crypto.spec.GCMParameterSpec
/** App-private encrypted storage. Keys cannot be exported or backed up. */
class ProtectedStore(private val context:Context,private val account:String){
 private val directory=File(context.filesDir,"sealed-media/$account").apply {mkdirs()}
 private fun file(id:String):File {require(id.matches(Regex("[a-z0-9-]+")));return File(directory,id)}
 @Synchronized private fun key():javax.crypto.SecretKey {val alias="guardian-media-$account";val ks=KeyStore.getInstance("AndroidKeyStore").apply {load(null)};if(ks.containsAlias(alias))return ks.getKey(alias,null) as javax.crypto.SecretKey;return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore").apply {init(KeyGenParameterSpec.Builder(alias,KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())}.generateKey()}
 fun exists(id:String)=file(id).exists()
 fun remove(id:String){file(id).delete()}
 fun save(id:String,metadata:JSONObject,write:(OutputStream)->Unit){val target=file(id);val temp=File(directory,"$id.part");try{val cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());temp.outputStream().use {out->out.write(cipher.iv.size);out.write(cipher.iv);DataOutputStream(CipherOutputStream(out,cipher)).use {sealed->val json=metadata.toString().toByteArray();sealed.writeInt(json.size);sealed.write(json);write(sealed)}};check(temp.renameTo(target)){"Could not store encrypted media"}}finally{temp.delete()}}
 fun open(id:String,out:File):JSONObject {try{file(id).inputStream().use {input->val n=input.read();require(n in 12..32);val iv=ByteArray(n);DataInputStream(input).readFully(iv);val cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,iv));DataInputStream(CipherInputStream(input,cipher)).use {clear->val length=clear.readInt();require(length in 1..65536);val json=ByteArray(length);clear.readFully(json);out.outputStream().use {clear.copyTo(it)};return JSONObject(String(json))}}}catch(e:Exception){out.delete();throw e}}
}
