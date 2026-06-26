package com.example.blind_ai_app

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.speech.RecognizerIntent
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.util.Locale

class MainActivity : FlutterActivity() {

    private val CHANNEL        = "com.blindassist/speech"
    private val SPEECH_REQUEST = 100
    private var pendingResult: MethodChannel.Result? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {

                    // ── Voice recognition ──────────────────────
                    "listen" -> {
                        pendingResult = result
                        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                                     RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.ENGLISH)
                            putExtra(RecognizerIntent.EXTRA_PROMPT, "Say a command...")
                            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                        }
                        startActivityForResult(intent, SPEECH_REQUEST)
                    }

                    // ── Direct phone call — bypasses dialer ─────
                    "call" -> {
                        val number = call.argument<String>("number") ?: ""
                        try {
                            val callIntent = Intent(Intent.ACTION_CALL).apply {
                                data  = Uri.parse("tel:$number")
                                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                            }
                            startActivity(callIntent)
                            result.success("calling")
                        } catch (e: Exception) {
                            result.error("CALL_FAILED", e.message, null)
                        }
                    }

                    else -> result.notImplemented()
                }
            }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == SPEECH_REQUEST) {
            if (resultCode == Activity.RESULT_OK && data != null) {
                val results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                val text    = results?.firstOrNull() ?: ""
                pendingResult?.success(text)
            } else {
                pendingResult?.error("CANCELLED", "Speech cancelled", null)
            }
            pendingResult = null
        }
    }
}