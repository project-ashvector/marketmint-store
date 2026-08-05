from pathlib import Path

path = Path('mobile-build/project/app/src/main/java/com/ebedesigns/marketmint/mobile/MainActivity.java')
text = path.read_text()

fields_marker = '''    private WebView webView;
    private ProgressBar pageProgress;
    private ValueCallback<Uri[]> pendingFileChooser;'''
fields_replacement = '''    private WebView webView;
    private ProgressBar pageProgress;
    private View nativeMenuTarget;
    private boolean nativeDrawerOpen;
    private ValueCallback<Uri[]> pendingFileChooser;'''
if fields_marker not in text:
    raise SystemExit('Could not find WebView fields')
text = text.replace(fields_marker, fields_replacement, 1)

prefs_marker = '''        serverUrl = prefs.getString(PREF_SERVER, "");
        pairingToken = prefs.getString(PREF_TOKEN, "");
        if (serverUrl.trim().isEmpty() || pairingToken.trim().isEmpty()) {'''
prefs_replacement = '''        serverUrl = prefs.getString(PREF_SERVER, "");
        pairingToken = prefs.getString(PREF_TOKEN, "");
        if ((getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
            String qaUrl = getIntent().getStringExtra("marketmint_qa_url");
            String qaToken = getIntent().getStringExtra("marketmint_qa_token");
            if (qaUrl != null && !qaUrl.trim().isEmpty() && qaToken != null && !qaToken.trim().isEmpty()) {
                serverUrl = ConnectionConfig.normalizeServerUrl(qaUrl);
                pairingToken = qaToken.trim();
            }
        }
        if (serverUrl.trim().isEmpty() || pairingToken.trim().isEmpty()) {'''
if prefs_marker not in text:
    raise SystemExit('Could not find preference loading block')
text = text.replace(prefs_marker, prefs_replacement, 1)

clear_marker = '''        root.removeAllViews();
    }

    private void showSetup'''
clear_replacement = '''        nativeMenuTarget = null;
        nativeDrawerOpen = false;
        root.removeAllViews();
    }

    private void showSetup'''
if clear_marker not in text:
    raise SystemExit('Could not find clearRoot end')
text = text.replace(clear_marker, clear_replacement, 1)

progress_marker = '''        FrameLayout.LayoutParams progressParams = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3));
        progressParams.gravity = Gravity.TOP;
        root.addView(pageProgress, progressParams);

        loadMarketMint(pairFirst);'''
progress_replacement = '''        FrameLayout.LayoutParams progressParams = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3));
        progressParams.gravity = Gravity.TOP;
        root.addView(pageProgress, progressParams);

        installNativeMenuTarget();
        loadMarketMint(pairFirst);'''
if progress_marker not in text:
    raise SystemExit('Could not find progress bar insertion point')
text = text.replace(progress_marker, progress_replacement, 1)

