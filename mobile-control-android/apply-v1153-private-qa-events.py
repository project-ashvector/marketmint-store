from pathlib import Path

path = Path('mobile-build/project/app/src/main/java/com/ebedesigns/marketmint/mobile/MainActivity.java')
text = path.read_text()

install_marker = '''    private void installNativeMenuTarget() {'''
record_method = '''    private void recordDrawerEvent(String message) {
        String safeMessage = message == null ? "" : message;
        Log.i("MarketMintDrawer", safeMessage);
        if ((getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) == 0) return;
        try (java.io.FileOutputStream stream = openFileOutput("drawer-qa-events.txt", MODE_APPEND)) {
            stream.write((safeMessage + "\\n").getBytes(java.nio.charset.StandardCharsets.UTF_8));
            stream.flush();
        } catch (java.io.IOException error) {
            Log.e("MarketMintDrawer", "QA_FILE_ERROR|" + error.getMessage());
        }
    }

    private void installNativeMenuTarget() {'''
if install_marker not in text:
    raise SystemExit('Could not find installNativeMenuTarget')
text = text.replace(install_marker, record_method, 1)

replacements = {
    '        Log.i("MarketMintDrawer", requestedOpen ? "NATIVE|REQUEST|OPEN" : "NATIVE|REQUEST|CLOSED");':
        '        recordDrawerEvent(requestedOpen ? "NATIVE|REQUEST|OPEN" : "NATIVE|REQUEST|CLOSED");',
    '            Log.i("MarketMintDrawer", opened ? "NATIVE|RESULT|OPEN" : "NATIVE|RESULT|CLOSED");':
        '            recordDrawerEvent(opened ? "NATIVE|RESULT|OPEN" : "NATIVE|RESULT|CLOSED");',
    '                Log.i("MarketMintDrawer", "PAGE|FINISHED|" + url);':
        '                recordDrawerEvent("PAGE|FINISHED|" + url);',
    '                    Log.e("MarketMintDrawer", "PAGE|ERROR|" + error.getErrorCode() + "|" + String.valueOf(error.getDescription()));':
        '                    recordDrawerEvent("PAGE|ERROR|" + error.getErrorCode() + "|" + String.valueOf(error.getDescription()));',
    '            Log.i("MarketMintDrawer", safeMessage);':
        '            recordDrawerEvent(safeMessage);',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f'Could not find event log line: {old}')
    text = text.replace(old, new, 1)

state_marker = '''        if (nativeMenuTarget != null) {
            nativeMenuTarget.setContentDescription(open ? "Close navigation" : "Open navigation");
            nativeMenuTarget.setSelected(open);
        }
    }'''
state_replacement = '''        if (nativeMenuTarget != null) {
            nativeMenuTarget.setContentDescription(open ? "Close navigation" : "Open navigation");
            nativeMenuTarget.setSelected(open);
        }
        recordDrawerEvent(open ? "NATIVE|TARGET|CLOSE" : "NATIVE|TARGET|OPEN");
    }'''
if state_marker not in text:
    raise SystemExit('Could not find native target state block')
text = text.replace(state_marker, state_replacement, 1)

for expected in (
    'openFileOutput("drawer-qa-events.txt", MODE_APPEND)',
    'recordDrawerEvent(requestedOpen ? "NATIVE|REQUEST|OPEN"',
    'recordDrawerEvent("PAGE|FINISHED|" + url)',
    'recordDrawerEvent(safeMessage)',
    'NATIVE|TARGET|CLOSE',
):
    if expected not in text:
        raise SystemExit(f'Missing private QA event change: {expected}')

path.write_text(text)
print('Drawer events now persist to debug app-private storage')
