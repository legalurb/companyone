#!/usr/bin/env python3
"""Servidor local de teste com suporte a Range (para o vídeo poder pular de parte)."""
import http.server, os, re, sys

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_head(self):
        path = self.translate_path(self.path.split('?')[0])
        if os.path.isdir(path):
            path = os.path.join(path, 'index.html')
        if not os.path.isfile(path):
            self.send_error(404); return None
        size = os.path.getsize(path)
        ctype = self.guess_type(path)
        rng = self.headers.get('Range')
        f = open(path, 'rb')
        if rng:
            m = re.match(r'bytes=(\d*)-(\d*)', rng)
            a = int(m.group(1)) if m.group(1) else 0
            b = int(m.group(2)) if m.group(2) else size - 1
            b = min(b, size - 1)
            f.seek(a)
            self.send_response(206)
            self.send_header('Content-Type', ctype)
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Range', f'bytes {a}-{b}/{size}')
            self.send_header('Content-Length', str(b - a + 1))
            self.end_headers()
            self._left = b - a + 1
            return f
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(size))
        self.end_headers()
        self._left = size
        return f
    def copyfile(self, src, out):
        left = getattr(self, '_left', None)
        while left is None or left > 0:
            buf = src.read(65536 if left is None else min(65536, left))
            if not buf: break
            try: out.write(buf)
            except (BrokenPipeError, ConnectionResetError): break
            if left is not None: left -= len(buf)

if __name__ == '__main__':
    root, port = sys.argv[1], int(sys.argv[2])
    os.chdir(root)
    http.server.ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
