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
