import os, json, subprocess, urllib.request, urllib.error, base64
from http.server import HTTPServer, BaseHTTPRequestHandler

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
CLAUDE_KEY     = os.environ.get("CLAUDE_API_KEY", "")
GH_PAT         = os.environ.get("GITHUB_PAT", "")
GEMINI_KEY     = os.environ.get("GEMINI_API_KEY", "")

print(f"v4.3 — OR={'SET' if OPENROUTER_KEY else 'MISSING'}, CLAUDE={'SET' if CLAUDE_KEY else 'MISSING'}, GH={'SET' if GH_PAT else 'MISSING'}")

def call_openrouter(prompt, model="meta-llama/llama-3.3-70b-instruct:free"):
    url = "https://openrouter.ai/api/v1/chat/completions"
    body = json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":4000}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type":"application/json",
        "Authorization":f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer":"https://baz-f.co.il",
        "X-Title":"MASTER BAZ"
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]

def call_claude(prompt):
    key = os.environ.get("CLAUDE_API_KEY", CLAUDE_KEY)
    url = "https://api.anthropic.com/v1/messages"
    body = json.dumps({"model":os.environ.get("CLAUDE_MODEL","claude-haiku-4-5"),"max_tokens":2000,"messages":[{"role":"user","content":prompt}]}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type":"application/json",
        "x-api-key":key,
        "anthropic-version":"2023-06-01"
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["content"][0]["text"]

def ask(prompt, engine="openrouter"):
    engines = [call_openrouter, call_claude] if engine != "claude" else [call_claude, call_openrouter]
    last_err = None
    for fn in engines:
        try:
            return fn(prompt)
        except Exception as e:
            last_err = e
            continue
    raise Exception(f"All engines failed: {last_err}")

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
        self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
        self.wfile.write(json.dumps({"status":"ready","name":"CodeX Dev Agent","version":"4.3",
            "engines":["openrouter/llama-3.3-70b","claude-3-5-haiku"],
            "env":{"openrouter":"SET" if OPENROUTER_KEY else "MISSING","claude":"SET" if CLAUDE_KEY else "MISSING","github":"SET" if GH_PAT else "MISSING"}
        }).encode())

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length",0))
            body = json.loads(self.rfile.read(n)) if n else {}
            task=body.get("task",""); action=body.get("action","chat")
            lang=body.get("language","python"); repo=body.get("repo","")
            filename=body.get("filename","output.py"); engine=body.get("engine","openrouter")
            result={}

            if action=="generate":
                result={"code": ask(f"Generate {lang} code ONLY (no explanation, no markdown):\n{task}", engine)}
            elif action=="execute":
                code=body.get("code",""); open("/tmp/run.py","w").write(code)
                r=subprocess.run(["python3","/tmp/run.py"],capture_output=True,text=True,timeout=30)
                result={"output":r.stdout,"error":r.stderr}
            elif action=="push":
                pushed=github_push(repo,filename,body.get("code",""),f"CodeX: {task[:50]}")
                result={"pushed":True,"url":pushed.get("content",{}).get("html_url","")}
            elif action=="full":
                code=ask(f"Generate {lang} code ONLY:\n{task}", engine)
                pushed_url=""
                if repo:
                    pushed=github_push(repo,filename,code,f"CodeX: {task[:50]}")
                    pushed_url=pushed.get("content",{}).get("html_url","")
                result={"code":code,"github":pushed_url}
            elif action=="chat":
                result={"response": ask(task, engine)}
            else:
                result={"error":f"Unknown: {action}"}

            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps(result,ensure_ascii=False).encode())
        except Exception as e:
            self.send_response(500); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps({"error":str(e)}).encode())

if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    print(f"CodeX Dev Agent v4.3 — port {port}")
    HTTPServer(("0.0.0.0",port),Handler).serve_forever()
