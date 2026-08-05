from pathlib import Path
import re

path = Path('mobile-build/project/app/src/main/java/com/ebedesigns/marketmint/mobile/MainActivity.java')
text = path.read_text()

webview_replacements = {
    '        settings.setUseWideViewPort(false);': '        settings.setUseWideViewPort(true);',
    '        settings.setLoadWithOverviewMode(false);': '        settings.setLoadWithOverviewMode(true);',
    '        webView.setInitialScale(100);': '        webView.setInitialScale(0);',
}
for old, new in webview_replacements.items():
    if old not in text:
        raise SystemExit(f'Could not find WebView scaling line: {old}')
    text = text.replace(old, new, 1)

phone_css = r'''
        /* v1.15.3 phone-fit layer: keep desktop-sized content inside the Android viewport. */
        body.marketmint-mobile-app,
        body.marketmint-mobile-app *{box-sizing:border-box!important;}
        body.marketmint-mobile-app .main :where(div,section,article,aside,header,footer,form,fieldset,label){
          min-width:0!important;
          max-width:100%!important;
        }
        body.marketmint-mobile-app .main :where(h1,h2,h3,h4,h5,h6,p,span,strong,small,em,li,dt,dd,label,legend){
          max-width:100%!important;
          overflow-wrap:anywhere!important;
          word-break:normal!important;
        }
        body.marketmint-mobile-app .main :where(ul,ol,dl){
          max-width:100%!important;
          padding-left:22px!important;
        }
        body.marketmint-mobile-app .main :where(svg,canvas,picture,img,video,iframe){
          display:block;
          width:auto;
          max-width:100%!important;
          height:auto;
        }
        body.marketmint-mobile-app .main picture,
        body.marketmint-mobile-app .main picture img{width:100%!important;}
        body.marketmint-mobile-app .main :where(pre,code,kbd,samp){
          max-width:100%!important;
          overflow-wrap:anywhere!important;
          white-space:pre-wrap!important;
        }
        body.marketmint-mobile-app .main pre{
          width:100%!important;
          overflow:auto!important;
          -webkit-overflow-scrolling:touch;
        }
        body.marketmint-mobile-app fieldset{
          width:100%!important;
          margin:0!important;
          padding:12px!important;
        }
        body.marketmint-mobile-app label{display:grid!important;gap:6px!important;}
        body.marketmint-mobile-app input:not([type="checkbox"]):not([type="radio"]):not([type="range"]),
        body.marketmint-mobile-app select,
        body.marketmint-mobile-app textarea{
          display:block!important;
          width:100%!important;
          max-width:100%!important;
          min-width:0!important;
          min-height:44px!important;
          padding:11px 12px!important;
          border-radius:12px!important;
        }
        body.marketmint-mobile-app textarea{
          min-height:112px!important;
          resize:vertical!important;
        }
        body.marketmint-mobile-app input[type="file"]{
          min-height:48px!important;
          padding:9px!important;
          font-size:13px!important;
          overflow:hidden!important;
        }
        body.marketmint-mobile-app input[type="checkbox"],
        body.marketmint-mobile-app input[type="radio"],
        body.marketmint-mobile-app input[type="range"]{
          width:auto!important;
          max-width:100%!important;
          min-width:0!important;
          flex:0 0 auto!important;
        }
        body.marketmint-mobile-app :where(.panel-head,.section-head,.site-actions,.row-actions,.background-actions,.hero-actions,.dashboard-hero-actions,.appearance-hero-actions,.catalog-copy-actions,.catalog-bulk-bar,.safety-toolbar){
          width:100%!important;
          min-width:0!important;
          gap:8px!important;
        }
        body.marketmint-mobile-app :where(.site-actions,.row-actions,.background-actions,.catalog-copy-actions) > *{
          flex:1 1 132px!important;
          min-width:0!important;
          max-width:100%!important;
        }
        body.marketmint-mobile-app :where(.button,.row-link,button[role="button"]){
          min-width:0!important;
          max-width:100%!important;
          padding:10px 12px!important;
          overflow-wrap:anywhere!important;
        }
        body.marketmint-mobile-app :where(.panel,.form-panel,.banner,.hero-card,.dashboard-hero,.operations-hero,.growth-hero,.conversion-hero,.audience-hero,.revenue-hero,.merch-hero,.launch-hero,.appearance-hero,.mobile-control-hero){
          overflow:hidden!important;
        }
        body.marketmint-mobile-app :where(.dashboard-action,.dashboard-detail-card,.today-card,.metric-card,.product-row,.listing-draft,.catalog-product-card,.catalog-card,.collection-card,.social-asset-card,.appearance-preset-card,.safety-card,.status-card){
          width:100%!important;
          min-width:0!important;
          max-width:100%!important;
          overflow:hidden!important;
        }
        body.marketmint-mobile-app :where(.catalog-product-card,.catalog-card,.collection-card,.social-asset-card,.appearance-preset-card){
          display:grid!important;
          grid-template-columns:minmax(0,1fr)!important;
          align-content:start!important;
        }
        body.marketmint-mobile-app :where(.catalog-product-card img,.catalog-card img,.collection-card img,.social-asset-card img,.appearance-preset-card img,.product-image,.collection-image,.listing-draft img){
          width:100%!important;
          height:auto!important;
          max-height:min(52vh,340px)!important;
          object-fit:contain!important;
          object-position:center!important;
          background:rgba(7,8,14,.42);
        }
        body.marketmint-mobile-app :where(.catalog-product-media,.product-media,.collection-art-preview,.collection-promo-preview,.background-preview,.social-asset-preview){
          width:100%!important;
          min-width:0!important;
          max-width:100%!important;
          overflow:hidden!important;
          border-radius:14px!important;
        }
        body.marketmint-mobile-app :where(.catalog-product-body,.catalog-product-copy,.collection-card-body,.social-asset-copy,.listing-draft-copy){
          width:100%!important;
          min-width:0!important;
          max-width:100%!important;
        }
        body.marketmint-mobile-app :where(.dashboard-today-grid,.dashboard-metric-grid,.metric-grid,.catalog-metrics,.appearance-status-grid,.safety-overview-grid,.background-status-grid,.dashboard-main-grid,.dashboard-detail-grid,.two-column,.traffic-layout,.audience-layout,.conversion-layout,.control-layout,.launch-layout,.merch-layout,.setup-grid,.mobile-control-grid,.safety-health-grid,.safety-backup-grid,.safety-rollback-grid,.appearance-design-layout,.catalog-copy-columns,.catalog-lower-layout,.collection-layout,.collection-art-layout,.social-layout,.revenue-layout,.catalog-product-grid,.social-asset-grid,.listing-draft-grid,.appearance-preset-grid,.collection-grid,.field-pair,.appearance-basic-grid,.catalog-toolbar){
          min-width:0!important;
          max-width:100%!important;
        }
        body.marketmint-mobile-app :where(.table-panel,.control-table-wrap,.activity-log,.responsive-table,.table-wrap){
          display:block!important;
          width:100%!important;
          max-width:100%!important;
          min-width:0!important;
          overflow-x:auto!important;
          overflow-y:hidden!important;
          overscroll-behavior-x:contain;
          -webkit-overflow-scrolling:touch;
          scrollbar-width:thin;
        }
        body.marketmint-mobile-app :where(.table-panel,.control-table-wrap,.responsive-table,.table-wrap) table{
          width:max-content!important;
          min-width:100%!important;
          max-width:none!important;
        }
        body.marketmint-mobile-app table :where(th,td){
          max-width:min(68vw,280px)!important;
          padding:10px!important;
          white-space:normal!important;
          overflow-wrap:anywhere!important;
        }
        body.marketmint-mobile-app :where(.modal,.dialog,.dialog-panel,.modal-panel,[role="dialog"]){
          width:calc(100vw - 20px)!important;
          max-width:calc(100vw - 20px)!important;
          max-height:calc(100dvh - var(--mm-mobile-header) - 24px)!important;
          margin:auto!important;
          overflow:auto!important;
          border-radius:16px!important;
        }
        body.marketmint-mobile-app :where(.phone-stage,.preview-stage,.site-preview,.preview-frame){
          width:100%!important;
          min-width:0!important;
          max-width:100%!important;
          overflow:hidden!important;
        }
        body.marketmint-mobile-app .phone-device,
        body.marketmint-mobile-app .phone-device iframe{
          width:100%!important;
          max-width:100%!important;
          height:min(72dvh,680px)!important;
          min-height:480px!important;
        }
        body.marketmint-mobile-app .top-actions,
        body.marketmint-mobile-app .context-nav,
        body.marketmint-mobile-app .appearance-tabs,
        body.marketmint-mobile-app .safety-tabs{
          overscroll-behavior-x:contain;
          -webkit-overflow-scrolling:touch;
        }
        @media(max-width:430px){
          .mm-mobile-header{
            grid-template-columns:42px minmax(0,1fr) auto;
            gap:6px;
            padding-left:6px;
            padding-right:6px;
          }
          .mm-mobile-title{grid-template-columns:30px minmax(0,1fr);gap:7px;}
          .mm-mobile-title img{width:30px;height:30px;}
          .mm-mobile-header-actions{gap:4px;}
          .mm-mobile-header-actions button{width:36px;height:36px;min-width:36px;min-height:36px;}
          .mm-mobile-header-actions button:first-child{display:none;}
          body.marketmint-mobile-app .main{padding-left:8px!important;padding-right:8px!important;}
          body.marketmint-mobile-app :where(.panel,.form-panel,.banner,.hero-card,.dashboard-hero,.operations-hero,.growth-hero,.conversion-hero,.audience-hero,.revenue-hero,.merch-hero,.launch-hero,.appearance-hero,.mobile-control-hero){
            padding:13px!important;
            border-radius:14px!important;
          }
          body.marketmint-mobile-app :where(.hero-actions,.dashboard-hero-actions,.appearance-hero-actions){
            grid-template-columns:minmax(0,1fr)!important;
          }
          body.marketmint-mobile-app .product-row{
            grid-template-columns:minmax(0,1fr)!important;
          }
          body.marketmint-mobile-app .product-row>*{grid-column:1!important;}
          body.marketmint-mobile-app .dashboard-site-status{grid-template-columns:minmax(0,1fr)!important;}
        }
        @media(max-width:350px){
          .mm-mobile-title img{display:none;}
          .mm-mobile-title{grid-template-columns:minmax(0,1fr);}
          .mm-mobile-status{font-size:8px;}
          body.marketmint-mobile-app :where(.dashboard-today-grid,.dashboard-metric-grid,.metric-grid,.catalog-metrics,.appearance-status-grid,.safety-overview-grid,.background-status-grid){
            grid-template-columns:minmax(0,1fr)!important;
          }
        }
'''

