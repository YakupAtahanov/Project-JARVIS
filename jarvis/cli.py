"""
CLI interface for JARVIS AI Assistant

Usage:
    jarvis                    # Start voice activation mode
    jarvis text               # Set text output mode
    jarvis voice              # Set voice output mode
    jarvis ask "<message>"    # Ask a question
    jarvis output-type        # Show current output mode
"""

import sys
import os
from pathlib import Path
from .config import Config


ENV_FILE = Path(__file__).parent / ".env"


def set_output_mode(mode: str) -> None:
    """
    Update OUTPUT_MODE in .env file
    
    Args:
        mode: 'text' or 'voice'
    """
    if mode not in ["text", "voice"]:
        print(f"Error: Invalid mode '{mode}'. Must be 'text' or 'voice'")
        sys.exit(1)
    
    # Read current .env or config.env.template
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text().splitlines()
    else:
        # If .env doesn't exist, try template
        template_file = Path(__file__).parent / "config.env.template"
        if template_file.exists():
            print(f"Creating .env from template...")
            lines = template_file.read_text().splitlines()
        else:
            lines = []
    
    # Update or add OUTPUT_MODE
    found = False
    for i, line in enumerate(lines):
        if line.startswith("OUTPUT_MODE=") or line.startswith("#OUTPUT_MODE="):
            lines[i] = f"OUTPUT_MODE={mode}"
            found = True
            break
    
    if not found:
        lines.append(f"OUTPUT_MODE={mode}")
    
    # Write back to .env
    ENV_FILE.write_text("\n".join(lines) + "\n")
    
    # Update current process environment
    os.environ["OUTPUT_MODE"] = mode
    Config.OUTPUT_MODE = mode
    
    print(f"✓ Output mode set to: {mode}")


def get_output_mode() -> str:
    """Get current output mode from config"""
    return Config.OUTPUT_MODE


def show_usage() -> None:
    """Display usage information"""
    print("JARVIS AI Assistant - CLI Interface")
    print()
    print("Usage:")
    print("  jarvis                    # Start voice activation mode")
    print("  jarvis text               # Set text output mode")
    print("  jarvis voice              # Set voice output mode")
    print("  jarvis ask \"<message>\"    # Ask a question")
    print("  jarvis output-type        # Show current output mode")
    print()
    print("Examples:")
    print("  jarvis                    # Start voice assistant")
    print("  jarvis text               # Switch to text output")
    print("  jarvis ask \"what is 2+2?\" # Ask a question")
    print("  jarvis output-type        # Check current mode")


def main() -> None:
    """Main CLI entry point"""
    # Import here to avoid circular imports and to delay heavy imports
    from .main import Jarvis
    
    # No arguments - start voice activation
    if len(sys.argv) == 1:
        print("Starting JARVIS in voice activation mode...")
        jarvis = Jarvis()
        jarvis.listen_with_activation()
        return
    
    # Parse command
    command = sys.argv[1]
    
    if command == "text":
        set_output_mode("text")
        
    elif command == "voice":
        set_output_mode("voice")
        
    elif command == "output-type":
        mode = get_output_mode()
        print(f"Current output mode: {mode}")
        
    elif command == "ask":
        if len(sys.argv) < 3:
            print("Error: Message required")
            print("Usage: jarvis ask \"<message>\"")
            sys.exit(1)
        
        # Combine all remaining arguments as the message
        message = " ".join(sys.argv[2:])
        
        # Initialize JARVIS in text mode (skip voice components)
        jarvis = Jarvis(text_mode=True)
        # ask() now handles output based on Config.OUTPUT_MODE
        jarvis.ask(message)
        
    elif command in ["-h", "--help", "help"]:
        show_usage()
        
    else:
        print(f"Error: Unknown command '{command}'")
        print()
        show_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()

