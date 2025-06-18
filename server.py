from http.server import HTTPServer, SimpleHTTPRequestHandler

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        super().end_headers()

if __name__ == "__main__":
    server = HTTPServer(('localhost', 5500), CORSRequestHandler)
    print("Server running at http://localhost:5500")
    server.serve_forever()
