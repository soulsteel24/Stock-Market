import os
from dotenv import load_dotenv
from app.config import get_settings
from app.services.gemini_client import gemini_client

print("--- Environment Verification ---")
load_dotenv()

# Check Environment Variable
env_key = os.getenv("GEMINI_API_KEY")
print(f"GEMINI_API_KEY in os.environ: {'PRESENT' if env_key else 'MISSING'}")
if env_key:
    print(f"Key Length: {len(env_key)}")
    print(f"Key Starts With: {env_key[:2]}...")

# Check Settings
settings = get_settings()
print(f"Settings gemini_api_key: {'PRESENT' if settings.gemini_api_key else 'MISSING'}")

# Check Client
print(f"Gemini Client Connected: {gemini_client.is_connected()}")

# Check Transformers
print("\n--- Dependency Verification ---")
try:
    import transformers
    import torch
    import darts
    print("Transformers version:", transformers.__version__)
    print("Torch version:", torch.__version__)
    print("Darts version:", darts.__version__)
except ImportError as e:
    print(f"Import Error: {e}")

print("\n--- Done ---")
