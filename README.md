# Project-JARVIS

**AI-Native CLI (PROTOTYPE)**

Current functionality:

- Conversation with the user
- Implementing codes in Terminal
- Reporting back the outputs from the Terminal

**Installation:**

1. Clone the llm_LLaVA branch
2. In the root of the project create folders: **models/piper**
3. Download a Piper model from: https://rhasspy.github.io/piper-samples/. Get both the .onnx and .onnx.json files and put them in the models/piper folder (The model I used: https://rhasspy.github.io/piper-samples/#en_US-libritts_r-medium)
4. If you don't have the virtual environment, create it: **python -m venv venv**
5. Run **pip install -r requirements.txt**
6. Run **ollama pull codegemma:7b-instruct-q5_K_M** (or any of your preferred models from https://ollama.com/search)
7. Create .env file in /jarvis folder and populate it as it is shown in .env.example file in the same folder.
8. Run main.py

**System requirements:**

---- To be filled out

**How it works:**

---- To be filled out

**Required Improvements:**

1. Response time < 5s (Not considering the Terminal I/O)
2. Response quality - fine tuning
   - Remove repetitions
   - Improve quality of Command/Conversation identification
   - Look for code tailored AI models (Optional, since codegemma is mostly code tailored)
3. Cross platform:
   - Windows (Supported)
   - Linux (Supported)
   - MacOS (Tests needed)
   - Raspberry PI (Not supported)
4. Scripting
   - Scripted installation
   - Docker for crossplatform scripting

**Next project step:**

OS implementation
