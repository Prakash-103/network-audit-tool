"""
Vercel Serverless Function Entrypoint for FastAPI Application.
"""
import sys
from pathlib import Path

# Add project root directory to Python path so modules are found in serverless environment
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app
