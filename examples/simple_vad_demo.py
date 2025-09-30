#!/usr/bin/env python3
"""
Simple Voice Activity Detection (VAD) Demo

This example demonstrates a simple wake word detection approach using
voice activity detection and energy thresholds. This is completely
offline and requires no external models or internet connection.

Requirements:
    pip install pyaudio numpy

Usage:
    python simple_vad_demo.py
"""

import pyaudio
import numpy as np
import time
import threading
from collections import deque

class SimpleVADDetector:
    """Simple voice activity detector for wake word detection."""
    
    def __init__(self, 
                 sample_rate=16000,
                 chunk_size=1024,
                 energy_threshold=500,
                 silence_duration=1.0,
                 speech_duration=0.5):
        """
        Initialize simple VAD detector.
        
        Args:
            sample_rate: Audio sample rate
            chunk_size: Audio chunk size
            energy_threshold: Energy threshold for speech detection
            silence_duration: Duration of silence before considering speech ended
            speech_duration: Minimum duration of speech to trigger
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.speech_duration = speech_duration
        
        # Audio processing
        self.audio = None
        self.stream = None
        self.running = False
        
        # State tracking
        self.speech_start_time = None
        self.last_speech_time = None
        self.is_speaking = False
        self.energy_history = deque(maxlen=10)  # Keep last 10 energy values
        
        # Callbacks
        self.on_speech_start = None
        self.on_speech_end = None
        
    def initialize(self):
        """Initialize audio system."""
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            print("✅ Simple VAD detector initialized successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize audio: {e}")
            return False
    
    def calculate_energy(self, audio_data):
        """Calculate energy of audio chunk."""
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        return np.sum(audio_array.astype(np.float32) ** 2) / len(audio_array)
    
    def start_listening(self):
        """Start listening for voice activity."""
        if not self.initialize():
            return False
            
        self.running = True
        print("👂 Listening for voice activity...")
        print(f"🎯 Energy threshold: {self.energy_threshold}")
        print(f"🎯 Speech duration: {self.speech_duration}s")
        print(f"🎯 Silence duration: {self.silence_duration}s")
        print("Press Ctrl+C to stop.\n")
        
        try:
            while self.running:
                # Read audio chunk
                audio_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Calculate energy
                energy = self.calculate_energy(audio_data)
                self.energy_history.append(energy)
                
                # Determine if speech is detected
                speech_detected = energy > self.energy_threshold
                current_time = time.time()
                
                if speech_detected:
                    if not self.is_speaking:
                        # Speech started
                        self.speech_start_time = current_time
                        self.is_speaking = True
                        print(f"🎤 Speech started (energy: {energy:.0f})")
                        
                        if self.on_speech_start:
                            self.on_speech_start()
                    
                    self.last_speech_time = current_time
                else:
                    if self.is_speaking:
                        # Check if silence duration has passed
                        if current_time - self.last_speech_time > self.silence_duration:
                            # Speech ended
                            speech_duration = current_time - self.speech_start_time
                            
                            if speech_duration >= self.speech_duration:
                                print(f"🎯 Speech detected! Duration: {speech_duration:.2f}s")
                                print(f"   → This is where you'd start your voice processing pipeline")
                                print(f"   → You could add keyword detection here (e.g., 'Jarvis')\n")
                                
                                if self.on_speech_end:
                                    self.on_speech_end(speech_duration)
                            else:
                                print(f"🔇 Speech too short: {speech_duration:.2f}s (ignored)")
                            
                            self.is_speaking = False
                            self.speech_start_time = None
                
                # Print energy level occasionally
                if int(current_time) % 5 == 0 and int(current_time) != int(getattr(self, '_last_print_time', 0)):
                    avg_energy = np.mean(list(self.energy_history))
                    print(f"📊 Energy: {energy:.0f} (avg: {avg_energy:.0f}, threshold: {self.energy_threshold})")
                    self._last_print_time = current_time
                    
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
    
    def set_callbacks(self, on_speech_start=None, on_speech_end=None):
        """Set callback functions."""
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end

def main():
    """Main demo function."""
    print("🎤 Simple Voice Activity Detection Demo")
    print("=" * 50)
    
    def on_speech_start():
        print("🚀 Speech started callback triggered!")
    
    def on_speech_end(duration):
        print(f"🏁 Speech ended callback triggered! Duration: {duration:.2f}s")
    
    # Create detector
    detector = SimpleVADDetector(
        energy_threshold=500,  # Adjust this based on your environment
        speech_duration=0.5,   # Minimum speech duration
        silence_duration=1.0   # Silence duration before considering speech ended
    )
    
    # Set callbacks
    detector.set_callbacks(on_speech_start, on_speech_end)
    
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
