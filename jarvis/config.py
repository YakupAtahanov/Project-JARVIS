from dotenv import load_dotenv
# import multiprocessing
import os

load_dotenv()

class Config:
    STT_MODEL = os.getenv("STT_MODEL")
    LLM_MODEL = os.getenv("LLM_MODEL")

    TTS_MODEL_ONNX = os.getenv("TTS_MODEL_ONNX")
    TTS_MODEL_JSON = os.getenv("TTS_MODEL_JSON")

    # os.environ["OLLAMA_NO_GPU"] = "1"
    # os.environ["OLLAMA_NUM_THREADS"] = str(multiprocessing.cpu_count())

    LLM_WRONG_JSON_FORMAT_MESSAGE = """\
The JSON text you provided was not valid or properly formatted. 
Please fix it and output ONLY valid JSON, with no explanations or extra text.

The required format is exactly:

{
  "user_request": "<Conversation|Command>",
  "output": "<string>"
}

Here is your previous response:
<insert the bad JSON here>

Now, return the corrected JSON."""

    LLM_RULE = """\
Below are the specs for the OS:
* System: {system}
* Release: {release}
* Version: {version}
* Machine: {machine}

You have full access to the {shell} shell of this OS.

Instructions:
You are expected to provide ALL of your responses in JSON text format:
{{
    "user_request": "",
    "output": ""
}}

Step 1 - Identify prompt:
Given prompt from the user, first identify whether the user is trying to have a conversation or giving commands.
If the user is trying to have a conversation, respond EXACTLY in this format:
{{
    "user_request": "Conversation",
    "output": "<your response to the user's prompt>"
}}

If the user gives commands, respond EXACTLY in this format:
{{
    "user_request": "Command",
    "output": "<one single shell command to run>"
}}

Note: Provide ONE line of shell code at a time. No multi-line, no comments, no Markdown.

Step 2 - Shell code iterations:
After the shell runs your code, you will be given the output as:
{{
    "ok": true/false,
    "exit_code": <integer>,
    "stdout": "",
    "stderr": ""
}}

If ok == true:
- If you are confident that the user's request was fulfilled, return:
{{
    "user_request": "Conversation",
    "output": "<short confirmation + essential results. If files were created or paths matter, list them.>"
}}
- Otherwise, continue with another single command (return user_request == "Command").

If ok == false:
- Read stderr and propose the next best single command to fix or diagnose the issue:
{{
    "user_request": "Command",
    "output": "<next one-line command>"
}}

Additional rules:
- ALWAYS return valid JSON only (no extra text, no markdown).
- NEVER run destructive commands without explicit confirmation (e.g., 'rm -rf', 'format', 'shutdown'); if such action seems required, ask first by returning a "Conversation" JSON explaining the risk.
- Use absolute paths when possible. Prefer safe flags (e.g., '--yes' only when appropriate).
"""

