#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import base64

TOKEN = '0123456789abcdef0123456789abcdef'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
HTML = '''<!doctype html>
<html><head><meta charset="utf-8"><title>MarketMint Test</title><style>
:root{--sidebar:250px;--ink:#f7f6ff;--muted:#a7a8bb;--line:#292d40;--purple:#a56cff;--app-card-mural:none}
*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:#080910;color:var(--ink);font-family:Arial,sans-serif}
.shell{min-height:100vh}.sidebar{position:fixed;inset:0 auto 0 0;width:var(--sidebar);padding:24px 16px;background:#0a0b12;display:flex;flex-direction:column;z-index:20}
.brand{padding:12px}.primary-navigation{display:flex;flex-direction:column;gap:8px}.nav-group{overflow:hidden;border:1px solid #292d40;border-radius:14px}.nav-group-button,.nav-button{width:100%;padding:14px;border:0;background:#11131d;color:#f7f6ff;text-align:left;font-size:16px}.nav-submenu{display:grid;gap:4px;padding:4px}.main{margin-left:var(--sidebar);padding:30px}.context-nav-button{padding:12px}.side-status,.sidebar-footer{padding:10px}.view-card{margin-top:20px;padding:24px;border:1px solid #292d40;border-radius:16px}
</style></head><body data-view="dashboard">
<div class="shell">
<aside class="sidebar">
  <div class="brand"><strong>MarketMint</strong><span>Mobile test</span></div>
  <nav class="primary-navigation">
    <div class="nav-group" data-nav-group="dashboard"><button class="nav-group-button" data-nav-default="dashboard" type="button"><span>◫</span><span class="nav-group-copy"><strong>Dashboard</strong><small>Today</small></span><span class="nav-caret">›</span></button><div class="nav-submenu"><button class="nav-button nav-subitem" data-view="dashboard" type="button"><span>•</span>Overview</button></div></div>
    <div class="nav-group" data-nav-group="operations"><button class="nav-group-button" data-nav-default="operations" type="button"><span>▦</span><span class="nav-group-copy"><strong>Store</strong><small>Catalog and website</small></span><span class="nav-caret">›</span></button><div class="nav-submenu"><button class="nav-button nav-subitem" data-view="catalog" type="button"><span>•</span>Catalog</button><button class="nav-button nav-subitem" data-view="website" type="button"><span>•</span>Website</button></div></div>
    <div class="nav-group"><button class="nav-group-button" data-nav-default="settings" type="button"><span>⚙</span><span class="nav-group-copy"><strong>Settings</strong><small>Connections</small></span><span class="nav-caret">›</span></button><div class="nav-submenu"><button class="nav-button nav-subitem" data-view="settings" type="button"><span>•</span>Connections</button></div></div>
  </nav>
  <div class="side-status">Connected</div><div class="sidebar-footer">QA fixture</div>
</aside>
<main class="main"><div class="topbar"><p class="eyebrow">COMMAND CENTER</p><h1 id="pageTitle">Dashboard</h1></div><div class="context-nav"><button class="context-nav-button" type="button">Summary</button></div><div class="view-card"><h2>Menu interaction test</h2><p>The sidebar should open, remain open on a group header, and close on a final destination.</p></div></main>
</div>
<script>
document.querySelectorAll('.nav-group-button').forEach(button=>button.addEventListener('click',()=>button.closest('.nav-group').classList.toggle('expanded')));
document.querySelectorAll('.nav-button[data-view]').forEach(button=>button.addEventListener('click',()=>{document.body.dataset.view=button.dataset.view;document.getElementById('pageTitle').textContent=button.textContent.trim();}));
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/mobile-control/ping':
            self._send(200, b'{"ok": true}', 'application/json')
        elif path == '/icon.png':
            self._send(200, PNG, 'image/png')
        else:
            self._send(200, HTML.encode(), 'text/html; charset=utf-8')

    def log_message(self, fmt, *args):
        print('[mock]', fmt % args, flush=True)

if __name__ == '__main__':
    print('Mock MarketMint server listening on 0.0.0.0:8765', flush=True)
    ThreadingHTTPServer(('0.0.0.0', 8765), Handler).serve_forever()
