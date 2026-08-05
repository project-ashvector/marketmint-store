#!/bin/sh
set -eu

mkdir -p release
python3 mobile-control-android/mock_marketmint_server.py > release/mock-server.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT INT TERM

ready=0
attempt=1
while [ "$attempt" -le 30 ]; do
  if curl -fsS http://127.0.0.1:8765/api/mobile-control/ping | grep -q '"ok": true'; then
    ready=1
    break
  fi
  sleep 1
  attempt=$((attempt + 1))
done

if [ "$ready" -ne 1 ]; then
  echo 'Mock MarketMint server failed to start' >&2
  exit 1
fi

apk='mobile-build/project/app/build/outputs/apk/debug/app-debug.apk'
test -f "$apk"
adb install -r "$apk"
adb shell cmd package resolve-activity --brief com.ebedesigns.marketmint.controlcenter \
  | tee release/RESOLVED-ACTIVITY.txt
grep -v 'No activity found' release/RESOLVED-ACTIVITY.txt | grep -q '/'

python3 mobile-control-android/emulator_phone_fit_test.py
python3 mobile-control-android/emulator_menu_test.py
