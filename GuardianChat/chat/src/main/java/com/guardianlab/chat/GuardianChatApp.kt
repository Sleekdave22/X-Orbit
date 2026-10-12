package com.guardianlab.chat
import android.app.Application
class GuardianChatApp:Application(){override fun onCreate(){super.onCreate();PushRegistration.ready(this)}}