configure_marker = '''    private void configureWebView() {'''
native_methods = '''    private void installNativeMenuTarget() {
        View target = new View(this);
        target.setContentDescription("Open navigation");
        target.setClickable(true);
        target.setFocusable(true);
        target.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_YES);
        target.setBackgroundColor(Color.TRANSPARENT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) target.setElevation(dp(48));
        target.setOnClickListener(view -> toggleNativeDrawer());
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(dp(58), dp(58));
        params.gravity = Gravity.TOP | Gravity.START;
        root.addView(target, params);
        nativeMenuTarget = target;
        updateNativeMenuState(false);
    }

    private void updateNativeMenuState(boolean open) {
        nativeDrawerOpen = open;
        if (nativeMenuTarget != null) {
            nativeMenuTarget.setContentDescription(open ? "Close navigation" : "Open navigation");
            nativeMenuTarget.setSelected(open);
        }
    }

    private void toggleNativeDrawer() {
        if (webView == null) return;
        final boolean requestedOpen = !nativeDrawerOpen;
        Log.i("MarketMintDrawer", requestedOpen ? "NATIVE|REQUEST|OPEN" : "NATIVE|REQUEST|CLOSED");
        injectMobileExperience();
        String script = """
            (()=>{
              const body=document.body;
              const sidebar=document.querySelector('.sidebar');
              if(!body)return 'NO_BODY';
              const open=__OPEN__;
              if(window.__marketMintMobileSetDrawer){
                window.__marketMintMobileSetDrawer(open);
              }else{
                body.classList.toggle('mm-drawer-open',open);
                if(sidebar){
                  sidebar.style.setProperty('transform',open?'translate3d(0,0,0)':'translate3d(-105%,0,0)','important');
                  sidebar.style.setProperty('visibility',open?'visible':'hidden','important');
                  sidebar.style.setProperty('pointer-events',open?'auto':'none','important');
                  sidebar.setAttribute('aria-hidden',open?'false':'true');
                }
              }
              return open?'OPEN':'CLOSED';
            })();
            """.replace("__OPEN__", requestedOpen ? "true" : "false");
        webView.evaluateJavascript(script, value -> {
            boolean opened = value != null && value.contains("OPEN");
            updateNativeMenuState(opened);
            Log.i("MarketMintDrawer", opened ? "NATIVE|RESULT|OPEN" : "NATIVE|RESULT|CLOSED");
        });
    }

    private void configureWebView() {'''
if configure_marker not in text:
    raise SystemExit('Could not find configureWebView')
text = text.replace(configure_marker, native_methods, 1)

page_finished_marker = '''            public void onPageFinished(WebView view, String url) {
                if (pageProgress != null) pageProgress.setVisibility(View.GONE);
                injectMobileExperience();'''
page_finished_replacement = '''            public void onPageFinished(WebView view, String url) {
                if (pageProgress != null) pageProgress.setVisibility(View.GONE);
                if (nativeMenuTarget != null) nativeMenuTarget.bringToFront();
                Log.i("MarketMintDrawer", "PAGE|FINISHED|" + url);
                injectMobileExperience();'''
if page_finished_marker not in text:
    raise SystemExit('Could not find onPageFinished')
text = text.replace(page_finished_marker, page_finished_replacement, 1)

error_marker = '''            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) setMobileStatus("Connection unavailable", "error");
            }'''
error_replacement = '''            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    Log.e("MarketMintDrawer", "PAGE|ERROR|" + error.getErrorCode() + "|" + String.valueOf(error.getDescription()));
                    setMobileStatus("Connection unavailable", "error");
                }
            }'''
if error_marker not in text:
    raise SystemExit('Could not find onReceivedError')
text = text.replace(error_marker, error_replacement, 1)

bridge_marker = '''        public void reportDrawerState(String message) {
            Log.i("MarketMintDrawer", message == null ? "" : message);
        }'''
bridge_replacement = '''        public void reportDrawerState(String message) {
            String safeMessage = message == null ? "" : message;
            Log.i("MarketMintDrawer", safeMessage);
            if ("STATE|OPEN".equals(safeMessage)) {
                runOnUiThread(() -> updateNativeMenuState(true));
            } else if ("STATE|CLOSED".equals(safeMessage)) {
                runOnUiThread(() -> updateNativeMenuState(false));
            }
        }'''
if bridge_marker not in text:
    raise SystemExit('Could not find reportDrawerState bridge')
text = text.replace(bridge_marker, bridge_replacement, 1)

for expected in (
    'private View nativeMenuTarget;',
    'private void toggleNativeDrawer()',
    'NATIVE|REQUEST|OPEN',
    'NATIVE|RESULT|OPEN',
    'target.setContentDescription("Open navigation")',
    'marketmint_qa_url',
    'FLAG_DEBUGGABLE',
    'PAGE|FINISHED|',
):
    if expected not in text:
        raise SystemExit(f'Missing native menu change: {expected}')

path.write_text(text)
print('Added native Android hamburger bridge and debug QA launch override')
