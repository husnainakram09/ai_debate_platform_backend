import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    MONGODB_URI = os.environ.get('MONGODB_URI')
    HUGGINGFACE_API_TOKEN = os.environ.get('HUGGINGFACE_API_TOKEN')
    
    # AI Model Configuration
    DEFAULT_MODEL = "microsoft/DialoGPT-medium"
    BACKUP_MODEL = "gpt2"
    FALLBACK_MODEL = "distilgpt2"
    
    # Debate Configuration
    MAX_DEBATE_ROUNDS = 3
    MAX_ARGUMENT_LENGTH = 500
    DEBATE_TIMEOUT = 300  # 5 minutes
    
    # API Configuration
    API_RATE_LIMIT = "100 per hour"
    
    # Database Configuration
    DB_CONNECTION_TIMEOUT = 30000  # 30 seconds