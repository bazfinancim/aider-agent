import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class AiderHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Aider Agent — Master Baz — Ready")

    def do_POST(self):
        try:
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            task = body.get("task", "")

            result = subprocess.run(
                ["aider", "--model", "gemini/gemini-2.0-flash",
                 "--message", task, "--yes", "--no-git"],
                capture_output=True, text=True, cwd="/tmp", timeout=300
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "done",
                "output": result.stdout[-2000:]
            }).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Aider Agent running on port {port}")
    server = HTTPServer(("0.0.0.0", port), AiderHandler)
    server.serve_forever()
