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

aapt2="${ANDROID_HOME}/build-tools/35.0.0/aapt2"
test -x "$aapt2"
"$aapt2" dump badging "$apk" > release/DEBUG-PACKAGE-METADATA.txt

debug_package=$(sed -n "s/^package: name='\([^']*\)'.*/\1/p" release/DEBUG-PACKAGE-METADATA.txt | head -n 1)
debug_activity=$(sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p" release/DEBUG-PACKAGE-METADATA.txt | head -n 1)

test -n "$debug_package"
test -n "$debug_activity"
case "$debug_activity" in
  .*) debug_activity="${debug_package}${debug_activity}" ;;
  *.*) : ;;
  *) debug_activity="${debug_package}.${debug_activity}" ;;
esac
debug_component="${debug_package}/${debug_activity}"

cat > release/DEBUG-PACKAGE.env <<EOF
MARKETMINT_QA_PACKAGE=${debug_package}
MARKETMINT_QA_ACTIVITY=${debug_component}
EOF

printf 'Debug package: %s\nDebug activity: %s\nDebug component: %s\n' \
  "$debug_package" "$debug_activity" "$debug_component" \
  | tee release/RESOLVED-ACTIVITY.txt

adb install -r "$apk"
adb shell pm path "$debug_package" | tee -a release/RESOLVED-ACTIVITY.txt
grep -q '^package:' release/RESOLVED-ACTIVITY.txt

export MARKETMINT_QA_PACKAGE="$debug_package"
export MARKETMINT_QA_ACTIVITY="$debug_component"

python3 mobile-control-android/emulator_phone_fit_test.py
python3 mobile-control-android/emulator_menu_test.py
