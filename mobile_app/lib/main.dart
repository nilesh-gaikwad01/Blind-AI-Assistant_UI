import 'dart:async';
import 'dart:convert';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';


// =======================================================
// CONSTANTS
// =======================================================

const String kServerBase   = 'http://10.134.238.102:5000'; // ← your laptop IP
const String kFamilyNumber = '+917028370897';              // ← replace with real number

const Color kCyan   = Color(0xFF00BCD4);
const Color kBlue   = Color(0xFF1E88E5);
const Color kGreen  = Color(0xFF43A047);
const Color kOrange = Color(0xFFEF6C00);
const Color kPurple = Color(0xFF8E24AA);
const Color kRed    = Color(0xFFE53935);

// =======================================================
// ENTRY POINT
// =======================================================

late List<CameraDescription> cameras;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  await Permission.camera.request();
  await Permission.microphone.request();
  await Permission.phone.request();
  cameras = await availableCameras();
  runApp(const BlindAssistApp());
}

// =======================================================
// APP
// =======================================================

class BlindAssistApp extends StatelessWidget {
  const BlindAssistApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Blind Assist AI',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: Colors.black,
        colorScheme: const ColorScheme.dark(
          primary: kCyan,
          secondary: kCyan,
        ),
      ),
      home: const BlindAssistScreen(),
    );
  }
}

// =======================================================
// FEATURE MODEL
// =======================================================

class AssistMode {
  final String name;
  final String endpoint;
  final IconData icon;
  final Color color;
  final String voiceLabel;

  const AssistMode({
    required this.name,
    required this.endpoint,
    required this.icon,
    required this.color,
    required this.voiceLabel,
  });
}

// =======================================================
// SCREEN
// =======================================================

class BlindAssistScreen extends StatefulWidget {
  const BlindAssistScreen({super.key});

  @override
  State<BlindAssistScreen> createState() => _BlindAssistScreenState();
}

