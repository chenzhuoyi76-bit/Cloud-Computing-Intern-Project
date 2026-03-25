from flask import Blueprint, current_app, jsonify, request

from backend.services.openai_service import IntentRecognitionError, recognize_intent
from backend.services.task_dispatcher import dispatch_task

dispatch_bp = Blueprint("dispatch", __name__, url_prefix="/api/llm")


@dispatch_bp.post("/dispatch")
def dispatch_from_user_input():
    payload = request.get_json(silent=True) or {}
    user_input = (payload.get("user_input") or "").strip()
    context = payload.get("context") or {}

    if not user_input:
        return jsonify({"error": "user_input is required"}), 400

    api_key = current_app.config.get("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY is not configured"}), 500

    try:
        intent_result = recognize_intent(
            user_input=user_input,
            api_key=api_key,
            model=current_app.config["OPENAI_MODEL"],
            base_url=current_app.config["OPENAI_BASE_URL"],
            timeout=current_app.config["OPENAI_TIMEOUT"],
        )
    except IntentRecognitionError as exc:
        return jsonify({"error": str(exc)}), 502

    dispatch_result = dispatch_task(intent_result=intent_result, context=context)
    return jsonify({"intent_result": intent_result, "dispatch_result": dispatch_result})
