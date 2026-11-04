import sys
import os
from pathlib import Path

# Ensure project root and api directory are on sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
api_dir = Path(__file__).resolve().parent.parent
for p in [str(repo_root), str(api_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from flask import Flask, jsonify
from flask_cors import CORS

try:
    from app.routes import api_blueprint
except ImportError:
    from api.app.routes import api_blueprint

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Health endpoints at root and under blueprint
    @app.route("/health", methods=["GET"])
    def root_health():
        return jsonify({"status": "healthy", "service": "ecommerce-backend"}), 200

    app.register_blueprint(api_blueprint, url_prefix="/api")
    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
