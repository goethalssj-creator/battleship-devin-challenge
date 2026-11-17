"""Local dev server that disables browser caching, so changes always show up on reload."""
import http.server, socketserver
class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", 8080), NoCache) as httpd:
    httpd.serve_forever()
