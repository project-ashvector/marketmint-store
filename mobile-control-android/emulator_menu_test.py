#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import time

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
    path = RELEASE / name
    print('+ adb exec-out screencap -p >', path, flush=True)
    with path.open('wb') as handle:
        subprocess.run(['adb', 'exec-out', 'screencap', '-p'], check=True, stdout=handle)


def drawer_events():
    result = adb('logcat', '-d', '-v', 'brief', '-s', 'MarketMintDrawer:I', '*:S', check=False)
    raw = result.stdout or ''
    (RELEASE / 'drawer-log.txt').write_text(raw)
    events = []
    for line in raw.splitlines():
        if 'MarketMintDrawer' not in line:
            continue
        match = re.search(r'MarketMintDrawer(?:\([^)]*\))?\s*:\s*(.*)$', line)
        if not match:
            match = re.search(r'MarketMintDrawer\s+[A-Z]\s+(.*)$', line)
        if match:
            event = match.group(1).strip()
            if event:
                events.append(event)
    return events


def wait_event(label, predicate, after=0, timeout=120):
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
    raise RuntimeError(
        f'Timed out waiting for {label} after event index {after}. '
        f'Last drawer events: {last_events[-20:]}'
    )


def parse_bounds_event(event):
    if not event.startswith('BOUNDS|'):
        raise ValueError(f'Not a bounds event: {event}')
    parts = event.split('|')
    if len(parts) < 6:
        raise ValueError(f'Incomplete bounds event: {event}')
    viewport_width = float(parts[1])
    viewport_height = float(parts[2])
    nodes = {}
    for item in parts[3:]:
        fields = item.split(',')
        name = fields[0]
        if len(fields) == 2 and fields[1] == 'missing':
            nodes[name] = None
            continue
        if len(fields) != 5:
            raise ValueError(f'Invalid node bounds: {item}')
        left, top, width, height = map(float, fields[1:])
        nodes[name] = (left, top, width, height)
    return viewport_width, viewport_height, nodes


def wait_bounds(label, node_name, after=0, timeout=120):
    def usable(event):
        if not event.startswith('BOUNDS|'):
            return False
        try:
            _, _, nodes = parse_bounds_event(event)
        except ValueError:
            return False
        node = nodes.get(node_name)
        return node is not None and node[2] > 1 and node[3] > 1

    event, index, events = wait_event(label, usable, after=after, timeout=timeout)
    viewport_width, viewport_height, nodes = parse_bounds_event(event)
    return (viewport_width, viewport_height, nodes[node_name]), index, events


def physical_screen_size():
    raw = adb('shell', 'wm', 'size').stdout or ''
    matches = re.findall(r'(?:Physical|Override)?\s*size:\s*(\d+)x(\d+)', raw, flags=re.I)
    if not matches:
        matches = re.findall(r'(\d+)x(\d+)', raw)
    if not matches:
        raise RuntimeError(f'Could not parse Android display size: {raw}')
    width, height = map(int, matches[-1])
    print(f'Android display: {width}x{height}', flush=True)
    return width, height


def tap_css_bounds(label, viewport_width, viewport_height, bounds):
    screen_width, screen_height = physical_screen_size()
    left, top, width, height = bounds
    css_x = left + width / 2.0
    css_y = top + height / 2.0
    x = round(css_x * screen_width / viewport_width)
    y = round(css_y * screen_height / viewport_height)
    x = max(1, min(screen_width - 2, x))
    y = max(1, min(screen_height - 2, y))
    print(
        f'PHYSICAL TAP {label}: CSS ({css_x:.1f},{css_y:.1f}) '
        f'viewport {viewport_width:.0f}x{viewport_height:.0f} -> Android ({x},{y})',
        flush=True,
    )
    adb('shell', 'input', 'tap', str(x), str(y))


def latest_state(events, start=0):
    for event in reversed(events[start:]):
        if event in ('STATE|OPEN', 'STATE|CLOSED'):
            return event
    return None