css_match = re.search(
    r'(private static final String MOBILE_CSS = """\n)(.*?)(\n        """;)',
    text,
    flags=re.S,
)
if not css_match:
    raise SystemExit('MOBILE_CSS block was not found')
if 'v1.15.3 phone-fit layer' not in css_match.group(2):
    css_body = css_match.group(2) + phone_css
    text = text[:css_match.start()] + css_match.group(1) + css_body + css_match.group(3) + text[css_match.end():]

script_marker = '''            window.__marketMintMobileApplied=true;
            reportDrawer('READY');'''
script_replacement = '''            window.__marketMintMobileApplied=true;
            const reportPhoneLayout=()=>{
              const viewport=Math.round(window.innerWidth||document.documentElement.clientWidth||0);
              const doc=Math.round(document.documentElement.scrollWidth||0);
              const bodyWidth=Math.round(document.body.scrollWidth||0);
              const main=document.querySelector('.main');
              const mainWidth=Math.round(main?.scrollWidth||0);
              const headerWidth=Math.round(document.getElementById('mmMobileHeader')?.scrollWidth||0);
              const dpr=Math.round((window.devicePixelRatio||1)*100)/100;
              const allowed='.table-panel,.control-table-wrap,.activity-log,.responsive-table,.table-wrap,.top-actions,.context-nav,.appearance-tabs,.safety-tabs,.sidebar';
              let oversized=0;
              document.querySelectorAll('body.marketmint-mobile-app .main *').forEach(node=>{
                if(!(node instanceof HTMLElement)||node.closest(allowed))return;
                const style=getComputedStyle(node);
                if(style.position==='fixed'||style.position==='absolute'||style.display==='none')return;
                const rect=node.getBoundingClientRect();
                if(rect.width>viewport+2||rect.right>viewport+2||rect.left<-2)oversized+=1;
              });
              reportDrawer(['LAYOUT',viewport,doc,bodyWidth,mainWidth,headerWidth,oversized,dpr].join('|'));
            };
            window.__marketMintMobileReportLayout=reportPhoneLayout;
            if(window.__marketMintMobileLayoutResizeHandler){
              window.removeEventListener('resize',window.__marketMintMobileLayoutResizeHandler);
            }
            window.__marketMintMobileLayoutResizeHandler=()=>{
              clearTimeout(window.__marketMintMobileLayoutTimer);
              window.__marketMintMobileLayoutTimer=setTimeout(reportPhoneLayout,240);
            };
            window.addEventListener('resize',window.__marketMintMobileLayoutResizeHandler,{passive:true});
            setTimeout(reportPhoneLayout,180);
            setTimeout(reportPhoneLayout,900);
            reportDrawer('READY');'''
if script_marker not in text:
    raise SystemExit('Could not find READY marker for phone layout reporting')
text = text.replace(script_marker, script_replacement, 1)

for expected in (
    'settings.setUseWideViewPort(true);',
    'settings.setLoadWithOverviewMode(true);',
    'webView.setInitialScale(0);',
    'v1.15.3 phone-fit layer',
    'body.marketmint-mobile-app .main :where(div,section,article,aside,header,footer,form,fieldset,label)',
    '@media(max-width:430px)',
    'window.__marketMintMobileReportLayout=reportPhoneLayout',
    "reportDrawer(['LAYOUT',viewport,doc,bodyWidth,mainWidth,headerWidth,oversized,dpr].join('|'))",
):
    if expected not in text:
        raise SystemExit(f'Missing phone-fit change: {expected}')

path.write_text(text)
print('Applied true mobile WebView scaling, comprehensive phone-fit CSS, and layout overflow reporting')
