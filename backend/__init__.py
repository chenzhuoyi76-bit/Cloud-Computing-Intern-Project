from flask import Flask

from backend.routes.dispatch import dispatch_bp
from backend.routes.llm import llm_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("backend.config.Config")
    app.json.ensure_ascii = False
    app.register_blueprint(llm_bp)
    app.register_blueprint(dispatch_bp)

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app
