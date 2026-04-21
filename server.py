import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

MODELS = {
    "gemini": "gemini/gemini-2.0-flash",
    "claude": "anthropic/claude-3-5-sonnet-20241022",
    "gpt4": "openai/gpt-4o",
    "groq": "groq/llama-3.3-70b-versatile",
    "default": "gemini/gemini-2.0-flash"
}

class AiderHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ready",
            "name": "Aider Agent — Master Baz",
            "models": list(MODELS.keys()),
            "version": "2.0"
        }).encode())

    def do_POST(self):
        try:
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            task = body.get("task", "")
            model_key = body.get("model", "default")
            repo_url = body.get("repo", "")
            model = MODELS.get(model_key, MODELS["default"])

            env = os.environ.copy()

            # הגדרת env vars לפי מודל
            gemini_key = env.get("GEMINI_API_KEY", "")
            anthropic_key = env.get("ANTHROPIC_API_KEY", "")
            openai_key = env.get("OPENAI_API_KEY", "")
            groq_key = env.get("GROQ_API_KEY", "")

            work_dir = "/tmp/aider_workspace"
            os.makedirs(work_dir, exist_ok=True)

            # clone repo אם נשלח
            if repo_url:
                subprocess.run(
                    ["git", "clone", repo_url, work_dir],
                    capture_output=True, env=env
                )

            cmd = [
                "aider",
                "--model", model,
                "--message", task,
                "--yes",
                "--no-git" if not repo_url else "",
            ]
            cmd = [c for c in cmd if c]

            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                cwd=work_dir, timeout=300, env=env
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "done",
                "model": model,
                "output": result.stdout[-3000:],
                "error": result.stderr[-500:] if result.stderr else ""
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Aider Agent v2.0 running on port {port}")
    server = HTTPServer(("0.0.0.0", port), AiderHandler)
    server.serve_forever()
