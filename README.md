# Project JARVIS

**AI-Native CLI (Prototype)**

Project JARVIS is an experimental AI-powered command-line interface designed to converse with the user, execute commands in the terminal, and report outputs back in real time.

---

## ✨ Current Functionality

- Interactive conversation with the user  
- Execution of commands directly in the terminal  
- Reporting terminal outputs back to the user  

---

## ⚡ Installation

1. **Clone the repository** (use the `main` branch).
   ```bash
   git clone -b main (https://github.com/YakupAtahanov/Project-JARVIS.git)
   cd Project-JARVIS
   ```
2. **Create required folders**:
   ```bash
   mkdir -p models/piper
   ```
3. **Download a Piper TTS model**:
   - Get both `.onnx` and `.onnx.json` files from [Piper samples](https://rhasspy.github.io/piper-samples/).  
   - Place them in `models/piper`.  
   - Example: [en_US-libritts_r-medium](https://rhasspy.github.io/piper-samples/#en_US-libritts_r-medium).  
4. **Create and activate a virtual environment** (if not already present):
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/MacOS
   venv\Scripts\activate      # Windows
   ```
5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
6. **Pull an LLM via Ollama** (example: `codegemma:7b-instruct-q5_K_M`):
   ```bash
   ollama pull codegemma:7b-instruct-q5_K_M
   ```
   (See [Ollama models](https://ollama.com/search) for alternatives.)
7. **Configure environment variables**:  
   - Create a `.env` file in the `/jarvis` folder.  
   - Populate it using `.env.example` as a template.  
8. **Run the application**:  
   ```bash
   python main.py
   ```

---

## 🖥️ System Requirements

- **Python**: 3.10 or later
- **Memory**: 8GB RAM (16GB recommended for larger models)
- **CPU**: x86_64 with AVX2 support (Apple Silicon and ARM64 builds may work but are untested)
- **GPU**: Optional, for acceleration of Ollama or Piper TTS models
- **OS**:
  - Windows 10/11
  - Linux (Ubuntu 20.04+ recommended)
  - MacOS (testing needed)

---

## 🔧 How It Works

1. **User Input**: The user types a message or request into the CLI.
2. **LLM Processing**: The input is passed to a Large Language Model (via Ollama).
3. **Command Handling**:
   - If the LLM detects a terminal command, it executes it.
   - If it detects a conversational query, it responds directly.
4. **Output Reporting**:
   - Command results are captured and displayed in the CLI.
   - Optionally, Piper generates speech output using the selected TTS model.

**Architecture overview**:
```
User → CLI → LLM (Ollama) → Command Execution → Output → (Piper TTS) → User
```

---

## 🚀 Roadmap / Required Improvements

1. **Performance**
   - Reduce response time to under 5s (excluding terminal I/O).
2. **Response Quality**
   - Eliminate repetitive outputs.
   - Improve detection of commands vs. conversations.
   - Investigate fine-tuning with code-specialized datasets.
3. **Cross-Platform Support**
   - ✅ Windows
   - ✅ Linux
   - ⚠️ MacOS (needs testing)
   - ⚠️ Raspberry Pi (needs testing)
4. **Scripting / Deployment**
   - Automated installation scripts.
   - Dockerized environment for portability.

---

## 🛠️ Next Steps

- Deeper OS-level integration (system services, background mode, etc.).
- Potential support for lightweight devices once performance optimizations are complete.

---
