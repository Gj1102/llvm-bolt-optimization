#!/usr/bin/env bash
set -euo pipefail
uptime
if [[ -d /tmp/bolt-small-layout && ! -e /home/gj/bolt-course-4794 ]]; then
  mv /tmp/bolt-small-layout /home/gj/bolt-course-4794
fi
du -sh /home/gj/bolt-course-4794 2>/dev/null || true
cat /etc/wsl.conf
