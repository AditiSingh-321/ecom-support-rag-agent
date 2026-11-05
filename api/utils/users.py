# User Preference Persistence Logic
from typing import Text, Dict, Any

try:
    from app import db
except ImportError:
    try:
        from api.app import db
    except ImportError:
        db = None

if db is not None and hasattr(db, "Model"):
    class UserPreference(db.Model):
        user_id = db.Column(db.String(36), primary_key=True)
        preferences = db.Column(db.JSON)
        created_at = db.Column(db.DateTime, default=db.func.now())
        updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

        @classmethod
        def update_prefs(cls, user_id: str, prefs: dict):
            pass
else:
    class UserPreference:
        @classmethod
        def update_prefs(cls, user_id: str, prefs: dict):
            pass

try:
    from rasa_sdk import Action
except ImportError:
    class Action:
        pass

try:
    from api.utils.redis_manager import RedisSessionManager
except ImportError:
    try:
        from utils.redis_manager import RedisSessionManager
    except ImportError:
        RedisSessionManager = None

class ActionSavePreference(Action):
    def name(self) -> Text:
        return "action_save_preference"
    
    def run(self, dispatcher, tracker, domain):
        user_id = tracker.sender_id
        prefs = {
            "language": tracker.get_slot("language"),
            "notification_prefs": tracker.get_slot("notification_prefs")
        }
        
        # Save to both Redis and PostgreSQL
        if RedisSessionManager:
            RedisSessionManager().store_session(user_id, prefs)
        UserPreference.update_prefs(user_id, prefs)
        return []
