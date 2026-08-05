#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

PACKAGE = 'com.ebedesigns.marketmint.controlcenter'
TOKEN = '0123456789abcdef0123456789abcdef'
SERVER = 'http://10.0.2.2:8765'
RELEASE = Path('release')
RELEASE.mkdir(exist_ok=True)


def adb(*args, check=True, capture=True):
    cmd = ['adb', *args]
    print('+', ' '.join(cmd), flush=True)
    return subprocess.run(cmd, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None)


def dump_ui(name):
    result = adb('exec-out', 'uiautomator', 'dump', '/dev/tty', check=False)
    raw = result.stdout or ''
    start = raw.find('<?xml')
    if start < 0:
        raise RuntimeError(f'UI dump did not return XML: {raw[-800:]}')
    xml = raw[start:]
    (RELEASE / f'{name}.xml').write_text(xml)
    return ET.fromstring(xml)


def bounds_center(node):
    match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
    if not match:
        raise RuntimeError(f'Invalid bounds for node: {node.attrib}')
    x1, y1, x2, y2 = map(int, match.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def find_node(root, *, desc=None, text=None, contains=None):
    for node in root.iter('node'):
        node_desc = node.attrib.get('content-desc', '')
        node_text = node.attrib.get('text', '')
        if desc is not None and node_desc == desc:
            return node
        if text is not None and node_text == text:
            return node
        if contains is not None and (contains in node_text or contains in node_desc):
            return node
    return None


def wait_node(label, timeout=45, **selector):
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            root = dump_ui(f'ui-{label}-{attempt:02d}')
            node = find_node(root, **selector)
            if node is not None:
                return node
        except Exception as exc:
            print(f'wait_node {label}: {exc}', flush=True)
        time.sleep(1.5)
    raise RuntimeError(f'Timed out waiting for {label}: {selector}')


def tap_node(node):
    x, y = bounds_center(node)
    adb('shell', 'input', 'tap', str(x), str(y))


def write_preferences():
    prefs = f'''<?xml version="1.0" encoding="utf-8" standalone="yes" ?>\n<map>\n<string name="server_url">{SERVER}</string>\n<string name="pairing_token">{TOKEN}</string>\n</map>\n'''
    local = Path('/tmp/marketmint_mobile.xml')
    local.write_text(prefs)
    adb('push', str(local), '/data/local/tmp/marketmint_mobile.xml')
    adb('shell', 'chmod', '644', '/data/local/tmp/marketmint_mobile.xml')
    adb('shell', 'run-as', PACKAGE, 'mkdir', '-p', 'shared_prefs')
    adb('shell', 'run-as', PACKAGE, 'cp', '/data/local/tmp/marketmint_mobile.xml', 'shared_prefs/marketmint_mobile.xml')
    adb('shell', 'run-as', PACKAGE, 'chmod', '600', 'shared_prefs/marketmint_mobile.xml')


def screenshot(name):
    with (RELEASE / name).open('wb') as handle:
        subprocess.run(['adb', 'exec-out', 'screencap', '-p'], check=True, stdout=handle)


def assert_desc(desc, name):
    node = wait_node(name, desc=desc)
    print(f'PASS: {desc} at {node.attrib.get("bounds")}', flush=True)
    return node


def main():
    apk = 'mobile-build/project/app/build/outputs/apk/debug/app-debug.apk'
    adb('install', '-r', apk)
    adb('shell', 'am', 'force-stop', PACKAGE)
    write_preferences()
    adb('logcat', '-c')
    resolved = adb('shell', 'cmd', 'package', 'resolve-activity', '--brief', PACKAGE).stdout.strip().splitlines()[-1]
    print('Resolved activity:', resolved, flush=True)
    adb('shell', 'am', 'start', '-W', '-n', resolved)

    open_button = assert_desc('Open navigation', 'menu-closed')
    screenshot('MarketMint-Mobile-v1.15.3-menu-closed.png')
    tap_node(open_button)

    close_button = assert_desc('Close navigation', 'menu-open')
    screenshot('MarketMint-Mobile-v1.15.3-menu-open.png')

    store = wait_node('store-group', text='Store')
    tap_node(store)
    time.sleep(1.0)
    assert_desc('Close navigation', 'menu-stays-open-after-group')
    print('PASS: drawer remains open after tapping Store group', flush=True)

    catalog = wait_node('catalog-destination', text='Catalog')
    tap_node(catalog)
    assert_desc('Open navigation', 'menu-closes-after-destination')
    screenshot('MarketMint-Mobile-v1.15.3-after-catalog.png')
    print('PASS: drawer closes after tapping Catalog destination', flush=True)

    crash = adb('logcat', '-b', 'crash', '-d', check=False).stdout or ''
    (RELEASE / 'crash-log.txt').write_text(crash)
    if PACKAGE in crash:
        raise RuntimeError('Crash buffer contains a MarketMint crash')
    activity = adb('shell', 'dumpsys', 'activity', 'activities', check=False).stdout or ''
    (RELEASE / 'activity.txt').write_text(activity)
    if PACKAGE not in activity:
        raise RuntimeError('MarketMint is not present in the activity state')
    (RELEASE / 'MENU-QA-PASSED.txt').write_text(
        'MarketMint Mobile v1.15.3 menu QA passed:\n'
        '- hamburger changed Open navigation -> Close navigation\n'
        '- Store group kept drawer open\n'
        '- Catalog destination closed drawer\n'
        '- no package crash found\n'
    )
    print('ALL MENU QA CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
