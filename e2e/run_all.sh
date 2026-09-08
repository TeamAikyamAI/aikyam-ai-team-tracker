#!/bin/bash
# Full acceptance run: rebuild the throwaway instance, then both suites.
set -o pipefail
echo "=== rebuilding the test instance ==="
/root/e2e/reset.sh || exit 1
echo
echo "=== API suite ==="
cd /root/e2e && /root/tvenv/bin/python -m pytest -q -p no:cacheprovider; API=$?
echo
echo "=== browser suite ==="
cd /root/e2e/ui && node run.mjs; UI=$?
echo
echo "=== unit suite (SQLite, in-process) ==="
cd /root/be/backend && /root/tvenv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -2; UNIT=$?
echo
echo "api=$API ui=$UI unit=$UNIT"
[ $API -eq 0 ] && [ $UI -eq 0 ] && [ $UNIT -eq 0 ] && echo "ALL GREEN" || echo "SOMETHING FAILED"
