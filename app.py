from flask import Flask, request, render_template_string
import subprocess
import os

app = Flask(__name__)
UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_FILE = os.path.join(UPLOAD_DIR, "prompts.txt")

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Flow Automator</title>
    <style>
        body { font-family: sans-serif; padding: 20px; }
        form { display: flex; flex-direction: column; max-width: 400px; gap: 15px; }
        label { font-weight: bold; }
    </style>
</head>
<body>
    <h1>Flow Image Generator Automator</h1>
    <p>Upload your text file. Ensure your global instructions are at the top, separated by two empty lines from the rest of the prompts.</p>
    <form method="POST" action="/" enctype="multipart/form-data">
        <div>
            <label>Prompts File (.txt)</label><br>
            <input type="file" name="prompts_file" accept=".txt" required>
        </div>
        
        <button type="submit">Start Automation</button>
    </form>
    {% if message %}
        <br>
        <p><strong>{{ message }}</strong></p>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        file = request.files.get("prompts_file")
        
        if file and file.filename != "":
            # Save the uploaded file natively as prompts.txt
            file.save(PROMPTS_FILE)
                
            try:
                # Trigger the main playwright script as a background process
                subprocess.Popen(["python", "main.py"], cwd=UPLOAD_DIR)
                message = "✅ File uploaded and automation started successfully! Check your command prompt/terminal window to watch the live progress."
            except Exception as e:
                message = f"❌ Error starting automation: {e}"
    return render_template_string(HTML, message=message)

if __name__ == "__main__":
    app.run(debug=True, port=8000)
