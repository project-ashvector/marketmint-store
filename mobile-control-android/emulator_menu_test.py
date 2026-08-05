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
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def screenshot(name):
    path = RELEASE / name
    print('+ adb exec-out screencap -p >', path, flush=True)
    with path.open('wb') as handle:
        subprocess.run(['adb', 'exec-out', 'screencap', '-p'], check=True, stdout=handle)


def drawer_events():
    result = adb('logcat', '-d', '-v', 'brief', check=False)
    raw = result.stdout or ''
    relevant = '\n'.join(line for line in raw.splitlines() if 'MarketMintDrawer' in line)
    (RELEASE / 'drawer-log.txt').write_text(relevant + ('\n' if relevant else ''))
    events = []
    for line in relevant.splitlines():
        match = re.search(r'MarketMintDrawer(?:\([^)]*\))?\s*:\s*(.*)$', line)
        if match:
            event = match.group(1).strip()
            if event:
                events.append(event)
    return events


def wait_event(label, predicate, after=0, timeout=90):
    deadline = time.time() + timeout
    last_events = []
    while time.time() < deadline:
        events = drawer_events()
        last_events = events
        for index in range(after, len(events)):
            event = events[index]
            if predicate(event):
                print(f'PASS: {label}: {event}', flush=True)
                return event, index, events
        time.sleep(1.0)
    screenshot(f'FAIL-{label}.png')
    raise RuntimeError(f'Timed out waiting for {label}. Last events: {last_events[-30:]}')


def dump_ui(name):
    result = adb('exec-out', 'uiautomator', 'dump', '/dev/tty', check=False)
    raw = result.stdout or ''
    start = raw.find('<?xml')
    if start < 0:
        (RELEASE / f'{name}-raw.txt').write_text(raw)
        return None
    xml = raw[start:]
    (RELEASE / f'{name}.xml').write_text(xml)
    try:
        return ET.fromstring(xml)
    except ET.ParseError:
        return None


