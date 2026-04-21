import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class AiderHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(length))
        task = body.get('task', '')
        repo = body.get('repo', '')
        
        cmd = [
            'aider',
            '--model', 'gemini/gemini-2.0-flash',
            '--message', task,
            '--yes',
            '--no-git'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/tmp')
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'done',
            'output': result.stdout
        }).encode())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), AiderHandler)
    print(f'Aider Agent running on port {port}')
    server.serve_forever()
