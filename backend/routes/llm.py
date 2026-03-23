from flask import Blueprint, current_app, jsonify, request

from backend.services.openai_service import IntentRecognitionError, recognize_intent

llm_bp = Blueprint("llm", __name__, url_prefix="/api/llm")


@llm_bp.post("/intent")
def detect_intent():
    payload = request.get_json(silent=True) or {}
    user_input = (payload.get("user_input") or "").strip()

    if not user_input:
        return jsonify({"error": "user_input is required"}), 400

    api_key = current_app.config.get("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY is not configured"}), 500

    try:
        result = recognize_intent(
            user_input=user_input,
            api_key=api_key,
            model=current_app.config["OPENAI_MODEL"],
            base_url=current_app.config["OPENAI_BASE_URL"],
            timeout=current_app.config["OPENAI_TIMEOUT"],
        )
    except IntentRecognitionError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(result)
