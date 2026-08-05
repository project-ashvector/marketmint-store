from pathlib import Path

path = Path('mobile-build/project/app/src/main/java/com/ebedesigns/marketmint/mobile/MainActivity.java')
text = path.read_text()

replacements = {
    '        settings.setUseWideViewPort(true);': '        settings.setUseWideViewPort(false);',
    '        settings.setLoadWithOverviewMode(true);': '        settings.setLoadWithOverviewMode(false);',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f'Could not find wide viewport setting: {old}')
    text = text.replace(old, new, 1)

if '        webView.setInitialScale(0);' not in text:
    raise SystemExit('Density-aware default initial scale was not found')

path.write_text(text)
print('Applied density-independent WebView viewport: wide viewport off, overview off, default scale')
