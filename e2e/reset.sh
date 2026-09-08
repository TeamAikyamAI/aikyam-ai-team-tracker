#!/bin/bash
# Rebuild the throwaway e2e database from nothing. Never point at a real DB.
set -e
PORT=8099
# Kill the previous instance properly. The login lockout counter lives in
# process memory, so a surviving server carries a lockout from the last run
# into this one and every login fails with 429.
fuser -k -TERM ${PORT}/tcp 2>/dev/null || true
for i in $(seq 1 15); do
  fuser -s ${PORT}/tcp 2>/dev/null || break
  sleep 1
done
if fuser -s ${PORT}/tcp 2>/dev/null; then fuser -k -KILL ${PORT}/tcp 2>/dev/null || true; sleep 2; fi
if fuser -s ${PORT}/tcp 2>/dev/null; then echo "port $PORT still busy"; exit 1; fi
su postgres -c "psql -tAc \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='tracker_test'\"" >/dev/null
su postgres -c "dropdb --if-exists tracker_test"
su postgres -c "createdb -O tracker tracker_test"
rm -rf /root/e2e/uploads && mkdir -p /root/e2e/uploads
cd /root/be/backend
set -a; . /root/testenv.sh; set +a
/root/tvenv/bin/python -m alembic upgrade head >/dev/null
/root/tvenv/bin/python /root/e2e/seed_e2e.py
setsid nohup /root/tvenv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port $PORT > /root/e2e/server.log 2>&1 < /dev/null &
for i in $(seq 1 30); do
  sleep 1
  if curl -sf -o /dev/null http://127.0.0.1:$PORT/api/health; then echo "server up"; exit 0; fi
done
echo "server did not come up"; tail -20 /root/e2e/server.log; exit 1
