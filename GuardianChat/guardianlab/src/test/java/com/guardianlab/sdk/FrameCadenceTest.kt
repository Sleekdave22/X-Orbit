package com.guardianlab.sdk
import org.junit.Test
import org.junit.Assert.*
class FrameCadenceTest {
 @Test fun capsStartsAtFivePerSecond(){
  val c=FrameCadence();val starts=(0L until 1000L step 10).filter {c.shouldAnalyze(it)}
  assertEquals(listOf(0L,200L,400L,600L,800L),starts)
 }
 @Test fun longClearIntervalsDoNotDisableGate(){
  val c=FrameCadence();assertTrue(c.shouldAnalyze(0));assertTrue(c.shouldAnalyze(60000));assertFalse(c.shouldAnalyze(60001));assertTrue(c.shouldAnalyze(60200))
 }
 @Test fun missedDeadlinesNeverCreateCatchupBurst(){
  val c=FrameCadence();c.shouldAnalyze(0);assertTrue(c.shouldAnalyze(650));assertFalse(c.shouldAnalyze(651));assertTrue(c.shouldAnalyze(850))
 }
 @Test fun restartAllowsImmediateAnalysis(){val c=FrameCadence();c.shouldAnalyze(0);c.reset();assertTrue(c.shouldAnalyze(1))}
}
