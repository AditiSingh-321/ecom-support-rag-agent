import os
from dotenv import load_dotenv
import redis
from datetime import timedelta

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    PORT = int(os.getenv("PORT", 5000))
    
    # PostgreSQL Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', '')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'ecommerce_dev')}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_pre_ping": True
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis Configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    
    # External APIs
    FAKESTORE_API_BASE = os.getenv(
        "FAKESTORE_API_BASE",
        "https://fakestoreapi.com"
    )
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_API_BASE = os.getenv(
        "DEEPSEEK_API_BASE", 
        "https://api.deepseek.com/v1"
    )
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    
    # Rasa Configuration
    RASA_ACTIONS_URL = os.getenv(
        "RASA_ACTIONS_URL", 
        "http://localhost:5055/webhook"
    )
    
    # Email Configuration
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    
    # JWT Security
    JWT_ACCESS_TOKEN_EXPIRES = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400)  # 24h
    )
    PROPAGATE_EXCEPTIONS = True

class RedisSessionManager:
    """Session manager with in-memory fallback if Redis is unavailable."""
    def __init__(self):
        self._memory_store = {}
        self.redis = None
        try:
            r = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=1
            )
            r.ping()
            self.redis = r
        except Exception:
            self.redis = None

    def store_session(self, session_id: str, data: dict):
        if self.redis:
            try:
                self.redis.hset(session_id, mapping=data)
                self.redis.expire(session_id, timedelta(days=1))
                return
            except Exception:
                pass
        self._memory_store[session_id] = data

    def get_session(self, session_id: str) -> dict:
        if self.redis:
            try:
                return self.redis.hgetall(session_id)
            except Exception:
                pass
        return self._memory_store.get(session_id, {})

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///ecommerce_dev.db")

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///ecommerce_test.db"

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:pass@cloud-postgres.example.com:5432/prod_db"
    )

config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
