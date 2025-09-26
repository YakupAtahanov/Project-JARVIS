#!/usr/bin/env python3
"""
Test Voice Activation

This script tests the voice activation system without
the full JARVIS system.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'jarvis'))

from voice_activation import VoiceActivation
import time

def main():
    """Test the voice activation system."""
    print("🎤 Testing Voice Activation System")
    print("=" * 50)
    
    def on_wake_word():
        print("🚀 Wake word callback triggered!")
        print("   → This is where JARVIS would start processing your command")
    
    # Create voice activation instance
    va = VoiceActivation(
        wake_words=["jarvis", "hey jarvis", "okay jarvis"],
        model_path="vosk-model-small-en-us-0.15",
        sample_rate=16000,
        chunk_size=4000,
        sensitivity=0.8,
        on_wake_word=on_wake_word
    )
    
    try:
        # Start listening
        if va.start_listening():
            print("👂 Listening for wake words... Press Ctrl+C to exit")
            print("🎯 Try saying: 'Jarvis', 'Hey Jarvis', or 'Okay Jarvis'")
            
            # Main loop - check for activations
            while True:
                activation = va.get_activation(timeout=1.0)
                if activation:
                    print(f"📨 Received activation: {activation}")
                    
                # Print stats every 10 seconds
                if int(time.time()) % 10 == 0:
                    stats = va.get_stats()
                    print(f"📊 Stats: {stats['detection_count']} detections")
                    
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        va.cleanup()
        print("✅ Test completed")

if __name__ == "__main__":
    main()