class _BlindAssistScreenState extends State<BlindAssistScreen>
    with WidgetsBindingObserver {

  // ---- Camera ----
  CameraController? _cameraController;
  bool _cameraReady = false;

  // ---- TTS (phone speaker — primary output) ----
  final FlutterTts _tts = FlutterTts();

  // // ---- STT (phone mic — primary input) ----
  // final SpeechToText _stt = SpeechToText();
  // bool _sttAvailable = false;

  // ---- Modes ----
  static const List<AssistMode> _modes = [
    AssistMode(
      name: 'Navigation',
      endpoint: '/set_mode/navigation',
      icon: Icons.navigation_rounded,
      color: kBlue,
      voiceLabel: 'navigation',
    ),
    AssistMode(
      name: 'Currency',
      endpoint: '/set_mode/currency',
      icon: Icons.currency_rupee_rounded,
      color: kGreen,
      voiceLabel: 'currency',
    ),
    AssistMode(
      name: 'Read Text',
      endpoint: '/set_mode/read',
      icon: Icons.text_fields_rounded,
      color: kOrange,
      voiceLabel: 'read text',
    ),
    AssistMode(
      name: 'Family',
      endpoint: '',
      icon: Icons.phone_rounded,
      color: kPurple,
      voiceLabel: 'family',
    ),
  ];

  // ---- State ----
  int      _activeModeIndex = 0;
  String   _statusText      = 'Starting...';
  String   _currentLang     = 'en-US';
  bool     _isProcessing    = false;
  bool     _isSOSActive     = false;
  bool     _isListening     = false;
  bool     _serverReachable = true;

  // ---- TTS cooldown (3 seconds, no repeat, no interrupt) ----
  String   _lastSpokenText = '';
  DateTime _lastSpokenTime = DateTime.now();

  // ---- Timer ----
  Timer? _frameTimer;

  AssistMode get _activeMode => _modes[_activeModeIndex];

  // =======================================================
  // LIFECYCLE
  // =======================================================

  @override
  void initState() {
  super.initState();
  WidgetsBinding.instance.addObserver(this);
  _setupTTS();
  _requestPermissionsAndInit();
}
 
Future<void> _requestPermissionsAndInit() async {
  // Request location permission early so SOS doesn't stall on first press
  await Permission.location.request();
  _initCamera();
}

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _frameTimer?.cancel();
    _cameraController?.dispose();
    _tts.stop();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final ctrl = _cameraController;
    if (ctrl == null || !ctrl.value.isInitialized) return;
    if (state == AppLifecycleState.inactive) {
      _frameTimer?.cancel();
      ctrl.dispose();
      setState(() => _cameraReady = false);
    } else if (state == AppLifecycleState.resumed) {
      _initCamera();
    }
  }

  // =======================================================
  // CAMERA
  // =======================================================

  Future<void> _initCamera() async {
    final status = await Permission.camera.status;
    if (!status.isGranted) {
      final result = await Permission.camera.request();
      if (!result.isGranted) {
        _setStatus('Camera permission denied');
        return;
      }
    }

    if (cameras.isEmpty) {
      _setStatus('No camera found');
      return;
    }

    final controller = CameraController(
      cameras[0],
      ResolutionPreset.medium,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.jpeg,
    );

    try {
      await controller.initialize();
      if (!mounted) return;
      _cameraController = controller;
      setState(() {
        _cameraReady = true;
        _statusText  = 'Navigation mode active';
      });
      await _speakWelcome();
      _startFrameLoop();
    } catch (e) {
      _setStatus('Camera error. Restart app.');
      debugPrint('Camera error: $e');
    }
  }

  // =======================================================
  // TTS — PRIMARY OUTPUT (phone speaker)
  // =======================================================

  Future<void> _setupTTS() async {
    await _tts.setLanguage(_currentLang);
    await _tts.setSpeechRate(0.5);
    await _tts.setVolume(1.0);
    await _tts.setPitch(1.0);
  }

  Future<void> _speak(String text) async {
  if (text.isEmpty) return;

  final now              = DateTime.now();
  final secondsSinceLast = now.difference(_lastSpokenTime).inSeconds;

  // Don't repeat same message within 3 seconds
  if (text == _lastSpokenText && secondsSinceLast < 3) return;

  _lastSpokenText = text;
  _lastSpokenTime = now;
  await _tts.stop();
  await _tts.setLanguage(_currentLang);
  await _tts.speak(text);
}

  Future<void> _speakWelcome() async {
    await Future.delayed(const Duration(seconds: 1));
    // Force welcome — bypass cooldown
    await _tts.setLanguage(_currentLang);
    await _tts.speak('Welcome to Blind Assist AI');
    await Future.delayed(const Duration(seconds: 2));
    await _tts.speak('Navigation mode activated');
  }

  // =======================================================
  // STT — VOICE INPUT (phone mic)
  // =======================================================


  Future<void> _onMicTap() async {
  setState(() {
    _isListening = true;
    _statusText = 'Listening...';
  });

  await _tts.stop();
  await _tts.speak('Listening');

  // Use Android native speech recognition via method channel
  const platform = MethodChannel('com.blindassist/speech');
  try {
    final String result = await platform.invokeMethod('listen');
    final command = result.toLowerCase().trim();
    debugPrint('Voice command: $command');
    await _handleVoiceCommand(command);
  } catch (e) {
    debugPrint('Speech error: $e');
    _setStatus('Could not recognize speech');
  } finally {
    if (mounted) {
      setState(() {
        _isListening = false;
        _statusText = '${_activeMode.name} mode active';
      });
    }
  }
}

  // =======================================================
  // VOICE COMMAND HANDLER
  // =======================================================

  Future<void> _handleVoiceCommand(String command) async {
    debugPrint('Handling: $command');

    if (command.contains('navigation') || command.contains('navigate')) {
      await _switchMode(0);
    } else if (command.contains('currency') ||
               command.contains('money')    ||
               command.contains('note')) {
      await _switchMode(1);
    } else if (command.contains('read') || command.contains('text')) {
      await _switchMode(2);
    } else if (command.contains('family') ||
               command.contains('call')   ||
               command.contains('phone')) {
      await _callFamily();
    } else if (command.contains('sos')       ||
               command.contains('emergency') ||
               command.contains('help')) {
      await _triggerSOS();
    } else {
      _setStatus('Not recognized: "$command"');
      await _tts.speak(
        'Command not recognized. Try navigation, currency, read text, or call family.',
      );
    }
  }

  // =======================================================
  // FRAME LOOP — sends frame every 1200ms, reads result back
  // =======================================================

  void _startFrameLoop() {
    _frameTimer?.cancel();
    _frameTimer = Timer.periodic(
      const Duration(milliseconds: 1200), // ← 1200ms
      (_) => _sendFrame(),
    );
  }

  Future<void> _sendFrame() async {
  if (_isProcessing) return;
  if (_activeModeIndex == 3) return;
  final ctrl = _cameraController;
  if (ctrl == null || !ctrl.value.isInitialized) return;

  _isProcessing = true;
  try {
    final XFile file  = await ctrl.takePicture();
    final bytes       = await file.readAsBytes();
    final base64Image = base64Encode(bytes);

    final response = await http
        .post(
          Uri.parse('$kServerBase/upload_frame'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'image': 'data:image/jpeg;base64,$base64Image',
          }),
        )
        .timeout(const Duration(seconds: 3));

    if (response.statusCode == 200) {
      if (!_serverReachable && mounted) {
        setState(() => _serverReachable = true);
      }

      // ← READ response and speak on phone
      try {
        final data    = jsonDecode(response.body);
        final message = (data['message'] as String? ?? '').trim();
        if (message.isNotEmpty && message != 'ok') {
          _setStatus(message);
          await _speak(message);
        }
      } catch (_) {}
    }
  } catch (_) {
    if (_serverReachable && mounted) {
      setState(() => _serverReachable = false);
      await _tts.speak('Connection lost'); // ← just this one line added
    }
  } finally {
    _isProcessing = false;
  }
}

  // =======================================================
  // MODE SWITCH
  // =======================================================
  
  Future<void> _switchMode(int index) async {
    HapticFeedback.mediumImpact();
    if (_activeModeIndex == index) return;

    setState(() {
      _activeModeIndex = index;
      _statusText      = '${_modes[index].name} mode activated';
      _lastSpokenText  = ''; // reset cooldown so announcement plays
    });

    // Force speak mode announcement
    await _tts.stop();
    await _tts.speak('${_modes[index].voiceLabel} mode activated');

    if (index == 3) return; // Family — no backend mode needed

    try {
      await http
          .post(Uri.parse('$kServerBase${_modes[index].endpoint}'))
          .timeout(const Duration(seconds: 3));
    } catch (_) {}
  }

  // =======================================================

  // Replace your _callFamily() method with this:
 
 Future<void> _callFamily() async {
  HapticFeedback.mediumImpact();
  await _tts.stop();
  await _tts.speak('Calling family member');
  await Future.delayed(const Duration(milliseconds: 600));

  // Request CALL_PHONE permission at runtime
  final status = await Permission.phone.status;
  if (!status.isGranted) {
    final result = await Permission.phone.request();
    if (!result.isGranted) {
      _setStatus('Phone permission denied');
      await _tts.speak('Phone permission denied. Please allow in settings.');
      return;
    }
  }

  // Use native Android call — bypasses dialer completely
  const platform = MethodChannel('com.blindassist/speech');
  try {
    await platform.invokeMethod('call', {'number': kFamilyNumber});
  } catch (e) {
    debugPrint('Call error: $e');
    _setStatus('Call failed');
    await _tts.speak('Call failed. Check phone permission.');
  }
}

  // =======================================================
  // SOS
  // =======================================================

 Future<void> _triggerSOS() async {
  HapticFeedback.mediumImpact();
  if (_isSOSActive) return;
  setState(() => _isSOSActive = true);
 
  await _tts.stop();
  await _tts.speak('Emergency alert sending');
 
  try {
    // ── Request location permission at runtime ──
    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
 
    double? lat;
    double? lng;
 
    if (permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse) {
      try {
        // 8-second timeout so GPS doesn't stall the SOS
        final Position position = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
        ).timeout(const Duration(seconds: 8));
        lat = position.latitude;
        lng = position.longitude;
        debugPrint('GPS obtained: $lat, $lng');
      } catch (gpsError) {
        // GPS timed out — send SOS without location (server falls back to IP)
        debugPrint('GPS timeout — sending SOS without GPS: $gpsError');
      }
    } else {
      debugPrint('Location permission denied — sending SOS without GPS');
    }
 
    // Fire and forget — server returns instantly now (automation runs in background)
    final response = await http.post(
      Uri.parse('$kServerBase/whatsapp'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        if (lat != null) 'lat': lat,
        if (lng != null) 'lng': lng,
      }),
    ).timeout(const Duration(seconds: 6));
 
    if (response.statusCode == 200) {
      _setStatus('Emergency alert sent');
      await _tts.speak('Emergency alert sent successfully');
    } else {
      throw Exception('Server returned ${response.statusCode}');
    }
 
  } on TimeoutException {
    _setStatus('Server timeout — check WiFi');
    await _tts.speak('Server not responding. Check WiFi connection.');
  } catch (e) {
    debugPrint('SOS error: $e');
    _setStatus('Failed to send alert');
    await _tts.speak('Failed to send emergency alert. Check WiFi connection.');
  } finally {
    if (mounted) setState(() => _isSOSActive = false);
  }
}
  // =======================================================
  // LANGUAGE CYCLE
  // =======================================================

  Future<void> _cycleLanguage() async {
    const langs  = ['en-US', 'hi-IN', 'mr-IN'];
    const labels = ['EN', 'HI', 'MR'];
    final next   = (langs.indexOf(_currentLang) + 1) % langs.length;
    setState(() => _currentLang = langs[next]);
    await _setupTTS();
    await _tts.speak('Language changed to ${labels[next]}');
  }

  String get _langLabel {
    switch (_currentLang) {
      case 'hi-IN': return 'HI';
      case 'mr-IN': return 'MR';
      default:      return 'EN';
    }
  }

  void _setStatus(String text) {
    if (mounted) setState(() => _statusText = text);
  }

  // =======================================================
  // BUILD
  // =======================================================

  @override
  Widget build(BuildContext context) {
    if (!_cameraReady || _cameraController == null) {
      return Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(color: kCyan, strokeWidth: 2),
              const SizedBox(height: 20),
              Text(
                _statusText == 'Starting...'
                    ? 'Starting camera...'
                    : _statusText,
                style: const TextStyle(color: Colors.white70, fontSize: 16),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const ClampingScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [

              _TopBar(
                langLabel: _langLabel,
                serverOk:  _serverReachable,
                onLangTap: _cycleLanguage,
              ),

              const SizedBox(height: 8),

              const Text(
                'BLIND ASSIST AI',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 28,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 2,
                ),
              ),

              const SizedBox(height: 14),

              AnimatedSwitcher(
                duration: const Duration(milliseconds: 350),
                child: Text(
                  _activeMode.name,
                  key: ValueKey(_activeMode.name),
                  style: TextStyle(
                    color: _activeMode.color,
                    fontSize: 30,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),

              const SizedBox(height: 6),

              AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                child: Text(
                  _statusText,
                  key: ValueKey(_statusText),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white60,
                    fontSize: 14,
                    height: 1.4,
                  ),
                ),
              ),

              const SizedBox(height: 18),

              // Camera preview
              Container(
                height: 230,
                width: double.infinity,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(color: kCyan, width: 2),
                  boxShadow: [
                    BoxShadow(
                      color: kCyan.withOpacity(0.25),
                      blurRadius: 14,
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: CameraPreview(_cameraController!),
                ),
              ),

              const SizedBox(height: 24),

              // Mic button
              GestureDetector(
                onTap: _onMicTap,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  height: 88,
                  width: 88,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _isListening ? Colors.greenAccent : kCyan,
                    boxShadow: [
                      BoxShadow(
                        color: (_isListening
                                ? Colors.greenAccent
                                : kCyan)
                            .withOpacity(0.5),
                        blurRadius: 20,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: Icon(
                    _isListening
                        ? Icons.mic_rounded
                        : Icons.mic_none_rounded,
                    color: Colors.black,
                    size: 42,
                  ),
                ),
              ),

              const SizedBox(height: 8),

              Text(
                _isListening ? 'Listening...' : 'Tap to speak',
                style: TextStyle(
                  color: _isListening ? kCyan : Colors.white70,
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                ),
              ),

              const SizedBox(height: 26),

              // Mode grid
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisSpacing: 14,
                mainAxisSpacing: 14,
                childAspectRatio: 1.55,
                children: List.generate(
                  _modes.length,
                  (i) => _ModeCard(
                    mode:     _modes[i],
                    isActive: _activeModeIndex == i,
                    onTap:    () => i == 3 ? _callFamily() : _switchMode(i),
                  ),
                ),
              ),

              const SizedBox(height: 30),

              // SOS
              GestureDetector(
                onLongPressStart: (_) => _triggerSOS(),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  height: 80,
                  width: 210,
                  decoration: BoxDecoration(
                    color: _isSOSActive ? Colors.red.shade900 : kRed,
                    borderRadius: BorderRadius.circular(22),
                    boxShadow: [
                      BoxShadow(
                        color: kRed.withOpacity(_isSOSActive ? 0.8 : 0.4),
                        blurRadius: _isSOSActive ? 28 : 14,
                      ),
                    ],
                  ),
                  child: Center(
                    child: _isSOSActive
                        ? const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
                              ),
                              SizedBox(width: 10),
                              Text(
                                'Sending...',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          )
                        : const Text(
                            'SOS',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 34,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 3,
                            ),
                          ),
                  ),
                ),
              ),

              const SizedBox(height: 6),

              const Text(
                'Hold to send emergency alert',
                style: TextStyle(color: Colors.white38, fontSize: 12),
              ),

              const SizedBox(height: 28),
            ],
          ),
        ),
      ),
    );
  }
}

