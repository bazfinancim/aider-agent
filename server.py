import os, json, subprocess, urllib.request, urllib.error, base64
from http.server import HTTPServer, BaseHTTPRequestHandler

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")
GH_PAT     = os.environ.get("GITHUB_PAT", "")

print(f"CodeX Dev Agent v4.2 — GEMINI={'SET' if GEMINI_KEY else 'MISSING'}, GROQ={'SET' if GROQ_KEY else 'MISSING'}, GH={'SET' if GH_PAT else 'MISSING'}")

def call_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    body = json.dumps({"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"max_tokens":4000}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json","Authorization":f"Bearer {GROQ_KEY}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]

def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    body = json.dumps({"contents":[{"parts":[{"text":prompt}]}]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]

def ask(prompt, engine="groq"):
    try:
        if engine == "groq":
            return call_groq(prompt)
        else:
            return call_gemini(prompt)
    except Exception as e1:
        # fallback
        try:
            if engine == "groq":
                return call_gemini(prompt)
            else:
                return call_groq(prompt)
        except Exception as e2:
            raise Exception(f"Both engines failed: {e1} | {e2}")

def github_push(repo, filename, content, message="Update by CodeX"):
    url = f"https://api.github.com/repos/bazfinancim/{repo}/contents/{filename}"
    get_req = urllib.request.Request(url, headers={"Authorization":f"token {GH_PAT}","User-Agent":"CodeX"})
    sha = ""
    try:
        with urllib.request.urlopen(get_req, timeout=10) as r:
            sha = json.loads(r.read()).get("sha","")
    except: pass
    encoded = base64.b64encode(content.encode()).decode()
    payload = {"message":message,"content":encoded}
    if sha: payload["sha"] = sha
    put_req = urllib.request.Request(url,
        data=json.dumps(payload).encode(),
        headers={"Authorization":f"token {GH_PAT}","Content-Type":"application/json","User-Agent":"CodeX"},
        method="PUT")
    with urllib.request.urlopen(put_req, timeout=15) as r:
        return json.loads(r.read())

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status":"ready","name":"CodeX Dev Agent — Master Baz","version":"4.2",
            "engines":["llama-3.3-70b (Groq)","gemini-2.0-flash"],
            "actions":["generate","execute","push","full","chat"],
            "env":{"gemini":"SET" if GEMINI_KEY else "MISSING","groq":"SET" if GROQ_KEY else "MISSING","github":"SET" if GH_PAT else "MISSING"}
        }).encode())

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length",0))
            body = json.loads(self.rfile.read(n)) if n else {}
            task     = body.get("task","")
            action   = body.get("action","chat")
            lang     = body.get("language","python")
            repo     = body.get("repo","")
            filename = body.get("filename","output.py")
            engine   = body.get("engine","groq")
            result   = {}

            if action == "generate":
                code = ask(f"Generate {lang} code ONLY (no explanation, no markdown blocks):\n{task}", engine)
                result = {"code": code}
            elif action == "execute":
                code = body.get("code","")
                path = f"/tmp/run.py"
                open(path,"w").write(code)
                r = subprocess.run(["python3",path],capture_output=True,text=True,timeout=30)
                result = {"output":r.stdout,"error":r.stderr}
            elif action == "push":
                code = body.get("code","")
                pushed = github_push(repo, filename, code, f"CodeX: {task[:50]}")
                result = {"pushed":True,"url":pushed.get("content",{}).get("html_url","")}
            elif action == "full":
                code = ask(f"Generate {lang} code ONLY (no markdown) for:\n{task}", engine)
                pushed_url = ""
                if repo:
                    pushed = github_push(repo, filename, code, f"CodeX: {task[:50]}")
                    pushed_url = pushed.get("content",{}).get("html_url","")
                result = {"code":code,"github":pushed_url}
            elif action == "chat":
                result = {"response": ask(task, engine)}
            else:
                result = {"error":f"Unknown action: {action}"}

            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result,ensure_ascii=False).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error":str(e)}).encode())

if __name__=="__main__":
    port = int(os.environ.get("PORT",10000))
    print(f"CodeX Dev Agent v4.2 — port {port}")
    HTTPServer(("0.0.0.0",port),Handler).serve_forever()
