#!/usr/bin/env python3
from pathlib import Path
import subprocess
import time

PACKAGE = 'com.ebedesigns.marketmint.controlcenter'
TOKEN = '0123456789abcdef0123456789abcdef'
SERVER = 'http://10.0.2.2:8765'
EVENT_FILE = 'files/drawer-qa-events.txt'
RELEASE = Path('release')
RELEASE.mkdir(exist_ok=True)

PROFILES = [
    ('compact-320', 640, 1136, 320, 320),
    ('standard-360', 720, 1280, 320, 360),
    ('large-412', 824, 1830, 320, 412),
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
        ('input', 'keyevent', 'KEYCODE_BACK'),
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
    return [line.strip() for line in (result.stdout or '').splitlines() if line.strip()]


def parse_layout(event):
    parts = event.split('|')
    if len(parts) != 7 or parts[0] != 'LAYOUT':
        raise ValueError(event)
    return {
        'viewport': int(parts[1]),
        'document': int(parts[2]),
        'body': int(parts[3]),
        'main': int(parts[4]),
        'header': int(parts[5]),
        'oversized': int(parts[6]),
    }


def wait_layout(expected_width, timeout=75):
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
        f'Timed out waiting for LAYOUT near {expected_width}px. '
        f'Last events: {last[-30:]}'
    )


def resolve_activity():
    result = adb('shell', 'cmd', 'package', 'resolve-activity', '--brief', PACKAGE)
    lines = [line.strip() for line in (result.stdout or '').splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f'Could not resolve MarketMint activity: {result.stdout}')
    return lines[-1]


def launch_profile(label, physical_width, physical_height, density, expected_css_width):
    print(f'\n=== PHONE FIT PROFILE {label} ===', flush=True)
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
        f"PASS {label}: viewport={layout['viewport']} document={layout['document']} "
        f"body={layout['body']} main={layout['main']} header={layout['header']} "
        f"oversized={layout['oversized']}",
        flush=True,
    )
    return layout, all_events


def main():
    reports = []
    try:
        for profile in PROFILES:
            label = profile[0]
            layout, all_events = launch_profile(*profile)
            reports.append((label, layout, all_events[-20:]))
    finally:
        adb('shell', 'wm', 'size', 'reset', check=False)
        adb('shell', 'wm', 'density', 'reset', check=False)

    lines = [
        'MarketMint Mobile v1.15.3 phone-fit QA passed:',
        '- tested compact 320px CSS viewport',
        '- tested standard 360px CSS viewport',
        '- tested large 412px CSS viewport',
        '- document/body/main/header stayed within every viewport',
        '- zero non-scrollable oversized elements were reported',
        '- intentionally wide tables/navigation rails remain contained in scroll wrappers',
        '',
    ]
    for label, layout, tail in reports:
        lines.append(f'{label}: {layout}')
        lines.append(f'{label} event tail: {tail}')
    (RELEASE / 'PHONE-FIT-QA-PASSED.txt').write_text('\n'.join(lines) + '\n')
    print('ALL MULTI-SIZE PHONE-FIT CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
