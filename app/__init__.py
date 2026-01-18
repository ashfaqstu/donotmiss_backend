from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)

    # Basic config
    app.config.setdefault("DONOTMISS_ENV", "development")

    # Enable CORS for all routes (for Chrome extension on localhost during dev)
    CORS(app, resources={r"/*": {"origins": "*"}})

    from .routes import bp as api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
