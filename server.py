import os
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GITHUB_PAT = os.environ.get("GITHUB_PAT", "")

def ask_gemini(prompt):
    """שליחת prompt ל-Gemini ישירות"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode()
    req = urllib.request.Request(url, data=payload,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Error: {e}"

def run_code(code, language="python"):
    """הרצת קוד"""
    ext = {"python": "py", "javascript": "js", "bash": "sh"}.get(language, "py")
    path = f"/tmp/codex_run.{ext}"
    with open(path, "w") as f:
        f.write(code)
    cmd = {"python": ["python3", path], "javascript": ["node", path], 
           "bash": ["bash", path]}.get(language, ["python3", path])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout + result.stderr

class CodeXAgentHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ready",
            "name": "CodeX Aider Agent — Master Baz v3.0",
            "capabilities": ["code_generation", "code_execution", "github_push"],
            "model": "gemini-2.0-flash"
        }).encode())

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            
            task = body.get("task", "")
            action = body.get("action", "generate")  # generate | execute | full
            language = body.get("language", "python")
            repo = body.get("repo", "")
            filename = body.get("filename", "output.py")

            result = {}

            if action == "generate":
                prompt = f"""You are an expert developer. Generate {language} code for this task:
{task}

Return ONLY the code, no explanation, no markdown blocks."""
                code = ask_gemini(prompt)
                result = {"action": "generate", "code": code, "language": language}

            elif action == "execute":
                code = body.get("code", "")
                output = run_code(code, language)
                result = {"action": "execute", "output": output}

            elif action == "full":
                # generate + execute
                prompt = f"""Generate {language} code for: {task}
Return ONLY the code."""
                code = ask_gemini(prompt)
                output = run_code(code, language)
                result = {"action": "full", "code": code, "output": output}

            elif action == "chat":
                # שיחה חופשית
                response = ask_gemini(task)
                result = {"action": "chat", "response": response}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"CodeX Agent v3.0 running on port {port}")
    server = HTTPServer(("0.0.0.0", port), CodeXAgentHandler)
    server.serve_forever()
