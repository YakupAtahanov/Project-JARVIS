#!/usr/bin/env python3
"""
Vosk Wake Word Detection Demo

This example demonstrates how to use Vosk for offline wake word detection.
Vosk is a completely offline speech recognition toolkit that can be used
for wake word detection without any internet connection.

Requirements:
    pip install vosk pyaudio

Usage:
    python vosk_demo.py
"""

import json
import pyaudio
import vosk
import sys
import time
import threading
from queue import Queue

class VoskWakeWordDetector:
    """Simple wake word detector using Vosk."""
    
    def __init__(self, model_path=None, wake_words=["jarvis", "hey jarvis"]):
        """
        Initialize Vosk wake word detector.
        
        Args:
            model_path: Path to Vosk model (if None, will try to download)
            wake_words: List of wake words to detect
        """
        self.wake_words = [word.lower() for word in wake_words]
        self.model_path = model_path
        self.model = None
        self.recognizer = None
        self.audio = None
        self.stream = None
        self.running = False
        self.detection_queue = Queue()
        
    def initialize(self):
        """Initialize Vosk model and audio."""
        try:
            # Initialize Vosk model
            if self.model_path:
                self.model = vosk.Model(self.model_path)
            else:
                # Try to use a small model (you'll need to download this)
                print("⚠️  No model path provided. You need to download a Vosk model.")
                print("💡 Download from: https://alphacephei.com/vosk/models")
                print("💡 Example: wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
                return False
            
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
            
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8000
            )
            
            print("✅ Vosk wake word detector initialized successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Vosk: {e}")
            return False
    
    def start_listening(self):
        """Start listening for wake words."""
        if not self.initialize():
            return False
            
        self.running = True
        print("👂 Listening for wake words...")
        print(f"🎯 Wake words: {', '.join(self.wake_words)}")
        print("Press Ctrl+C to stop.\n")
        
        try:
            while self.running:
                data = self.stream.read(4000, exception_on_overflow=False)
                
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').lower().strip()
                    
                    if text:
                        print(f"📝 Recognized: '{text}'")
                        
                        # Check if any wake word is in the recognized text
                        for wake_word in self.wake_words:
                            if wake_word in text:
                                print(f"🎯 WAKE WORD DETECTED: '{wake_word}'")
                                print(f"   Full text: '{text}'")
                                print(f"   Time: {time.strftime('%H:%M:%S')}")
                                print("   → This is where you'd start your voice processing pipeline\n")
                                
                                # Queue the detection
                                self.detection_queue.put({
                                    'wake_word': wake_word,
                                    'full_text': text,
                                    'timestamp': time.time()
                                })
                                break
                else:
                    # Partial result
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get('partial', '').lower().strip()
                    if partial_text:
                        print(f"🔄 Partial: '{partial_text}'", end='\r')
                        
        except KeyboardInterrupt:
            print("\n👋 Stopping...")
        except Exception as e:
            print(f"❌ Error during listening: {e}")
        finally:
            self.stop_listening()
    
    def stop_listening(self):
        """Stop listening and cleanup."""
        self.running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        
        print("🔇 Listening stopped")
    
    def get_detection(self, timeout=None):
        """Get the next wake word detection."""
        try:
            return self.detection_queue.get(timeout=timeout)
        except:
            return None

def main():
    """Main demo function."""
    print("🎤 Vosk Wake Word Detection Demo")
    print("=" * 50)
    
    # You need to download a Vosk model first
    # Download from: https://alphacephei.com/vosk/models
    # Example: wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    # Then unzip it and provide the path
    
    model_path = "vosk-model-small-en-us-0.15"  # Set this to your model path
    
    if not model_path:
        print("❌ No model path provided!")
        print("\n📥 To get started:")
        print("1. Download a Vosk model:")
        print("   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        print("2. Unzip it:")
        print("   unzip vosk-model-small-en-us-0.15.zip")
        print("3. Update the model_path in this script")
        print("4. Run the demo again")
        return
    
    # Create detector
    detector = VoskWakeWordDetector(
        model_path=model_path,
        wake_words=["jarvis", "hey jarvis", "okay jarvis"]
    )
    
    try:
        # Start listening
        detector.start_listening()
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    finally:
        detector.stop_listening()
        print("✅ Demo completed")

if __name__ == "__main__":
    main()
