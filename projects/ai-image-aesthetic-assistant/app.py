import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core.analyzer import analyze_image_bytes

ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        path_map = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "application/javascript; charset=utf-8"),
        }
        if self.path not in path_map:
            self.send_error(404)
            return
        filename, content_type = path_map[self.path]
        content = (STATIC_DIR / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if self.path != "/api/analyze":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        filename = self.headers.get("X-Filename", "upload.jpg")
        image_bytes = self.rfile.read(length)
        payload = analyze_image_bytes(image_bytes, filename)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)


def build_server(address=("127.0.0.1", 8000)):
    return ThreadingHTTPServer(address, AppHandler)


if __name__ == "__main__":
    server = build_server()
    try:
        print("Serving on http://127.0.0.1:8000")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