def node_center(node):
    match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
    if not match:
        raise RuntimeError(f'Invalid UI node bounds: {node.attrib}')
    x1, y1, x2, y2 = map(int, match.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def find_native_node(root, description):
    if root is None:
        return None
    for node in root.iter('node'):
        if node.attrib.get('content-desc') == description:
            return node
    return None


def dismiss_system_anr():
    root = dump_ui('system-dialog-check')
    if root is None:
        return
    wait_node = None
    for node in root.iter('node'):
        text = node.attrib.get('text', '')
        if text == 'Wait':
            wait_node = node
            break
    if wait_node is not None:
        x, y = node_center(wait_node)
        print(f'Dismissing System UI ANR with Wait at {x},{y}', flush=True)
        adb('shell', 'input', 'tap', str(x), str(y))
        time.sleep(8)


def wait_native_button(description, timeout=45):
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        dismiss_system_anr()
        root = dump_ui(f'native-{description.replace(" ", "-")}-{attempt:02d}')
        node = find_native_node(root, description)
        if node is not None:
            print(f'PASS: native target {description}: {node.attrib.get("bounds")}', flush=True)
            return node
        time.sleep(1.5)
    screenshot(f'FAIL-native-{description.replace(" ", "-")}.png')
    activity = adb('shell', 'dumpsys', 'activity', 'activities', check=False).stdout or ''
    (RELEASE / 'activity-on-native-timeout.txt').write_text(activity)
    raise RuntimeError(f'Timed out waiting for native target: {description}')


def parse_bounds_event(event):
    parts = event.split('|')
    if len(parts) < 6 or parts[0] != 'BOUNDS':
        raise ValueError(event)
    viewport_width = float(parts[1])
    viewport_height = float(parts[2])
    nodes = {}
    for item in parts[3:]:
        fields = item.split(',')
        name = fields[0]
        if len(fields) == 2 and fields[1] == 'missing':
            nodes[name] = None
        elif len(fields) == 5:
            nodes[name] = tuple(map(float, fields[1:]))
    return viewport_width, viewport_height, nodes


def wait_bounds(label, node_name, after=0, timeout=60):
    def usable(event):
        if not event.startswith('BOUNDS|'):
            return False
        try:
            _, _, nodes = parse_bounds_event(event)
        except ValueError:
            return False
        bounds = nodes.get(node_name)
        return bounds is not None and bounds[2] > 1 and bounds[3] > 1

    event, index, events = wait_event(label, usable, after=after, timeout=timeout)
    viewport_width, viewport_height, nodes = parse_bounds_event(event)
    return (viewport_width, viewport_height, nodes[node_name]), index, events


def screen_size():
    raw = adb('shell', 'wm', 'size').stdout or ''
    matches = re.findall(r'(\d+)x(\d+)', raw)
    if not matches:
        raise RuntimeError(f'Could not parse display size: {raw}')
    return tuple(map(int, matches[-1]))


def tap_css_bounds(label, viewport_width, viewport_height, bounds):
    screen_width, screen_height = screen_size()
    left, top, width, height = bounds
    x = round((left + width / 2) * screen_width / viewport_width)
    y = round((top + height / 2) * screen_height / viewport_height)
    x = max(1, min(screen_width - 2, x))
    y = max(1, min(screen_height - 2, y))
    print(f'PHYSICAL TAP {label}: Android ({x},{y})', flush=True)
    adb('shell', 'input', 'tap', str(x), str(y))


def latest_state(events, start=0):
    for event in reversed(events[start:]):
        if event in ('STATE|OPEN', 'STATE|CLOSED'):
            return event
    return None


def main():
    apk = 'mobile-build/project/app/build/outputs/apk/debug/app-debug.apk'
    adb('install', '-r', apk)
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP', check=False)
    adb('shell', 'wm', 'dismiss-keyguard', check=False)
    dismiss_system_anr()
    adb('shell', 'am', 'force-stop', PACKAGE)
    adb('logcat', '-c')

    resolved_output = adb('shell', 'cmd', 'package', 'resolve-activity', '--brief', PACKAGE).stdout or ''
    resolved_lines = [line.strip() for line in resolved_output.splitlines() if line.strip()]
    if not resolved_lines:
        raise RuntimeError(f'Could not resolve launcher activity: {resolved_output}')
    resolved = resolved_lines[-1]
    print('Resolved activity:', resolved, flush=True)
    adb(
        'shell', 'am', 'start', '-W', '-n', resolved,
        '--es', 'marketmint_qa_url', SERVER,
        '--es', 'marketmint_qa_token', TOKEN,
    )

    native_open = wait_native_button('Open navigation')
    _, page_index, _ = wait_event('page-finished', lambda event: event.startswith('PAGE|FINISHED|'))
    _, ready_index, _ = wait_event('mobile-shell-ready', lambda event: event == 'READY', after=page_index)
    screenshot('MarketMint-Mobile-v1.15.3-menu-closed.png')

    before_menu_tap = len(drawer_events())
    x, y = node_center(native_open)
    print(f'PHYSICAL TAP native hamburger: Android ({x},{y})', flush=True)
    adb('shell', 'input', 'tap', str(x), str(y))
    _, request_index, _ = wait_event(
        'native-hamburger-request', lambda event: event == 'NATIVE|REQUEST|OPEN', after=before_menu_tap
    )
    _, open_index, open_events = wait_event(
        'drawer-opened', lambda event: event in ('STATE|OPEN', 'NATIVE|RESULT|OPEN'), after=request_index
    )
    native_close = wait_native_button('Close navigation')
    if latest_state(open_events, request_index) not in (None, 'STATE|OPEN'):
        raise RuntimeError('Drawer did not remain open after native hamburger tap')

    (operations_width, operations_height, operations_bounds), _, _ = wait_bounds(
        'store-group-bounds', 'operations', after=open_index
    )
    screenshot('MarketMint-Mobile-v1.15.3-menu-open.png')

    before_group = len(drawer_events())
    tap_css_bounds('Store group', operations_width, operations_height, operations_bounds)
    _, group_index, _ = wait_event(
        'store-group-click', lambda event: event == 'NAV|GROUP', after=before_group
    )
    time.sleep(0.8)
    group_events = drawer_events()
    if any(event == 'STATE|CLOSED' for event in group_events[group_index + 1:]):
        raise RuntimeError('Drawer closed after tapping Store group')
    wait_native_button('Close navigation')
    print('PASS: drawer remained open after Store group tap', flush=True)

    (catalog_width, catalog_height, catalog_bounds), _, _ = wait_bounds(
        'catalog-destination-bounds', 'catalog', after=group_index
    )
    screenshot('MarketMint-Mobile-v1.15.3-store-group-open.png')

    before_catalog = len(drawer_events())
    tap_css_bounds('Catalog destination', catalog_width, catalog_height, catalog_bounds)
    _, destination_index, _ = wait_event(
        'catalog-click', lambda event: event == 'NAV|DESTINATION', after=before_catalog
    )
    _, closed_index, closed_events = wait_event(
        'drawer-closed', lambda event: event == 'STATE|CLOSED', after=destination_index
    )
    wait_native_button('Open navigation')
    if latest_state(closed_events, destination_index) != 'STATE|CLOSED':
        raise RuntimeError('Drawer did not remain closed after Catalog navigation')
    screenshot('MarketMint-Mobile-v1.15.3-after-catalog.png')

    crash = adb('logcat', '-b', 'crash', '-d', check=False).stdout or ''
    (RELEASE / 'crash-log.txt').write_text(crash)
    if PACKAGE in crash:
        raise RuntimeError('Crash buffer contains a MarketMint crash')

    activity = adb('shell', 'dumpsys', 'activity', 'activities', check=False).stdout or ''
    (RELEASE / 'activity.txt').write_text(activity)
    if PACKAGE not in activity:
        raise RuntimeError('MarketMint is not present in Android activity state')

    final_events = drawer_events()
    (RELEASE / 'MENU-QA-PASSED.txt').write_text(
        'MarketMint Mobile v1.15.3 Android menu QA passed:\n'
        '- mock MarketMint page finished loading\n'
        '- native Open navigation target was present\n'
        '- Android physically tapped the native hamburger\n'
        '- native bridge requested OPEN and drawer opened\n'
        '- native target changed to Close navigation\n'
        '- Store group kept drawer open\n'
        '- Catalog destination closed drawer\n'
        '- native target returned to Open navigation\n'
        '- no MarketMint package crash found\n'
        f'- final events: {final_events[-30:]}\n'
    )
    print('ALL NATIVE + WEBVIEW MENU QA CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
