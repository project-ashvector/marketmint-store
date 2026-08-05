from pathlib import Path

path = Path('mobile-build/project/app/src/main/java/com/ebedesigns/marketmint/mobile/MainActivity.java')
text = path.read_text()

if 'import android.util.Log;' not in text:
    marker = 'import android.provider.Settings;\n'
    if marker not in text:
        raise SystemExit('Could not find Settings import')
    text = text.replace(marker, marker + 'import android.util.Log;\n', 1)

set_drawer_marker = '''            const setDrawer=open=>{
              const shouldOpen=Boolean(open);'''
set_drawer_replacement = '''            const reportDrawer=message=>{
              try{window.MarketMintMobile?.reportDrawerState(String(message));}catch(_){ }
            };
            const nodeBounds=(name,node)=>{
              if(!node)return name+',missing';
              const rect=node.getBoundingClientRect();
              return [name,rect.left,rect.top,rect.width,rect.height].join(',');
            };
            const reportBounds=()=>{
              const menu=document.getElementById('mmMobileMenu');
              const operations=document.querySelector('[data-nav-default="operations"]')
                || Array.from(document.querySelectorAll('.nav-group-button')).find(node=>/store|catalog/i.test(node.textContent||''));
              const catalog=document.querySelector('.nav-button[data-view="catalog"]')
                || Array.from(document.querySelectorAll('.nav-button[data-view]')).find(node=>/catalog/i.test(node.textContent||''));
              reportDrawer([
                'BOUNDS',window.innerWidth,window.innerHeight,
                nodeBounds('menu',menu),nodeBounds('operations',operations),nodeBounds('catalog',catalog)
              ].join('|'));
            };
            const setDrawer=open=>{
              const shouldOpen=Boolean(open);'''
if set_drawer_marker not in text:
    raise SystemExit('Could not find setDrawer marker')
text = text.replace(set_drawer_marker, set_drawer_replacement, 1)

sidebar_marker = '''              const sidebar=document.querySelector('.sidebar');
              if(sidebar)sidebar.setAttribute('aria-hidden',shouldOpen?'false':'true');
            };'''
sidebar_replacement = '''              const sidebar=document.querySelector('.sidebar');
              if(sidebar)sidebar.setAttribute('aria-hidden',shouldOpen?'false':'true');
              reportDrawer(shouldOpen?'STATE|OPEN':'STATE|CLOSED');
              if(shouldOpen)setTimeout(reportBounds,360);
            };'''
if sidebar_marker not in text:
    raise SystemExit('Could not find sidebar state marker')
text = text.replace(sidebar_marker, sidebar_replacement, 1)

menu_marker = '''              if(button.id==='mmMobileMenu'){toggleDrawer(event);return;}'''
menu_replacement = '''              if(button.id==='mmMobileMenu'){reportDrawer('CLICK|MENU');toggleDrawer(event);return;}'''
if menu_marker not in text:
    raise SystemExit('Could not find menu click marker')
text = text.replace(menu_marker, menu_replacement, 1)

nav_marker = '''            window.__marketMintMobileNavCloseHandler=event=>{
              if(event.target.closest('#mmMobileHeader,.nav-group-button'))return;
              if(event.target.closest('.nav-button[data-view],.context-nav-button,[data-open-view]')){
                setTimeout(closeDrawer,120);
              }
            };'''
nav_replacement = '''            window.__marketMintMobileNavCloseHandler=event=>{
              if(event.target.closest('#mmMobileHeader'))return;
              if(event.target.closest('.nav-group-button')){
                reportDrawer('NAV|GROUP');
                setTimeout(reportBounds,360);
                return;
              }
              if(event.target.closest('.nav-button[data-view],.context-nav-button,[data-open-view]')){
                reportDrawer('NAV|DESTINATION');
                setTimeout(closeDrawer,120);
              }
            };'''
if nav_marker not in text:
    raise SystemExit('Could not find navigation close handler')
text = text.replace(nav_marker, nav_replacement, 1)

ready_marker = '''            window.__marketMintMobileApplied=true;
          };'''
ready_replacement = '''            window.__marketMintMobileApplied=true;
            reportDrawer('READY');
            setTimeout(reportBounds,120);
          };'''
if ready_marker not in text:
    raise SystemExit('Could not find mobile applied marker')
text = text.replace(ready_marker, ready_replacement, 1)

bridge_marker = '''        @JavascriptInterface
        public void openConnectionMenu() {
            runOnUiThread(MainActivity.this::showConnectionMenu);
        }'''
bridge_replacement = '''        @JavascriptInterface
        public void reportDrawerState(String message) {
            Log.i("MarketMintDrawer", message == null ? "" : message);
        }

        @JavascriptInterface
        public void openConnectionMenu() {
            runOnUiThread(MainActivity.this::showConnectionMenu);
        }'''
if bridge_marker not in text:
    raise SystemExit('Could not find MobileBridge insertion point')
text = text.replace(bridge_marker, bridge_replacement, 1)

for expected in (
    'Log.i("MarketMintDrawer"',
    "reportDrawer('CLICK|MENU')",
    "reportDrawer('NAV|GROUP')",
    "reportDrawer('NAV|DESTINATION')",
    "reportDrawer('READY')",
):
    if expected not in text:
        raise SystemExit(f'Missing expected probe: {expected}')

path.write_text(text)
print('Added live MarketMint drawer reporting for physical tap QA')
