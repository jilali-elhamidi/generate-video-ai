from flask import Flask, request, jsonify
from video_generator import generate_video
import traceback

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    script = data.get("script", "")
    title = data.get("title", "Explication")
    if not script:
        return jsonify({"error": "script field is required"}), 400
    try:
        output_path = generate_video(script, title=title)
        return jsonify({"videoUrl": output_path, "message": "Video generated successfully"})
    except Exception as e:
        # Print full traceback to console for debugging
        print(traceback.format_exc(), flush=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Port 5000 par défaut
    app.run(host="0.0.0.0", port=8000, debug=True)
