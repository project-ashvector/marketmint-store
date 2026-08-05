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
button,input,select,textarea{font:inherit}.shell{min-height:100vh}.sidebar{position:fixed;inset:0 auto 0 0;width:var(--sidebar);padding:24px 16px;background:#0a0b12;display:flex;flex-direction:column;z-index:20}
.brand{padding:12px}.primary-navigation{display:flex;flex-direction:column;gap:8px}.nav-group{overflow:hidden;border:1px solid #292d40;border-radius:14px}.nav-group-button,.nav-button{width:100%;padding:14px;border:0;background:#11131d;color:#f7f6ff;text-align:left;font-size:16px}.nav-submenu{display:grid;gap:4px;padding:4px}.main{margin-left:var(--sidebar);padding:30px}.context-nav{display:flex;gap:8px}.context-nav-button{padding:12px}.side-status,.sidebar-footer{padding:10px}.view-card,.panel,.form-panel,.hero-card{margin-top:20px;padding:24px;border:1px solid #292d40;border-radius:16px;background:#11131d}.hero-card{display:grid;grid-template-columns:1.6fr 1fr;gap:24px;min-width:760px}.hero-actions{display:flex;gap:10px}.button{display:inline-flex;align-items:center;justify-content:center;padding:12px 18px;border:1px solid #654598;border-radius:12px;background:#251b38;color:#fff;text-decoration:none}.dashboard-metric-grid{display:grid;grid-template-columns:repeat(4,minmax(180px,1fr));gap:12px;min-width:820px;margin-top:18px}.metric-card{padding:18px;border:1px solid #292d40;border-radius:14px;background:#171927}.two-column{display:grid;grid-template-columns:1fr 1fr;gap:18px;min-width:760px}.field-pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}.field-pair label{display:grid;gap:6px}.field-pair input,.field-pair select,.form-panel textarea{width:100%;padding:12px}.form-panel textarea{min-height:120px}.site-actions,.row-actions{display:flex;gap:10px;margin-top:12px}.catalog-product-grid{display:grid;grid-template-columns:repeat(3,minmax(250px,1fr));gap:16px;min-width:900px}.catalog-product-card{padding:14px;border:1px solid #292d40;border-radius:16px;background:#171927}.catalog-product-card img{width:420px;height:300px;object-fit:cover}.table-panel{margin-top:18px;border:1px solid #292d40;border-radius:14px}.table-panel table{border-collapse:collapse;min-width:860px}.table-panel th,.table-panel td{padding:12px;border-bottom:1px solid #292d40;text-align:left}.long-copy{width:680px}.fixed-preview{width:620px;height:260px;border-radius:16px;background:linear-gradient(135deg,#42286d,#151724)}
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
<main class="main">
  <div class="topbar"><p class="eyebrow">COMMAND CENTER</p><h1 id="pageTitle">Dashboard</h1><div class="top-actions"><button class="button">Build storefront</button><button class="button">Refresh catalog</button><button class="button">Open preview</button></div></div>
  <div class="context-nav"><button class="context-nav-button" type="button">Summary</button><button class="context-nav-button" type="button">Catalog and listings</button><button class="context-nav-button" type="button">Collections</button></div>
  <section class="hero-card"><div><p>PHONE LAYOUT QA</p><h2>A deliberately desktop-sized MarketMint page that must become clean and readable on a phone.</h2><p class="long-copy">This extra-long copy and URL-like text verifies wrapping: https://ebedesigns.online/collections/this-is-a-deliberately-long-mobile-layout-test-value-that-must-not-expand-the-page</p><div class="hero-actions"><button class="button">Primary action with a longer label</button><button class="button">Secondary action</button></div></div><div class="fixed-preview"></div></section>
  <div class="dashboard-metric-grid"><article class="metric-card"><small>Products</small><strong>128</strong></article><article class="metric-card"><small>Needs attention</small><strong>17</strong></article><article class="metric-card"><small>Collections</small><strong>9</strong></article><article class="metric-card"><small>Site status</small><strong>Ready</strong></article></div>
  <div class="two-column"><section class="form-panel"><h2>Listing editor</h2><div class="field-pair"><label>Product title<input value="A very long product title that needs to remain inside the form"></label><label>Category<select><option>Shirts and oversized apparel</option></select></label></div><label>Description<textarea>This description field should resize to the full card width without forcing the phone page sideways.</textarea></label><label>Artwork file<input type="file"></label><div class="site-actions"><button class="button">Save listing draft</button><button class="button">Create another product</button></div></section><section class="panel"><h2>Preview</h2><div class="fixed-preview"></div><p>Images and preview blocks must contain themselves without cropping the surrounding card.</p></section></div>
  <section class="panel"><h2>Catalog cards</h2><div class="catalog-product-grid"><article class="catalog-product-card"><img src="/icon.png" alt=""><h3>Started From The Bottom Now I’m Mids</h3><p>Artwork and product copy stay readable at every tested width.</p><div class="row-actions"><button class="button">Edit copy</button><button class="button">Open product</button></div></article><article class="catalog-product-card"><img src="/icon.png" alt=""><h3>Second product with an intentionally long title</h3><p>Cards collapse into one clean phone column.</p></article><article class="catalog-product-card"><img src="/icon.png" alt=""><h3>Third product</h3><p>No horizontal page overflow.</p></article></div></section>
  <section class="table-panel"><table><thead><tr><th>Product</th><th>Status</th><th>Price</th><th>Collection</th><th>Actions</th></tr></thead><tbody><tr><td>Long catalog product name</td><td>Needs attention</td><td>$29.99</td><td>Featured collection</td><td>Edit · Preview · Open Fourthwall</td></tr></tbody></table></section>
  <div class="view-card"><h2>Menu interaction test</h2><p>The sidebar should open, remain open on a group header, and close on a final destination.</p></div>
</main>
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
