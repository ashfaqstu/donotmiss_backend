from flask import Flask
from flask_cors import CORS
import os


def create_app():
    app = Flask(__name__)

    # Basic config
    app.config.setdefault("DONOTMISS_ENV", "development")
    
    # Database configuration
    # Use DATABASE_URL from environment (Render provides this for PostgreSQL)
    database_url = os.environ.get("DATABASE_URL", "sqlite:///donotmiss.db")
    
    # Fix for Render's postgres:// vs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Enable CORS for all routes (for Chrome extension)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Initialize database
    from .models import db
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        db.create_all()

    from .routes import bp as api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
