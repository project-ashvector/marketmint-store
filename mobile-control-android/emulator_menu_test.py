#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import time

PACKAGE = 'com.ebedesigns.marketmint.controlcenter'
TOKEN = '0123456789abcdef0123456789abcdef'
SERVER = 'http://10.0.2.2:8765'
EVENT_FILE = 'files/drawer-qa-events.txt'
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


def suppress_system_dialogs():
    commands = [
        ('settings', 'put', 'global', 'hide_error_dialogs', '1'),
        ('settings', 'put', 'global', 'anr_show_background', '0'),
        ('settings', 'put', 'global', 'show_first_crash_dialog', '0'),
        ('settings', 'put', 'global', 'show_restart_in_crash_dialog', '0'),
        ('settings', 'put', 'secure', 'anr_show_background', '0'),
        ('am', 'force-stop', 'com.android.settings'),
        ('am', 'broadcast', '-a', 'android.intent.action.CLOSE_SYSTEM_DIALOGS'),
    ]
    for command in commands:
        adb('shell', *command, check=False)


def screenshot(name):
    path = RELEASE / name
    print('+ adb exec-out screencap -p >', path, flush=True)
    with path.open('wb') as handle:
        subprocess.run(['adb', 'exec-out', 'screencap', '-p'], check=True, stdout=handle)


def clear_events():
    adb('shell', 'run-as', PACKAGE, 'rm', '-f', EVENT_FILE, check=False)


def drawer_events():
    result = adb('shell', 'run-as', PACKAGE, 'cat', EVENT_FILE, check=False)
    raw = result.stdout or ''
    events = [line.strip() for line in raw.splitlines() if line.strip()]
    (RELEASE / 'drawer-private-events.txt').write_text('\n'.join(events) + ('\n' if events else ''))
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
        time.sleep(0.8)
    screenshot(f'FAIL-{label}.png')
    raise RuntimeError(f'Timed out waiting for {label}. Last events: {last_events[-40:]}')


def screen_size():
    raw = adb('shell', 'wm', 'size').stdout or ''
    matches = re.findall(r'(\d+)x(\d+)', raw)
    if not matches:
        raise RuntimeError(f'Could not parse display size: {raw}')
    return tuple(map(int, matches[-1]))


def parse_native_bounds(event):
    parts = event.split('|')
    if len(parts) != 6 or parts[:2] != ['NATIVE', 'BOUNDS']:
        raise ValueError(event)
    left, top, width, height = map(int, parts[2:])
    if width <= 0 or height <= 0:
        raise ValueError(event)
    return left, top, width, height


def wait_native_bounds(after=0, timeout=60):
    def usable(event):
        if not event.startswith('NATIVE|BOUNDS|'):
            return False
        try:
            parse_native_bounds(event)
            return True
        except ValueError:
            return False

    event, index, events = wait_event('native-hamburger-bounds', usable, after=after, timeout=timeout)
    return parse_native_bounds(event), index, events


