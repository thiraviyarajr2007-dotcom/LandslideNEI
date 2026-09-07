"""
Lightweight port 80 redirector to 8000
Allows users typing http://127.0.0.1 or http://localhost without :8000 to reach the app.
"""
import http.server
import socketserver
import sys

PORT = 80

class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        target = f"http://127.0.0.1:8000{self.path}"
        self.send_response(307)
        self.send_header('Location', target)
        self.end_headers()

    def do_HEAD(self):
        target = f"http://127.0.0.1:8000{self.path}"
        self.send_response(307)
        self.send_header('Location', target)
        self.end_headers()

    def do_POST(self):
        target = f"http://127.0.0.1:8000{self.path}"
        self.send_response(307)
        self.send_header('Location', target)
        self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), RedirectHandler) as httpd:
            print(f"Port 80 redirector active -> http://127.0.0.1:8000", flush=True)
            httpd.serve_forever()
    except Exception as e:
        print(f"Could not bind port 80: {e}", file=sys.stderr, flush=True)
