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

PROFILES = [
    ('compact-320', 640, 1136, 320, 320, 2.0),
    ('standard-360', 720, 1280, 320, 360, 2.0),
    ('large-412', 824, 1830, 320, 412, 2.0),
]


def adb(*args, check=True):
    cmd = ['adb', *args]
    print('+', ' '.join(cmd), flush=True)
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def suppress_system_dialogs():
    for command in (
        ('settings', 'put', 'global', 'hide_error_dialogs', '1'),
        ('settings', 'put', 'global', 'anr_show_background', '0'),
        ('settings', 'put', 'global', 'show_first_crash_dialog', '0'),
        ('settings', 'put', 'global', 'show_restart_in_crash_dialog', '0'),
        ('am', 'force-stop', 'com.android.settings'),
    ):
        adb('shell', *command, check=False)


def screenshot(name):
    path = RELEASE / name
    print('+ adb exec-out screencap -p >', path, flush=True)
    with path.open('wb') as handle:
        subprocess.run(['adb', 'exec-out', 'screencap', '-p'], check=True, stdout=handle)


def clear_events():
    adb('shell', 'run-as', PACKAGE, 'rm', '-f', EVENT_FILE, check=False)


def events():
    result = adb('shell', 'run-as', PACKAGE, 'cat', EVENT_FILE, check=False)
    values = [line.strip() for line in (result.stdout or '').splitlines() if line.strip()]
    (RELEASE / 'phone-fit-private-events.txt').write_text('\n'.join(values) + ('\n' if values else ''))
    return values


def parse_layout(event):
    parts = event.split('|')
    if len(parts) != 8 or parts[0] != 'LAYOUT':
        raise ValueError(event)
    return {
        'viewport': int(parts[1]),
        'document': int(parts[2]),
        'body': int(parts[3]),
        'main': int(parts[4]),
        'header': int(parts[5]),
        'oversized': int(parts[6]),
        'dpr': float(parts[7]),
    }


def wait_layout(expected_width, timeout=90):
    deadline = time.time() + timeout
    last = []
    while time.time() < deadline:
        last = events()
        for event in reversed(last):
            if not event.startswith('LAYOUT|'):
                continue
            try:
                layout = parse_layout(event)
            except ValueError:
                continue
            if abs(layout['viewport'] - expected_width) <= 8:
                return layout, last
        time.sleep(0.8)
    raise RuntimeError(
        f'Timed out waiting for true mobile LAYOUT near {expected_width}px. '
        f'Package={PACKAGE} activity={QA_ACTIVITY}. Last events: {last[-40:]}'
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
        raise RuntimeError(f'Could not resolve MarketMint activity for {PACKAGE}: {result.stdout}')
    return lines[-1]


def launch_profile(label, physical_width, physical_height, density, expected_css_width, expected_dpr):
    print(f'\n=== PHONE FIT PROFILE {label} ===', flush=True)
    print(f'QA package={PACKAGE} activity={resolve_activity()}', flush=True)
    adb('shell', 'wm', 'size', f'{physical_width}x{physical_height}')
    adb('shell', 'wm', 'density', str(density))
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP', check=False)
    adb('shell', 'wm', 'dismiss-keyguard', check=False)
    suppress_system_dialogs()
    adb('shell', 'am', 'force-stop', PACKAGE)
    clear_events()

    activity = resolve_activity()
    adb(
        'shell', 'am', 'start', '-W', '-n', activity,
        '--es', 'marketmint_qa_url', SERVER,
        '--es', 'marketmint_qa_token', TOKEN,
    )

    layout, all_events = wait_layout(expected_css_width)
    screenshot(f'MarketMint-Mobile-v1.15.3-phone-fit-{label}.png')

    tolerance = 2
    failures = []
    if abs(layout['viewport'] - expected_css_width) > 8:
        failures.append(f"viewport {layout['viewport']} was not near expected {expected_css_width}")
    if abs(layout['dpr'] - expected_dpr) > 0.15:
        failures.append(f"devicePixelRatio {layout['dpr']} was not near expected {expected_dpr}")
    if layout['document'] > layout['viewport'] + tolerance:
        failures.append(f"document {layout['document']} > viewport {layout['viewport']}")
    if layout['body'] > layout['viewport'] + tolerance:
        failures.append(f"body {layout['body']} > viewport {layout['viewport']}")
    if layout['main'] > layout['viewport'] + tolerance:
        failures.append(f"main {layout['main']} > viewport {layout['viewport']}")
    if layout['header'] > layout['viewport'] + tolerance:
        failures.append(f"header {layout['header']} > viewport {layout['viewport']}")
    if layout['oversized'] != 0:
        failures.append(f"{layout['oversized']} non-scrollable element(s) exceeded viewport")

    if failures:
        raise RuntimeError(f'{label} phone-fit failed: ' + '; '.join(failures))

    print(
        f"PASS {label}: viewport={layout['viewport']} dpr={layout['dpr']} "
        f"document={layout['document']} body={layout['body']} main={layout['main']} "
        f"header={layout['header']} oversized={layout['oversized']}",
        flush=True,
    )
    return layout, all_events


def main():
    reports = []
    try:
        for profile in PROFILES:
            label = profile[0]
            layout, all_events = launch_profile(*profile)
            reports.append((label, layout, all_events[-25:]))
    finally:
        adb('shell', 'wm', 'size', 'reset', check=False)
        adb('shell', 'wm', 'density', 'reset', check=False)

    lines = [
        'MarketMint Mobile v1.15.3 phone-fit QA passed:',
        f'- tested installed debug package: {PACKAGE}',
        f'- tested launcher component: {resolve_activity()}',
        '- WebView used true logical phone CSS widths instead of physical-pixel desktop widths',
        '- tested compact 320px CSS viewport at DPR 2.0',
        '- tested standard 360px CSS viewport at DPR 2.0',
        '- tested large 412px CSS viewport at DPR 2.0',
        '- document/body/main/header stayed within every viewport',
        '- zero non-scrollable oversized elements were reported',
        '- intentionally wide tables/navigation rails remain contained in scroll wrappers',
        '',
    ]
    for label, layout, tail in reports:
        lines.append(f'{label}: {layout}')
        lines.append(f'{label} event tail: {tail}')
    (RELEASE / 'PHONE-FIT-QA-PASSED.txt').write_text('\n'.join(lines) + '\n')
    print('ALL TRUE-MOBILE MULTI-SIZE PHONE-FIT CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
