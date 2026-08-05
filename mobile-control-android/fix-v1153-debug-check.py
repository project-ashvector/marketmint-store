from pathlib import Path

path = Path('mobile-build/project/app/src/main/java/com/ebedesigns/marketmint/mobile/MainActivity.java')
text = path.read_text()
old = '        if (BuildConfig.DEBUG) {'
new = '        if ((getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0) {'
if old not in text:
    raise SystemExit('BuildConfig debug check was not found')
text = text.replace(old, new, 1)
path.write_text(text)
print('Replaced unavailable BuildConfig.DEBUG with Android debuggable flag')
