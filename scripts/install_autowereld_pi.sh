#!/usr/bin/env bash
# Idempotent Pi installer. Does not enable timer or configure credentials.
set -euo pipefail
ROOT="$HOME/campervan_weekly_search"
if [[ ! -f "$ROOT/autowereld_snapshot.py" ]]; then
  echo "Clone the repository into $ROOT first" >&2
  exit 1
fi
command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "Python 3 is required" >&2; exit 1; }
mkdir -p "$ROOT/data" "$HOME/.config/systemd/user"
SERVICE="$HOME/.config/systemd/user/autowereld-rss.service"
TIMER="$HOME/.config/systemd/user/autowereld-rss.timer"
cat > "$SERVICE" <<EOF
[Unit]
Description=Collect five public AutoWereld RSS feeds
[Service]
Type=oneshot
WorkingDirectory=$ROOT
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 $ROOT/autowereld_snapshot.py --output $ROOT/data/autowereld_rss_snapshot.json
EOF
cat > "$TIMER" <<'EOF'
[Unit]
Description=Weekly AutoWereld RSS snapshot collection
[Timer]
OnCalendar=Thu *-*-* 13:30:00
Persistent=true
Unit=autowereld-rss.service
[Install]
WantedBy=timers.target
EOF
systemctl --user daemon-reload
echo "Installed service and timer (not enabled)."
echo "Test manually: systemctl --user start autowereld-rss.service"
echo "Read logs: journalctl --user -u autowereld-rss.service -n 40 --no-pager"
echo "If permitted and ready, enable: systemctl --user enable --now autowereld-rss.timer"
echo "Timer only collects locally; uploads are deliberately separate."