def tap_native_menu(bounds, after_index):
    left, top, width, height = bounds
    screen_width, screen_height = screen_size()
    x = max(2, min(screen_width - 2, left + width // 2))
    y = max(2, min(screen_height - 2, top + height // 2))
    suppress_system_dialogs()
    print(f'PHYSICAL TAP exact native hamburger bounds {bounds}: Android ({x},{y})', flush=True)
    adb('shell', 'input', 'tap', str(x), str(y))
    _, request_index, events = wait_event(
        'native-hamburger-request',
        lambda event: event == 'NATIVE|REQUEST|OPEN',
        after=after_index,
        timeout=20,
    )
    return request_index, events


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


def tap_css_bounds(label, viewport_width, viewport_height, bounds, content_origin):
    screen_width, screen_height = screen_size()
    origin_x, origin_y = content_origin
    left, top, width, height = bounds
    scale = screen_width / viewport_width if viewport_width > 0 else 1.0
    x = round(origin_x + (left + width / 2.0) * scale)
    y = round(origin_y + (top + height / 2.0) * scale)
    x = max(2, min(screen_width - 2, x))
    y = max(2, min(screen_height - 2, y))
    suppress_system_dialogs()
    print(
        f'PHYSICAL TAP {label}: CSS center ({left + width / 2.0:.1f},{top + height / 2.0:.1f}) '
        f'origin {content_origin} scale {scale:.3f} -> Android ({x},{y})',
        flush=True,
    )
    adb('shell', 'input', 'tap', str(x), str(y))


def latest_matching(events, values, start=0):
    for event in reversed(events[start:]):
        if event in values:
            return event
    return None


def main():
    apk = 'mobile-build/project/app/build/outputs/apk/debug/app-debug.apk'
    adb('install', '-r', apk)
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP', check=False)
    adb('shell', 'wm', 'dismiss-keyguard', check=False)
    suppress_system_dialogs()
    adb('shell', 'am', 'force-stop', PACKAGE)
    clear_events()

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

    _, page_index, _ = wait_event('page-finished', lambda event: event.startswith('PAGE|FINISHED|'))
    _, ready_index, _ = wait_event('mobile-shell-ready', lambda event: event == 'READY', after=page_index)
    _, target_open_index, _ = wait_event(
        'native-open-target-ready', lambda event: event == 'NATIVE|TARGET|OPEN', after=0
    )
    native_bounds, native_bounds_index, _ = wait_native_bounds(after=0)
    content_origin = (native_bounds[0], native_bounds[1])
    screenshot('MarketMint-Mobile-v1.15.3-menu-closed.png')

    before_menu_tap = len(drawer_events())
    request_index, _ = tap_native_menu(native_bounds, before_menu_tap)
    _, open_index, open_events = wait_event(
        'drawer-opened',
        lambda event: event in ('STATE|OPEN', 'NATIVE|RESULT|OPEN'),
        after=request_index,
    )
    _, close_target_index, close_target_events = wait_event(
        'native-close-target-ready', lambda event: event == 'NATIVE|TARGET|CLOSE', after=request_index
    )
    if latest_matching(close_target_events, {'NATIVE|TARGET|OPEN', 'NATIVE|TARGET|CLOSE'}, request_index) != 'NATIVE|TARGET|CLOSE':
        raise RuntimeError('Native target did not remain in Close navigation state')

    (operations_width, operations_height, operations_bounds), operations_bounds_index, _ = wait_bounds(
        'store-group-bounds', 'operations', after=open_index
    )
    screenshot('MarketMint-Mobile-v1.15.3-menu-open.png')

    before_group = len(drawer_events())
    tap_css_bounds('Store group', operations_width, operations_height, operations_bounds, content_origin)
    _, group_index, _ = wait_event('store-group-click', lambda event: event == 'NAV|GROUP', after=before_group)
    time.sleep(1.0)
    group_events = drawer_events()
    if any(event == 'STATE|CLOSED' for event in group_events[group_index + 1:]):
        screenshot('FAIL-drawer-closed-after-store-group.png')
        raise RuntimeError('Drawer closed after tapping the Store group')
    if latest_matching(group_events, {'NATIVE|TARGET|OPEN', 'NATIVE|TARGET|CLOSE'}, request_index) != 'NATIVE|TARGET|CLOSE':
        screenshot('FAIL-native-target-after-store-group.png')
        raise RuntimeError('Native menu target was not Close navigation after Store group tap')
    print('PASS: drawer remained open after Store group tap', flush=True)

    (catalog_width, catalog_height, catalog_bounds), catalog_bounds_index, _ = wait_bounds(
        'catalog-destination-bounds', 'catalog', after=group_index
    )
    screenshot('MarketMint-Mobile-v1.15.3-store-group-open.png')

    before_catalog = len(drawer_events())
    tap_css_bounds('Catalog destination', catalog_width, catalog_height, catalog_bounds, content_origin)
    _, destination_index, _ = wait_event(
        'catalog-click', lambda event: event == 'NAV|DESTINATION', after=before_catalog
    )
    _, closed_index, closed_events = wait_event(
        'drawer-closed', lambda event: event == 'STATE|CLOSED', after=destination_index
    )
    _, reopened_target_index, final_events = wait_event(
        'native-open-target-restored', lambda event: event == 'NATIVE|TARGET|OPEN', after=destination_index
    )
    if latest_matching(final_events, {'NATIVE|TARGET|OPEN', 'NATIVE|TARGET|CLOSE'}, destination_index) != 'NATIVE|TARGET|OPEN':
        raise RuntimeError('Native menu target did not return to Open navigation')
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
        '- MarketMint page finished loading\n'
        '- app-private READY event recorded\n'
        '- native Open navigation target recorded\n'
        f'- exact native bounds used: {native_bounds}\n'
        '- Android physically tapped the exact native hamburger center\n'
        '- native bridge requested OPEN and drawer opened\n'
        '- native target changed to Close navigation\n'
        '- Store group kept the drawer open\n'
        '- Catalog destination closed the drawer\n'
        '- native target returned to Open navigation\n'
        '- no MarketMint package crash found\n'
        f'- final private events: {final_events[-40:]}\n'
    )
    print('ALL EXACT-BOUNDS MENU QA CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
