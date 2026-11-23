"""Router HTTP con selección declarativa del backend (demostración GitOps).

Solo expuesto en 127.0.0.1 por Compose. El archivo de estado se monta read-only
en el contenedor y cambia al promover/rollback, sin reiniciar el proxy.
"""
from __future__ import annotations
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from pathlib import Path
import json,os,time

STATE=Path(os.getenv("GITOPS_STATE","/state/desired-state.json"))
ALLOWED={"/health","/model/info","/machines","/predict","/metrics","/history"}
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,code,body,slot="none",extra=None):
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("X-Serving-Slot",slot)
        self.send_header("Cache-Control","no-store")
        if extra:
            self.send_header("X-Backend-Trace-Id",extra)
        self.send_header("Content-Length",str(len(body)))
        self.end_headers();self.wfile.write(body)
    def handle_route(self):
        path=self.path.split("?")[0]
        if path not in ALLOWED:
            self.respond(404,b'{"detail":"route not allowed"}')
            return
        try:
            state=json.loads(STATE.read_text(encoding="utf-8"))
            slot=state["active_slot"]
            if slot not in ("stable","candidate"):raise ValueError("Invalid slot")
            target=state["routes"][slot]+path
        except (OSError,ValueError,KeyError) as ex:
            self.respond(503,b'{"detail":"desired state invalid"}')
            return
        if path=="/health":
            result={"status":"ok","active_slot":slot,
                    "desired_model_sha256":state["model_sha256"],
                    "routing":"gitops_academic_staging"}
            self.respond(200,json.dumps(result).encode(),slot);return
        payload=None
        if self.command=="POST":
            n=int(self.headers.get("Content-Length","0"))
            if n>100_000:
                self.respond(413,b'{"detail":"payload too large"}',slot);return
            payload=self.rfile.read(n)
        request=Request(target,data=payload,method=self.command,
          headers={"Content-Type":"application/json"})
        try:
            with urlopen(request,timeout=8) as backend:
                content=backend.read()
                code=backend.status
                trace=backend.headers.get("X-Trace-Id")
        except HTTPError as e:
            code=e.code;content=e.read();trace=None
        except (URLError,TimeoutError,OSError):
            self.respond(502,b'{"detail":"active backend unavailable"}',slot);return
        self.respond(code,content,slot,trace)
    def do_GET(self):self.handle_route()
    def do_POST(self):self.handle_route()
if __name__=="__main__":
    ThreadingHTTPServer(("0.0.0.0",8010),Handler).serve_forever()
