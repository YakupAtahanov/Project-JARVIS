from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    STT_MODEL = os.getenv("STT_MODEL")