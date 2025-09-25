# Project JARVIS

**AI-Native Voice Assistant with Dynamic Capability Discovery**

Project JARVIS is an innovative AI-powered voice assistant that combines natural language processing with dynamic tool discovery through SuperMCP (Super Model Context Protocol) orchestration. It can understand spoken commands, discover available tools dynamically, and execute them through specialized MCP servers.

---

## ✨ Revolutionary Features

- **🎤 Voice-First Interface**: Real-time speech recognition and synthesis
- **🧠 AI-Driven Tool Discovery**: Automatically discovers and uses available MCP servers
- **🔧 Dynamic Capability Extension**: Add new tools without code changes
- **🛡️ Secure Local Processing**: All operations run locally for privacy
- **🌐 Cross-Platform Support**: Windows, Linux, macOS compatibility
- **⚡ Self-Extending AI**: Can create new MCP servers on demand  

---

## ⚡ Installation

1. **Clone the repository with SuperMCP submodule**:
   ```bash
   git clone --recursive https://github.com/YakupAtahanov/Project-JARVIS.git
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

4. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/MacOS
   venv\Scripts\activate      # Windows
   ```

5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

6. **Install Ollama and pull an LLM model**:
   ```bash
   # Install Ollama from https://ollama.com/
   ollama pull codegemma:7b-instruct-q5_K_M
   ```

7. **Configure environment variables**:  
   - Copy `jarvis/config.env.template` to `jarvis/.env`
   - Adjust settings as needed for your system

8. **Run JARVIS**:  
   ```bash
   cd jarvis
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

1. **🎤 Voice Input**: User speaks into microphone, Whisper converts speech to text
2. **🧠 AI Processing**: LLM (via Ollama) analyzes the request and determines required tools
3. **🔍 Dynamic Discovery**: SuperMCP discovers available MCP servers and their capabilities
4. **⚡ Tool Execution**: Appropriate MCP servers execute the requested operations
5. **🔊 Voice Output**: Piper TTS converts the response back to speech

**Revolutionary Architecture**:
```
User Voice → Whisper (STT) → LLM → SuperMCP → MCP Servers → Response → Piper (TTS) → User
```

### **Available MCP Servers**
- **ShellMCP**: Terminal command execution
- **CodeAnalysisMCP**: Code repository analysis and file operations
- **EchoMCP**: Testing and validation
- **FileSystemMCP**: Advanced file system operations
- **[Extensible]**: Add custom MCP servers dynamically

---

## 🚀 Innovation & Future Vision

### **Current Capabilities**
- ✅ **Voice-First AI Assistant**: Real-time speech processing
- ✅ **Dynamic Tool Discovery**: SuperMCP orchestration
- ✅ **Local Privacy**: All processing on-device
- ✅ **Cross-Platform**: Windows, Linux, macOS support
- ✅ **Extensible Architecture**: Plugin-based MCP servers

### **Revolutionary Features in Development**
- 🔄 **AI-Driven MCP Generation**: AI creates new tools on demand
- 🧠 **Intelligent Server Routing**: Automatic tool selection
- 🌐 **MCP Registry Integration**: Access to ecosystem of tools
- 🔒 **Enhanced Security**: Sandboxed execution environments
- 📊 **Performance Analytics**: Usage tracking and optimization

### **Future Applications**
- **🏠 Smart Home Integration**: Voice-controlled IoT devices
- **💼 Enterprise Automation**: Business process automation
- **🎓 Educational Tools**: Interactive learning assistants
- **🔬 Research Platform**: Scientific computation and analysis
- **🎨 Creative Workflows**: Content creation and design

---

## 🏆 Why This Matters

JARVIS represents a **paradigm shift** in AI assistant technology:

- **🎯 True Intelligence**: Not just command execution, but dynamic capability discovery
- **🔧 Self-Extending**: Grows its own capabilities based on user needs
- **🛡️ Privacy-First**: Local processing ensures data never leaves your device
- **🌱 Open Ecosystem**: Community-driven tool development and sharing

This is the future of human-computer interaction - **AI that truly understands and adapts**.

---
