package com.guardianlab.chat

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

internal object AccountPalette {
 private var catalog:List<JSONObject>?=null
 fun choices(context:Context):List<JSONObject> = catalog ?: JSONArray(context.assets.open("comparison-web/personalization.json").bufferedReader().use {it.readText()}).let {array->(0 until array.length()).map {array.getJSONObject(it)}.also {catalog=it}}
 fun selected(context:Context,owner:String):JSONObject {
  val id=context.getSharedPreferences("account",Context.MODE_PRIVATE).getString("palette-$owner","orbit-cyan-navy")
  return choices(context).firstOrNull {matches(it,id)}?:choices(context).first()
 }
 private fun matches(p:JSONObject,id:String?):Boolean {if(p.getString("id")==id)return true;val aliases=p.optJSONArray("aliases")?:return false;return (0 until aliases.length()).any {aliases.optString(it)==id}}
 fun remember(context:Context,owner:String,id:String){val p=choices(context).firstOrNull {matches(it,id)}?:return;context.getSharedPreferences("account",Context.MODE_PRIVATE).edit().putString("palette-$owner",p.getString("id")).apply()}
}
