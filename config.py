"""
AI IT Helpdesk Agent - Configuration Module
Centralizes paths, constants, environment settings, and category definitions.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "helpdesk.db"

# Ensure runtime directories exist
for directory in [KNOWLEDGE_BASE_DIR, VECTORSTORE_DIR, DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env if present
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Gemini AI Settings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-exp"
]

# IT Helpdesk Taxonomy
CATEGORIES = [
    "Network",
    "Hardware",
    "Software",
    "Printer",
    "Account",
    "Security",
    "Other"
]

PRIORITIES = [
    "Low",
    "Medium",
    "High",
    "Critical"
]

STATUSES = [
    "Open",
    "In Progress",
    "Resolved"
]

# Category Badges & Color Accents
CATEGORY_COLORS = {
    "Network": "#2563EB",     # Royal Blue
    "Hardware": "#D97706",    # Amber
    "Software": "#059669",    # Emerald Green
    "Printer": "#7C3AED",     # Purple
    "Account": "#0891B2",     # Cyan
    "Security": "#DC2626",    # Red
    "Other": "#6B7280"        # Gray
}

PRIORITY_COLORS = {
    "Low": "#10B981",         # Green
    "Medium": "#F59E0B",      # Amber
    "High": "#EF4444",        # Orange-Red
    "Critical": "#991B1B"     # Deep Crimson
}

# Pre-defined Suggested Questions for UI
SUGGESTED_QUESTIONS = [
    "My Wi-Fi is connected but internet isn't working",
    "Check my internet connection and IP address",
    "How do I fix a printer that is offline?",
    "How much disk space do I have left?",
    "My application keeps crashing on Windows",
    "I forgot my student portal account password"
]

# RAG configuration
CHUNK_SIZE = 500
CHUNK_OVERLAP = 60
TOP_K_RETRIEVAL = 3
