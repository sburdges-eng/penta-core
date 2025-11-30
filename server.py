"""Simple HTTP server for penta-core."""

import logging
import os
import signal
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_port():
    """Get port from environment variable with validation."""
    port_str = os.environ.get("PORT", "8000")
    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return port
    except ValueError:
        logger.error("Invalid PORT value: %s. Using default 8000.", port_str)
        return 8000


PORT = get_port()
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

    def shutdown_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Shutting down server...")
        httpd.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("Server running on http://%s:%d", HOST, PORT)
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
