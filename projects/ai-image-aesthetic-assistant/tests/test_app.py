import io
import json
import unittest
from threading import Thread
from urllib import request

from PIL import Image

from app import build_server


class AppTests(unittest.TestCase):
    def test_analyze_endpoint_returns_scores(self):
        server = build_server(("127.0.0.1", 8765))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            image = Image.new("RGB", (32, 32), "white")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            req = request.Request(
                "http://127.0.0.1:8765/api/analyze",
                data=buffer.getvalue(),
                method="POST",
                headers={"Content-Type": "image/jpeg", "X-Filename": "sample.jpg"},
            )
            with request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            self.assertIn("scores", payload)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
