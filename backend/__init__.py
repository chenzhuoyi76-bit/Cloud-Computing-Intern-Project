from flask import Flask

from backend.db import init_database
from backend.models.task_record import TaskExecutionRecord  # noqa: F401
from backend.routes.dispatch import dispatch_bp
from backend.routes.llm import llm_bp
from backend.routes.tasks import tasks_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("backend.config.Config")
    app.json.ensure_ascii = False
    init_database(app.config["DATABASE_URL"])
    app.register_blueprint(llm_bp)
    app.register_blueprint(dispatch_bp)
    app.register_blueprint(tasks_bp)

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app
