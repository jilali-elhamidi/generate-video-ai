from flask import Flask, request, jsonify
from video_generator import generate_video
import traceback

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    script = data.get("script", "")
    title = data.get("title", "Expliacation")
    explanations = data.get("explanations", [])
    # If the client didn't specify, default to True when explanations are provided
    show_explanations_text = data.get("explanationsShowText")
    if show_explanations_text is None:
        show_explanations_text = bool(explanations)
    style = data.get("style", {})
    explanations_display = data.get("explanationsDisplay", None)
    if not script:
        return jsonify({"error": "script field is required"}), 400
    try:
        try:
            output_path = generate_video(
                script,
                title=title,
                explanations=explanations,
                show_explanations_text=show_explanations_text,
                style=style,
                explanations_display=explanations_display,
            )
        except TypeError as te:
            # Backward compatibility: older signature without explanations_display
            print("[WARN] generate_video doesn't accept 'explanations_display'. Retrying without it...", flush=True)
            output_path = generate_video(
                script,
                title=title,
                explanations=explanations,
                show_explanations_text=show_explanations_text,
                style=style,
            )
        return jsonify({"videoUrl": output_path, "message": "Video generated successfully"})
    except Exception as e:
        # Print full traceback to console for debugging
        print(traceback.format_exc(), flush=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Port 5000 par défaut
    app.run(host="0.0.0.0", port=8000, debug=True)
