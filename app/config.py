# config.py

import importlib.util
import os

if importlib.util.find_spec("dotenv") is not None:
    from dotenv import load_dotenv
else:
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")