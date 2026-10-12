package com.guardianlab.chat

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.GradientDrawable
import android.media.*
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Gravity
import android.view.View
import android.widget.*
import java.io.File
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.max

class VoiceNoteView(context:Context,private val onPlay:(VoiceNoteView)->Unit):LinearLayout(context){
 private val handler=Handler(Looper.getMainLooper());private var player:MediaPlayer?=null;private var disposed=false;private var ready=false;private var seeking=false;private var pendingSeek=false
 private val play=TextView(context).apply {text="▶";textSize=22f;gravity=Gravity.CENTER;setTextColor(Color.rgb(230,69,112));contentDescription="Play voice note";isEnabled=false}
 private val wave=WaveView(context);private val seek=SeekBar(context).apply {max=10000;progressDrawable=ColorDrawable(Color.TRANSPARENT);thumb=GradientDrawable().apply {shape=GradientDrawable.OVAL;setColor(Color.rgb(230,69,112));setSize(dp(7),dp(20))};setPadding(0,0,0,0);contentDescription="Seek voice note";isEnabled=false}
 private val time=TextView(context).apply {text="Loading voice note…";textSize=10f;setTextColor(Color.GRAY)}
 init{orientation=HORIZONTAL;gravity=Gravity.CENTER_VERTICAL;addView(play,LayoutParams(dp(34),dp(42)));val centre=LinearLayout(context).apply {orientation=VERTICAL};val frame=FrameLayout(context);frame.addView(wave,FrameLayout.LayoutParams(-1,-1));frame.addView(seek,FrameLayout.LayoutParams(-1,-1));centre.addView(frame,LayoutParams(-1,dp(42)));centre.addView(time);addView(centre,LayoutParams(0,-2,1f));play.setOnClickListener {val p=player;if(ready&&p!=null){if(p.isPlaying)pause()else{onPlay(this);if(p.currentPosition>=p.duration)p.seekTo(0);p.start();play.text="Ⅱ";play.contentDescription="Pause voice note";handler.removeCallbacks(tick);handler.post(tick)}}};seek.setOnSeekBarChangeListener(object:SeekBar.OnSeekBarChangeListener{override fun onProgressChanged(bar:SeekBar?,value:Int,user:Boolean){if(user&&ready){wave.progress=value/10000f;time.text="${format((player?.duration?:0)*value/10000)} / ${format(player?.duration?:0)}"}};override fun onStartTrackingTouch(bar:SeekBar?){seeking=true;parent?.requestDisallowInterceptTouchEvent(true)};override fun onStopTrackingTouch(bar:SeekBar?){seeking=false;player?.let {pendingSeek=true;it.seekTo((it.duration.toLong()*seek.progress/10000).toInt())};parent?.requestDisallowInterceptTouchEvent(false)}})}
 private fun dp(n:Int)=(n*resources.displayMetrics.density).toInt()
 fun load(file:File){if(disposed)return;val p=MediaPlayer();player=p;try{p.setDataSource(file.absolutePath);p.setOnPreparedListener {if(disposed)return@setOnPreparedListener;ready=true;play.isEnabled=true;seek.isEnabled=true;updateTime()};p.setOnSeekCompleteListener {pendingSeek=false;updateTime()};p.setOnCompletionListener {play.text="▶";play.contentDescription="Play voice note";handler.removeCallbacks(tick);updateTime()};p.setOnErrorListener {_,_,_->ready=false;play.isEnabled=false;seek.isEnabled=false;handler.removeCallbacks(tick);time.text="Audio preview unavailable";true};p.prepareAsync()}catch(_:Exception){time.text="Audio preview unavailable"}}
 fun peaks(values:FloatArray){if(!disposed){wave.peaks=values;wave.invalidate()}}
 fun pause(){if(ready)player?.let {if(it.isPlaying)it.pause()};play.text="▶";play.contentDescription="Play voice note";handler.removeCallbacks(tick);updateTime()}
 fun dispose(){disposed=true;ready=false;handler.removeCallbacks(tick);player?.release();player=null}
 private fun updateTime(){if(!ready||seeking||pendingSeek)return;val p=player?:return;val duration=p.duration.coerceAtLeast(1);val value=p.currentPosition;seek.progress=(value.toLong()*10000/duration).toInt();wave.progress=value.toFloat()/duration;time.text="${format(value)} / ${format(duration)}";seek.contentDescription="Seek voice note, ${format(value)} of ${format(duration)}"}
 private fun format(ms:Int)="${ms/60000}:"+(ms/1000%60).toString().padStart(2,'0')
 private val tick=object:Runnable{override fun run(){if(disposed)return;updateTime();if(player?.isPlaying==true)handler.postDelayed(this,16)}}
 private class WaveView(context:Context):View(context){var peaks=FloatArray(56);var progress=0f;set(value){field=value;invalidate()};private val paint=Paint(Paint.ANTI_ALIAS_FLAG);override fun onDraw(canvas:Canvas){super.onDraw(canvas);val step=width.toFloat()/peaks.size;for(i in peaks.indices){paint.color=if(i.toFloat()/peaks.size<=progress)Color.rgb(230,69,112)else Color.GRAY;val h=max(3f,peaks[i]*(height-6));canvas.drawRoundRect(i*step,(height-h)/2,i*step+step*.6f,(height+h)/2,2f,2f,paint)}}}
 companion object{
  fun decodePeaks(file:File):FloatArray{val result=FloatArray(56);val extractor=MediaExtractor();var codec:MediaCodec?=null;try{extractor.setDataSource(file.absolutePath);val index=(0 until extractor.trackCount).firstOrNull {extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("audio/")==true}?:return result;extractor.selectTrack(index);val format=extractor.getTrackFormat(index);val duration=if(format.containsKey(MediaFormat.KEY_DURATION))format.getLong(MediaFormat.KEY_DURATION)else 0;if(duration<=0)return result;codec=MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME)!!);codec.configure(format,null,null,0);codec.start();val info=MediaCodec.BufferInfo();var inputEnd=false;var outputEnd=false;val deadline=SystemClock.elapsedRealtime()+10000;while(!outputEnd&&SystemClock.elapsedRealtime()<deadline){if(!inputEnd){val input=codec.dequeueInputBuffer(1000);if(input>=0){val buffer=codec.getInputBuffer(input)!!;val size=extractor.readSampleData(buffer,0);if(size<0){codec.queueInputBuffer(input,0,0,0,MediaCodec.BUFFER_FLAG_END_OF_STREAM);inputEnd=true}else{codec.queueInputBuffer(input,0,size,extractor.sampleTime,0);extractor.advance()}}};val output=codec.dequeueOutputBuffer(info,1000);if(output>=0){val buffer=codec.getOutputBuffer(output);if(buffer!=null&&info.size>0){val outputFormat=codec.outputFormat;val rate=outputFormat.getInteger(MediaFormat.KEY_SAMPLE_RATE);val channels=outputFormat.getInteger(MediaFormat.KEY_CHANNEL_COUNT);val floating=outputFormat.containsKey(MediaFormat.KEY_PCM_ENCODING)&&outputFormat.getInteger(MediaFormat.KEY_PCM_ENCODING)==AudioFormat.ENCODING_PCM_FLOAT;buffer.position(info.offset);buffer.limit(info.offset+info.size);val pcm=buffer.slice().order(ByteOrder.LITTLE_ENDIAN);val bytes=if(floating)4 else 2;var sample=0;while(pcm.remaining()>=bytes){val amplitude=if(floating)abs(pcm.float)else abs(pcm.short.toInt())/32768f;val stamp=info.presentationTimeUs+(sample/channels).toLong()*1000000/rate;val bin=(stamp*result.size/duration).toInt().coerceIn(0,result.lastIndex);result[bin]=max(result[bin],amplitude);sample++}};outputEnd=info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM!=0;codec.releaseOutputBuffer(output,false)}};val highest=result.maxOrNull()?:0f;if(highest>0)for(i in result.indices)result[i]/=highest}catch(_:Exception){}finally{try{codec?.stop()}catch(_:Exception){};codec?.release();extractor.release()};return result}
 }
}
