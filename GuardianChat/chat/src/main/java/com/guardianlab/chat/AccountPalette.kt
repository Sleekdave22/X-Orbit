package com.guardianlab.chat

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

internal object AccountPalette {
 private var catalog:List<JSONObject>?=null
 fun choices(context:Context):List<JSONObject> = catalog ?: JSONArray(context.assets.open("comparison-web/personalization.json").bufferedReader().use {it.readText()}).let {array->(0 until array.length()).map {array.getJSONObject(it)}.also {catalog=it}}
 fun selected(context:Context,owner:String):JSONObject {
  val id=context.getSharedPreferences("account",Context.MODE_PRIVATE).getString("palette-$owner","oxblood-gold")
  return choices(context).firstOrNull {it.getString("id")==id}?:choices(context).first()
 }
 fun remember(context:Context,owner:String,id:String){if(choices(context).any {it.getString("id")==id})context.getSharedPreferences("account",Context.MODE_PRIVATE).edit().putString("palette-$owner",id).apply()}
}
