"""Simple HTTP server for penta-core."""

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Load port from environment variable with default
PORT = int(os.environ.get("PORT", 8000))
HOST = os.environ.get("HOST", "0.0.0.0")


class RequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler for the server."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            super().do_GET()


def run_server():
    """Run the HTTP server."""
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Server running on http://{HOST}:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
