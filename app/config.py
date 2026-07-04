# config.py

import importlib.util
import os

if importlib.util.find_spec("dotenv") is not None:
    from dotenv import load_dotenv
else:
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

# Change line 14 to map cleanly to the default Google API variable
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")