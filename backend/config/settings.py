import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-dmrv-key")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    # Mesh Network Configuration
    ESP32_IP = os.getenv("ESP32_IP", "192.168.4.1")
    ESP32_PORT = int(os.getenv("ESP32_PORT", 1234))

    # ChromaDB Configuration
    CHROMA_DB_DIR = os.path.join(os.getcwd(), "db", "chroma_data")