def main():
    apk = 'mobile-build/project/app/build/outputs/apk/debug/app-debug.apk'
    adb('install', '-r', apk)
    adb('shell', 'am', 'force-stop', PACKAGE)
    write_preferences()
    adb('logcat', '-c')

    resolved_output = adb('shell', 'cmd', 'package', 'resolve-activity', '--brief', PACKAGE).stdout or ''
    resolved_lines = [line.strip() for line in resolved_output.splitlines() if line.strip()]
    if not resolved_lines:
        raise RuntimeError(f'Could not resolve launcher activity: {resolved_output}')
    resolved = resolved_lines[-1]
    print('Resolved activity:', resolved, flush=True)
    adb('shell', 'am', 'start', '-W', '-n', resolved)

    _, ready_index, ready_events = wait_event('mobile-shell-ready', lambda event: event == 'READY')
    (menu_viewport_width, menu_viewport_height, menu_bounds), menu_bounds_index, _ = wait_bounds(
        'menu-button-bounds', 'menu', after=ready_index
    )
    screenshot('MarketMint-Mobile-v1.15.3-menu-closed.png')

    before_menu_tap = len(drawer_events())
    tap_css_bounds('hamburger', menu_viewport_width, menu_viewport_height, menu_bounds)
    _, menu_click_index, _ = wait_event(
        'hamburger-click-received', lambda event: event == 'CLICK|MENU', after=before_menu_tap
    )
    _, open_index, open_events = wait_event(
        'drawer-opened', lambda event: event == 'STATE|OPEN', after=menu_click_index
    )
    if latest_state(open_events, menu_click_index) != 'STATE|OPEN':
        raise RuntimeError('Drawer did not remain open after hamburger tap')

    (operations_viewport_width, operations_viewport_height, operations_bounds), operations_bounds_index, _ = wait_bounds(
        'store-group-bounds', 'operations', after=open_index
    )
    screenshot('MarketMint-Mobile-v1.15.3-menu-open.png')

    before_group_tap = len(drawer_events())
    tap_css_bounds('Store group', operations_viewport_width, operations_viewport_height, operations_bounds)
    _, group_index, group_events = wait_event(
        'store-group-click-received', lambda event: event == 'NAV|GROUP', after=before_group_tap
    )
    time.sleep(0.8)
    events_after_group = drawer_events()
    if any(event == 'STATE|CLOSED' for event in events_after_group[group_index + 1:]):
        screenshot('FAIL-drawer-closed-after-store-group.png')
        raise RuntimeError('Drawer closed after tapping the Store navigation group')
    if latest_state(events_after_group, open_index) != 'STATE|OPEN':
        screenshot('FAIL-drawer-not-open-after-store-group.png')
        raise RuntimeError('Drawer was not open after tapping the Store navigation group')
    print('PASS: drawer remained open after Store group tap', flush=True)

    (catalog_viewport_width, catalog_viewport_height, catalog_bounds), catalog_bounds_index, _ = wait_bounds(
        'catalog-destination-bounds', 'catalog', after=group_index
    )
    screenshot('MarketMint-Mobile-v1.15.3-store-group-open.png')

    before_catalog_tap = len(drawer_events())
    tap_css_bounds('Catalog destination', catalog_viewport_width, catalog_viewport_height, catalog_bounds)
    _, destination_index, _ = wait_event(
        'catalog-click-received', lambda event: event == 'NAV|DESTINATION', after=before_catalog_tap
    )
    _, closed_index, closed_events = wait_event(
        'drawer-closed-after-catalog', lambda event: event == 'STATE|CLOSED', after=destination_index
    )
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
        raise RuntimeError('MarketMint is not present in the Android activity state')

    final_events = drawer_events()
    (RELEASE / 'MENU-QA-PASSED.txt').write_text(
        'MarketMint Mobile v1.15.3 physical Android menu QA passed:\n'
        '- Android physically tapped the live hamburger coordinates\n'
        '- WebView reported CLICK|MENU and STATE|OPEN\n'
        '- Android physically tapped the Store navigation group\n'
        '- WebView reported NAV|GROUP and drawer remained open\n'
        '- Android physically tapped the Catalog destination\n'
        '- WebView reported NAV|DESTINATION and STATE|CLOSED\n'
        '- no MarketMint package crash found\n'
        f'- final drawer events: {final_events[-20:]}\n'
    )
    print('ALL PHYSICAL MENU QA CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
