from pathlib import Path
import re

root = Path('mobile-build/project')
java_path = root / 'app/src/main/java/com/ebedesigns/marketmint/mobile/MainActivity.java'
gradle_path = root / 'app/build.gradle'

text = java_path.read_text()
text = re.sub(r'private static final String MOBILE_VERSION = "[^"]+";',
              'private static final String MOBILE_VERSION = "1.15.3";', text, count=1)

replacements = {
'''        .mm-mobile-header button:active{transform:scale(.96);background:rgba(165,108,255,.18);}''':
'''        .mm-mobile-header,.mm-mobile-header *{pointer-events:auto!important;}
        #mmMobileMenu{position:relative;z-index:2;touch-action:manipulation!important;-webkit-tap-highlight-color:transparent;}
        .mm-mobile-header button:active{transform:scale(.96);background:rgba(165,108,255,.18);}''',
'''          transition:opacity .2s ease,visibility .2s ease;
        }
        body.mm-drawer-open .mm-mobile-scrim{opacity:1;visibility:visible;}''':
'''          pointer-events:none;
          transition:opacity .2s ease,visibility .2s ease;
        }
        body.marketmint-mobile-app.mm-drawer-open .mm-mobile-scrim{opacity:1;visibility:visible;pointer-events:auto;}''',
'''          transform:translate3d(-105%,0,0);
          transition:transform .23s cubic-bezier(.2,.8,.2,1);''':
'''          transform:translate3d(-105%,0,0)!important;
          visibility:hidden!important;
          pointer-events:none!important;
          transition:transform .23s cubic-bezier(.2,.8,.2,1),visibility .23s ease;''',
'''        body.mm-drawer-open .sidebar{transform:translate3d(0,0,0);}''':
'''        body.marketmint-mobile-app.mm-drawer-open .sidebar{transform:translate3d(0,0,0)!important;visibility:visible!important;pointer-events:auto!important;}''',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f'Missing expected CSS block: {old[:80]!r}')
    text = text.replace(old, new, 1)