// =======================================================
// TOP BAR
// =======================================================

class _TopBar extends StatelessWidget {
  final String langLabel;
  final bool serverOk;
  final VoidCallback onLangTap;

  const _TopBar({
    required this.langLabel,
    required this.serverOk,
    required this.onLangTap,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: [
            const Icon(Icons.remove_red_eye_rounded, color: kCyan, size: 42),
            const SizedBox(width: 8),
            Container(
              width: 9,
              height: 9,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: serverOk ? Colors.greenAccent : Colors.redAccent,
              ),
            ),
          ],
        ),
        GestureDetector(
          onTap: onLangTap,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
            decoration: BoxDecoration(
              color: kCyan,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Text(
              langLabel,
              style: const TextStyle(
                color: Colors.black,
                fontWeight: FontWeight.bold,
                fontSize: 15,
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// =======================================================
// MODE CARD
// =======================================================

class _ModeCard extends StatelessWidget {
  final AssistMode mode;
  final bool isActive;
  final VoidCallback onTap;

  const _ModeCard({
    required this.mode,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 280),
        decoration: BoxDecoration(
          color: isActive
              ? mode.color.withOpacity(0.15)
              : Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isActive ? Colors.white : mode.color,
            width: isActive ? 2.5 : 1.8,
          ),
          boxShadow: isActive
              ? [
                  BoxShadow(
                    color: mode.color.withOpacity(0.45),
                    blurRadius: 16,
                    spreadRadius: 1,
                  ),
                ]
              : [],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(mode.icon, color: mode.color, size: 34),
            const SizedBox(height: 10),
            Text(
              mode.name,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 15,
              ),
            ),
          ],
        ),
      ),
    );
  }
}