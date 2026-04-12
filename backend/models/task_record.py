from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


class TaskExecutionRecord(Base):
    __tablename__ = "task_execution_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intent: Mapped[str] = mapped_column(String(100), nullable=False)
    repo_url: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    repository_json: Mapped[str] = mapped_column(Text, nullable=False)
    task_request_json: Mapped[str] = mapped_column(Text, nullable=False)
    install_result_json: Mapped[str] = mapped_column(Text, nullable=False, default="null")
    test_result_json: Mapped[str] = mapped_column(Text, nullable=False, default="null")
    deploy_result_json: Mapped[str] = mapped_column(Text, nullable=False, default="null")
    dispatch_result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
