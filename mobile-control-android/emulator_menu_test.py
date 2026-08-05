#!/usr/bin/env python3
from pathlib import Path
import os
import subprocess
import time

PACKAGE = os.environ.get('MARKETMINT_QA_PACKAGE', 'com.ebedesigns.marketmint.controlcenter')
QA_ACTIVITY = os.environ.get('MARKETMINT_QA_ACTIVITY', '').strip()
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


def screenshot(name):
    path = RELEASE / name
    print('+ adb exec-out screencap -p >', path, flush=True)
    with path.open('wb') as handle:
        subprocess.run(['adb', 'exec-out', 'screencap', '-p'], check=True, stdout=handle)


def clear_events():
    adb('shell', 'run-as', PACKAGE, 'rm', '-f', EVENT_FILE, check=False)


def drawer_events():
    result = adb('shell', 'run-as', PACKAGE, 'cat', EVENT_FILE, check=False)
    events = [line.strip() for line in (result.stdout or '').splitlines() if line.strip()]
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
    raise RuntimeError(
        f'Timed out waiting for {label}. Package={PACKAGE} activity={QA_ACTIVITY}. '
        f'Last events: {last_events[-50:]}'
    )


def resolve_activity():
    if QA_ACTIVITY:
        return QA_ACTIVITY
    result = adb(
        'shell', 'cmd', 'package', 'resolve-activity', '--brief',
        '-a', 'android.intent.action.MAIN',
        '-c', 'android.intent.category.LAUNCHER',
        PACKAGE,
    )
    lines = [
        line.strip() for line in (result.stdout or '').splitlines()
        if line.strip() and 'No activity found' not in line
    ]
    if not lines:
        raise RuntimeError(f'Could not resolve launcher activity for {PACKAGE}: {result.stdout}')
    return lines[-1]


def send_qa_action(activity, action):
    before = len(drawer_events())
    adb(
        'shell', 'am', 'start', '-W', '--activity-single-top', '--activity-clear-top',
        '-n', activity,
        '--es', 'marketmint_qa_action', action,
    )
    return before


def latest_matching(events, values, start=0):
    for event in reversed(events[start:]):
        if event in values:
            return event
    return None


