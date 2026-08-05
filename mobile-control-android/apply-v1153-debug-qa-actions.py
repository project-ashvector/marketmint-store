from pathlib import Path

path = Path('mobile-build/project/app/src/main/java/com/ebedesigns/marketmint/mobile/MainActivity.java')
text = path.read_text()

resume_marker = '''    @Override
    protected void onResume() {
        super.onResume();
        enterImmersiveMode();
    }

    private int dp(int value) {'''
resume_replacement = '''    @Override
    protected void onResume() {
        super.onResume();
        enterImmersiveMode();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        maybeRunDebugQaAction(intent);
    }

    private boolean isDebuggableBuild() {
        return (getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0;
    }

    private void maybeRunDebugQaAction(Intent intent) {
        if (!isDebuggableBuild() || intent == null) return;
        String action = intent.getStringExtra("marketmint_qa_action");
        if (action == null || action.trim().isEmpty()) return;
        intent.removeExtra("marketmint_qa_action");
        String normalized = action.trim().toLowerCase(java.util.Locale.ROOT);
        root.post(() -> {
            recordDrawerEvent("QA|ACTION|" + normalized.toUpperCase(java.util.Locale.ROOT));
            if ("menu".equals(normalized)) {
                if (nativeMenuTarget == null) {
                    recordDrawerEvent("QA|ERROR|MENU_TARGET_MISSING");
                    return;
                }
                boolean clicked = nativeMenuTarget.performClick();
                recordDrawerEvent(clicked ? "QA|RESULT|MENU_CLICKED" : "QA|ERROR|MENU_CLICK_REJECTED");
                return;
            }
            if (webView == null) {
                recordDrawerEvent("QA|ERROR|WEBVIEW_MISSING");
                return;
            }
            String selector;
            if ("store".equals(normalized)) {
                selector = "[data-nav-default='operations']";
            } else if ("catalog".equals(normalized)) {
                selector = ".nav-button[data-view='catalog']";
            } else {
                recordDrawerEvent("QA|ERROR|UNKNOWN_ACTION|" + normalized);
                return;
            }
            String script = """
                (()=>{
                  const node=document.querySelector(__SELECTOR__);
                  if(!node)return 'MISSING';
                  node.click();
                  return 'CLICKED';
                })();
                """.replace("__SELECTOR__", org.json.JSONObject.quote(selector));
            webView.evaluateJavascript(script, value -> {
                boolean clicked = value != null && value.contains("CLICKED");
                recordDrawerEvent(clicked
                    ? "QA|RESULT|" + normalized.toUpperCase(java.util.Locale.ROOT) + "_CLICKED"
                    : "QA|ERROR|" + normalized.toUpperCase(java.util.Locale.ROOT) + "_MISSING");
            });
        });
    }

    private int dp(int value) {'''
if resume_marker not in text:
    raise SystemExit('Could not find onResume insertion point')
text = text.replace(resume_marker, resume_replacement, 1)

for expected in (
    'protected void onNewIntent(Intent intent)',
    'marketmint_qa_action',
    'nativeMenuTarget.performClick()',
    'QA|RESULT|MENU_CLICKED',
    "[data-nav-default='operations']",
    ".nav-button[data-view='catalog']",
):
    if expected not in text:
        raise SystemExit(f'Missing debug QA action change: {expected}')

path.write_text(text)
print('Added debug-only native and WebView QA actions')
