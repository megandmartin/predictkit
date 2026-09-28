"""Loopback-only Studio; authenticated APIs; generated code is never executed."""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from .runtime import SprintEngine
from .providers import RehearsalProvider
from .http_provider import OpenAIResponsesProvider
from .spend import SpendPolicy

ROOT = Path(__file__).resolve().parent.parent


def make_server(port: int = 8765, provider_name: str = "rehearsal", run_root: Path | None = None):
    if provider_name == "openai":
        if not os.getenv("OPENAI_API_KEY") or not os.getenv("PREDICTKIT_MODEL"):
            raise ValueError("Live mode requires OPENAI_API_KEY and PREDICTKIT_MODEL in the server environment")
        provider = OpenAIResponsesProvider(os.environ["PREDICTKIT_MODEL"], SpendPolicy.from_env(os.environ))
    elif provider_name == "rehearsal":
        provider = RehearsalProvider()
    else:
        raise ValueError("Unknown provider")
    engine = SprintEngine(run_root or ROOT / ".local/runs", provider)
    token = secrets.token_urlsafe(32)
    source_download_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def allowed_host(self):
            return len(self.headers.get_all("Host", [])) == 1 and self.headers.get("Host") in {
                f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def authorized_api(self):
            if not self.allowed_host() or len(self.headers.get_all("X-PredictKit-Token", [])) != 1:
                return False
            if not secrets.compare_digest(self.headers.get("X-PredictKit-Token", ""), token):
                return False
            origin = self.headers.get("Origin")
            if len(self.headers.get_all("Origin", [])) > 1 or (origin and origin != "http://" + self.headers.get("Host")):
                return False
            return self.headers.get("Sec-Fetch-Site", "same-origin") not in ("cross-site", "same-site")

        def send(self, status, body, content_type="application/json", extra=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def page(self, name):
            # The child srcdoc policy blocks subresources, but does not prevent
            # an untrusted script navigating its own frame. The parent frame
            # policy also confines that navigation to this loopback origin.
            return self.send(200, (ROOT / "web" / name).read_text().replace("__SERVER_TOKEN__", token), "text/html; charset=utf-8",
                {"Content-Security-Policy": "frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'"})

        def do_GET(self):
            if not self.allowed_host():
                return self.send(403, {"error": "Loopback host required"})
            url = urlparse(self.path)
            if url.path.startswith("/api/") and not self.authorized_api():
                return self.send(403, {"error": "Invalid local session, host or origin"})
            try:
                if url.path in ("/", "/index.html"):
                    return self.page("landing.html")
                if url.path in ("/studio", "/studio.html"):
                    return self.page("studio.html" if (ROOT / "web/studio.html").exists() else "dashboard.html")
                if url.path == "/skills":
                    return self.page("skills.html")
                if url.path == "/solana-demo":
                    return self.send(200, (ROOT / "solana/demo/index.html").read_bytes(), "text/html; charset=utf-8",
                        {"Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; font-src data:; object-src 'none'; base-uri 'none'; form-action 'none'"})
                if url.path == "/classic":
                    return self.page("dashboard.html")
                static = {"/studio.js": ("studio.js", "text/javascript"), "/studio.css": ("studio.css", "text/css"),
                          "/evidence-modern.js": ("evidence-modern.js", "text/javascript"), "/evidence-modern.css": ("evidence-modern.css", "text/css")}
                for name in ("landing", "skills"):
                    static[f"/{name}.js"] = (f"{name}.js", "text/javascript")
                    static[f"/{name}.css"] = (f"{name}.css", "text/css")
                static["/fonts.css"] = ("fonts.css", "text/css")
                if url.path in static:
                    name, mime = static[url.path]
                    return self.send(200, (ROOT / "web" / name).read_bytes(), mime + "; charset=utf-8")
                fonts = {"/fonts/spacegrotesk-variable.ttf": "spacegrotesk-variable.ttf",
                         "/fonts/inter-variable.ttf": "inter-variable.ttf"}
                if url.path in fonts:
                    return self.send(200, (ROOT / "web/fonts" / fonts[url.path]).read_bytes(), "font/ttf")
                if url.path == "/download/source.zip":
                    with source_download_lock:
                        package = ROOT / ".local/releases/PredictKit-Local-Starter.zip"
                        if any(path.is_symlink() for path in (ROOT / '.local', package.parent, package)):
                            raise ValueError("Source release path must not be symlinked")
                        if not package.is_file():
                            from scripts.package_source import package_source
                            package, _ = package_source(ROOT)
                        data = package.read_bytes()
                    return self.send(200, data, "application/zip", {"Content-Disposition": 'attachment; filename="PredictKit-Local-Starter.zip"'})
                if url.path == "/api/catalog":
                    from .catalog import build_catalog
                    return self.send(200, build_catalog())
                if url.path == "/api/state":
                    return self.send(200, {**engine.snapshot(), "server_provider": provider.name, "version": "0.2.1-local", "spend_policy": provider.policy.view() if hasattr(provider, "policy") else None})
                if url.path == "/api/example":
                    return self.send(200, json.loads((ROOT / "examples/launchlens.json").read_text()))
                if url.path == "/api/artifact":
                    relative = parse_qs(url.query).get("path", [""])[0]
                    return self.send(200, engine.artifact(relative))
                if url.path in ("/api/history", "/api/runs"):
                    return self.send(200, engine.history())
                if url.path == "/api/export":
                    return self.send(200, engine.export(), "application/zip", {"Content-Disposition": 'attachment; filename="predictkit-run-pack.zip"'})
                if url.path in ("/readiness", "/evidence.html"):
                    return self.page("evidence-modern.html" if (ROOT / "web/evidence-modern.html").exists() else "readiness.html")
                if url.path == "/classic-readiness":
                    return self.page("readiness.html")
                if url.path == "/api/readiness":
                    from .readiness import evaluate_run
                    return self.send(200, evaluate_run(engine.snapshot()))
                if url.path == "/health":
                    return self.send(200, {"ok": True, "provider": provider.name})
                return self.send(404, {"error": "Not found"})
            except (ValueError, TypeError, OSError) as exc:
                return self.send(400, {"error": str(exc)[:250]})

        def do_POST(self):
            if not self.authorized_api():
                return self.send(403, {"error": "Invalid local session, host or origin"})
            try:
                if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
                    raise ValueError("One bounded Content-Length is required")
                length = int(self.headers.get("Content-Length", 0))
                if length < 0 or length > 50000:
                    raise ValueError("Request too large")
                data = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(data, dict):
                    raise ValueError("Request body must be a JSON object")
                if self.path == "/api/start":
                    if provider.name != "rehearsal" and data.get("approve_model_spend") is not True:
                        raise ValueError("Explicit approval of paid model calls is required")
                    engine.start(data.get("brief"))
                elif self.path == "/api/approve":
                    engine.approve(data.get("brief_hash", ""), data.get("memo_hash"))
                elif self.path == "/api/pause": engine.pause()
                elif self.path == "/api/resume": engine.resume()
                elif self.path == "/api/stop": engine.stop()
                elif self.path == "/api/select": engine.select(data.get("id"))
                else: return self.send(404, {"error": "Not found"})
                return self.send(200, engine.snapshot())
            except (ValueError, TypeError, OSError) as exc:
                return self.send(400, {"error": str(exc)[:250]})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.engine = engine
    server.session_token = token
    server.daemon_threads = True
    return server