start_marker = '    private static final String MOBILE_SCRIPT = """'
end_marker = '\n        """;'
start = text.index(start_marker)
end = text.index(end_marker, start) + len(end_marker)
new_script = '''    private static final String MOBILE_SCRIPT = """
        (()=>{
          const apply=()=>{
            const body=document.body;
            if(!body)return;
            document.documentElement.classList.add('marketmint-mobile-shell');
            body.classList.add('marketmint-mobile-app');
            let viewport=document.querySelector('meta[name="viewport"]');
            if(!viewport){viewport=document.createElement('meta');viewport.name='viewport';document.head.appendChild(viewport);}
            viewport.content='width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover';
            let style=document.getElementById('marketmint-mobile-v115-style');
            if(!style){style=document.createElement('style');style.id='marketmint-mobile-v115-style';document.head.appendChild(style);}
            style.textContent=__CSS__;

            let header=document.getElementById('mmMobileHeader');
            if(!header){
              header=document.createElement('header');
              header.id='mmMobileHeader';
              header.className='mm-mobile-header';
              header.innerHTML=`
                <button id="mmMobileMenu" type="button" aria-label="Open navigation" aria-expanded="false">☰</button>
                <div class="mm-mobile-title">
                  <img src="/icon.png" alt="">
                  <div class="mm-mobile-title-copy">
                    <strong id="mmMobileTitle">MarketMint</strong>
                    <div class="mm-mobile-status" id="mmMobileStatus" data-state="loading"><span class="mm-mobile-status-dot"></span><span id="mmMobileStatusText">Connecting over Tailscale</span></div>
                  </div>
                </div>
                <div class="mm-mobile-header-actions">
                  <button id="mmMobileBack" type="button" aria-label="Go back">‹</button>
                  <button id="mmMobileRefresh" type="button" aria-label="Refresh">↻</button>
                  <button id="mmMobileSettings" type="button" aria-label="Connection settings">⚙</button>
                </div>`;
              body.prepend(header);
            }

            let scrim=document.getElementById('mmMobileScrim');
            if(!scrim){
              scrim=document.createElement('div');
              scrim.id='mmMobileScrim';
              scrim.className='mm-mobile-scrim';
              body.insertBefore(scrim,header.nextSibling);
            }

            const setDrawer=open=>{
              const shouldOpen=Boolean(open);
              body.classList.toggle('mm-drawer-open',shouldOpen);
              const menu=document.getElementById('mmMobileMenu');
              if(menu){
                menu.setAttribute('aria-expanded',shouldOpen?'true':'false');
                menu.setAttribute('aria-label',shouldOpen?'Close navigation':'Open navigation');
              }
              const sidebar=document.querySelector('.sidebar');
              if(sidebar)sidebar.setAttribute('aria-hidden',shouldOpen?'false':'true');
            };
            const toggleDrawer=event=>{
              if(event){event.preventDefault();event.stopPropagation();}
              setDrawer(!body.classList.contains('mm-drawer-open'));
              return false;
            };
            const closeDrawer=()=>setDrawer(false);
            window.__marketMintMobileSetDrawer=setDrawer;
            window.__marketMintMobileToggleDrawer=toggleDrawer;
            window.__marketMintMobileCloseDrawer=closeDrawer;

            header.onclick=event=>{
              const button=event.target.closest('button');
              if(!button)return;
              if(button.id==='mmMobileMenu'){toggleDrawer(event);return;}
              if(button.id==='mmMobileBack'){event.preventDefault();window.MarketMintMobile?.goBack();return;}
              if(button.id==='mmMobileRefresh'){event.preventDefault();window.MarketMintMobile?.refresh();return;}
              if(button.id==='mmMobileSettings'){event.preventDefault();window.MarketMintMobile?.openConnectionMenu();}
            };
            scrim.onclick=event=>{event.preventDefault();closeDrawer();};

            if(window.__marketMintMobileNavCloseHandler){
              document.removeEventListener('click',window.__marketMintMobileNavCloseHandler,true);
            }
            window.__marketMintMobileNavCloseHandler=event=>{
              if(event.target.closest('#mmMobileHeader,.nav-group-button'))return;
              if(event.target.closest('.nav-button[data-view],.context-nav-button,[data-open-view]')){
                setTimeout(closeDrawer,120);
              }
            };
            document.addEventListener('click',window.__marketMintMobileNavCloseHandler,true);

            if(!window.__marketMintMobileSwipeInstalled){
              let startX=0,startY=0;
              body.addEventListener('touchstart',event=>{
                const touch=event.touches&&event.touches[0];
                if(!touch)return;
                startX=touch.clientX;startY=touch.clientY;
              },{passive:true});
              body.addEventListener('touchend',event=>{
                const touch=event.changedTouches&&event.changedTouches[0];
                if(!touch)return;
                const dx=touch.clientX-startX;
                const dy=Math.abs(touch.clientY-startY);
                if(dy>70)return;
                if(startX<36&&dx>80)setDrawer(true);
                else if(body.classList.contains('mm-drawer-open')&&dx<-80)setDrawer(false);
              },{passive:true});
              window.__marketMintMobileSwipeInstalled=true;
            }

            const syncTitle=()=>{
              const title=document.getElementById('pageTitle')?.textContent?.trim()||'MarketMint';
              const target=document.getElementById('mmMobileTitle');
              if(target)target.textContent=title;
            };
            syncTitle();
            const pageTitle=document.getElementById('pageTitle');
            if(pageTitle&&!pageTitle.dataset.mobileObserved){
              pageTitle.dataset.mobileObserved='true';
              new MutationObserver(syncTitle).observe(pageTitle,{childList:true,subtree:true,characterData:true});
            }
            window.__marketMintMobileSetStatus=(label,state='ok')=>{
              const node=document.getElementById('mmMobileStatus');
              const text=document.getElementById('mmMobileStatusText');
              if(node)node.dataset.state=state;
              if(text)text.textContent=label;
            };
            window.__marketMintMobileApplied=true;
          };
          if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply,{once:true});else apply();
        })();
        """;'''
text = text[:start] + new_script + text[end:]
java_path.write_text(text)

gradle = gradle_path.read_text()
gradle = re.sub(r"applicationId\s+'[^']+'", "applicationId 'com.ebedesigns.marketmint.controlcenter'", gradle)
gradle = re.sub(r'versionCode\s+\d+', 'versionCode 11503', gradle)
gradle = re.sub(r"versionName\s+'[^']+'", "versionName '1.15.3'", gradle)
gradle = re.sub(r'\n\s{4}signingConfigs \{.*?\n\s{4}\}\n', '\n', gradle, flags=re.S)
gradle = re.sub(r'^\s*signingConfig signingConfigs\.release\s*$', '', gradle, flags=re.M)
gradle_path.write_text(gradle)

assert 'window.__marketMintMobileToggleDrawer=toggleDrawer' in text
assert "event.target.closest('#mmMobileHeader,.nav-group-button')" in text
assert 'transform:translate3d(0,0,0)!important' in text
assert "versionCode 11503" in gradle
assert "versionName '1.15.3'" in gradle
print('Applied MarketMint Mobile v1.15.3 menu fix')
