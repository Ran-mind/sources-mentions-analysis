#!/usr/bin/env python3
"""
Simple HTTP server for Source Mention Research with API proxy
Run this script and open http://localhost:8001 in your browser
"""

import http.server
import socketserver
import os
import urllib.request
import json
import mimetypes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PORT = 8001  # Different port to avoid conflict with Backoffice
API_BASE_URL = 'https://chat-rank-api.amionai.com/tables'
API_KEY = os.getenv('API_KEY', '')

if not API_KEY:
    raise ValueError("API_KEY not found in environment variables. Please create a .env file with API_KEY=your_key")

class MyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, x-api-key')
        super().end_headers()
    
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        path_without_query = self.path.split('?')[0]
        
        if path_without_query == '/':
            path_without_query = '/index.html'
        
        try:
            file_path = os.path.join(os.getcwd(), path_without_query.lstrip('/'))
            if os.path.isdir(file_path):
                file_path = os.path.join(file_path, 'index.html')
            
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                self.send_error(404, "File not found")
                return
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

    def do_POST(self):
        if self.path.startswith('/api/'):
            self.handle_api_proxy()
        else:
            self.send_response(405)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Method not allowed')

    def handle_api_proxy(self):
        """Proxy POST requests to the actual API"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            
            api_endpoint = self.path.replace('/api', '')
            if not api_endpoint.startswith('/'):
                api_endpoint = '/' + api_endpoint
            if not api_endpoint.endswith('/'):
                api_endpoint = api_endpoint + '/'
            
            api_url = f"{API_BASE_URL}{api_endpoint}"
            
            req = urllib.request.Request(api_url, data=body, method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('x-api-key', API_KEY)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read()
                response_code = response.getcode()
                
                self.send_response(response_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(response_data)
                
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read()
            except:
                error_body = json.dumps({'error': f'HTTP {e.code}: {e.reason}'}).encode()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error_body)
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Proxy error: {error_msg}")
            print(traceback.format_exc())
            error_response = json.dumps({'error': error_msg}).encode()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error_response)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"🔬 Source Mention Research Server")
        print(f"   Open http://localhost:{PORT}/ in your browser")
        print(f"   API proxy at http://localhost:{PORT}/api/")
        print("   Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