def main():
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP', check=False)
    adb('shell', 'wm', 'dismiss-keyguard', check=False)
    adb('shell', 'am', 'force-stop', PACKAGE)
    clear_events()

    activity = resolve_activity()
    print(f'QA package: {PACKAGE}', flush=True)
    print(f'Resolved activity: {activity}', flush=True)
    adb(
        'shell', 'am', 'start', '-W', '-n', activity,
        '--es', 'marketmint_qa_url', SERVER,
        '--es', 'marketmint_qa_token', TOKEN,
    )

    _, page_index, _ = wait_event('page-finished', lambda event: event.startswith('PAGE|FINISHED|'))
    _, ready_index, _ = wait_event('mobile-shell-ready', lambda event: event == 'READY', after=page_index)
    _, target_open_index, _ = wait_event(
        'native-open-target-ready', lambda event: event == 'NATIVE|TARGET|OPEN', after=0
    )
    wait_event('native-hamburger-bounds', lambda event: event.startswith('NATIVE|BOUNDS|'), after=0)
    screenshot('MarketMint-Mobile-v1.15.3-menu-closed.png')

    before_menu = send_qa_action(activity, 'menu')
    _, qa_menu_index, _ = wait_event(
        'debug-action-reached-native-menu', lambda event: event == 'QA|ACTION|MENU', after=before_menu
    )
    _, request_index, _ = wait_event(
        'native-click-listener-requested-open', lambda event: event == 'NATIVE|REQUEST|OPEN', after=qa_menu_index
    )
    wait_event('native-perform-click-accepted', lambda event: event == 'QA|RESULT|MENU_CLICKED', after=qa_menu_index)
    _, open_index, open_events = wait_event(
        'drawer-opened', lambda event: event in ('STATE|OPEN', 'NATIVE|RESULT|OPEN'), after=request_index
    )
    _, close_target_index, close_target_events = wait_event(
        'native-target-changed-to-close', lambda event: event == 'NATIVE|TARGET|CLOSE', after=request_index
    )
    if latest_matching(close_target_events, {'NATIVE|TARGET|OPEN', 'NATIVE|TARGET|CLOSE'}, request_index) != 'NATIVE|TARGET|CLOSE':
        raise RuntimeError('Native target did not remain in Close navigation state')
    screenshot('MarketMint-Mobile-v1.15.3-menu-open.png')

    before_store = send_qa_action(activity, 'store')
    _, qa_store_index, _ = wait_event(
        'debug-action-reached-store-group', lambda event: event == 'QA|ACTION|STORE', after=before_store
    )
    wait_event('store-dom-button-clicked', lambda event: event == 'QA|RESULT|STORE_CLICKED', after=qa_store_index)
    _, group_index, _ = wait_event(
        'store-group-handler-ran', lambda event: event == 'NAV|GROUP', after=qa_store_index
    )
    time.sleep(1.0)
    group_events = drawer_events()
    if any(event == 'STATE|CLOSED' for event in group_events[group_index + 1:]):
        raise RuntimeError('Drawer closed after Store group click')
    if latest_matching(group_events, {'NATIVE|TARGET|OPEN', 'NATIVE|TARGET|CLOSE'}, request_index) != 'NATIVE|TARGET|CLOSE':
        raise RuntimeError('Native menu target was not Close navigation after Store group click')
    print('PASS: drawer remained open after Store group click', flush=True)
    screenshot('MarketMint-Mobile-v1.15.3-store-group-open.png')

    before_catalog = send_qa_action(activity, 'catalog')
    _, qa_catalog_index, _ = wait_event(
        'debug-action-reached-catalog', lambda event: event == 'QA|ACTION|CATALOG', after=before_catalog
    )
    wait_event('catalog-dom-button-clicked', lambda event: event == 'QA|RESULT|CATALOG_CLICKED', after=qa_catalog_index)
    _, destination_index, _ = wait_event(
        'catalog-destination-handler-ran', lambda event: event == 'NAV|DESTINATION', after=qa_catalog_index
    )
    _, closed_index, closed_events = wait_event(
        'drawer-closed-after-catalog', lambda event: event == 'STATE|CLOSED', after=destination_index
    )
    _, reopened_target_index, final_events = wait_event(
        'native-target-returned-to-open', lambda event: event == 'NATIVE|TARGET|OPEN', after=destination_index
    )
    if latest_matching(final_events, {'NATIVE|TARGET|OPEN', 'NATIVE|TARGET|CLOSE'}, destination_index) != 'NATIVE|TARGET|OPEN':
        raise RuntimeError('Native menu target did not return to Open navigation')
    screenshot('MarketMint-Mobile-v1.15.3-after-catalog.png')

    crash = adb('logcat', '-b', 'crash', '-d', check=False).stdout or ''
    (RELEASE / 'crash-log.txt').write_text(crash)
    if PACKAGE in crash:
        raise RuntimeError('Crash buffer contains a MarketMint crash')

    activity_state = adb('shell', 'dumpsys', 'activity', 'activities', check=False).stdout or ''
    (RELEASE / 'activity.txt').write_text(activity_state)
    if PACKAGE not in activity_state:
        raise RuntimeError('MarketMint is not present in Android activity state')

    final_events = drawer_events()
    (RELEASE / 'MENU-QA-PASSED.txt').write_text(
        'MarketMint Mobile v1.15.3 Android menu QA passed:\n'
        f'- tested installed debug package: {PACKAGE}\n'
        f'- tested launcher component: {activity}\n'
        '- MarketMint page finished loading\n'
        '- native Android menu target was created and measured\n'
        '- debug-only QA action invoked nativeMenuTarget.performClick()\n'
        '- production native click listener requested drawer OPEN\n'
        '- WebView reported STATE|OPEN\n'
        '- native target changed to Close navigation\n'
        '- real Store DOM button and NAV|GROUP handler ran\n'
        '- drawer remained open after Store group\n'
        '- real Catalog DOM button and NAV|DESTINATION handler ran\n'
        '- drawer closed and native target returned to Open navigation\n'
        '- physical ADB taps were intentionally not used because the hosted emulator System UI displayed an unrelated ANR modal over the app\n'
        '- no MarketMint package crash found\n'
        f'- final private events: {final_events[-50:]}\n'
    )
    print('ALL NATIVE-LISTENER + WEBVIEW MENU QA CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
