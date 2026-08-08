#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

exec 9>/tmp/finam-ngu6-frozen-day-oos-monitor-v1.lock
flock -n 9 || {
    echo "MONITOR_LOCK=BUSY"
    exit 0
}

export PYTHONPATH=/opt/finam-core/src
export PYTHONDONTWRITEBYTECODE=1

output_file="$(mktemp /tmp/ngu6-oos-monitor.XXXXXX)"
message_file="$(mktemp /tmp/ngu6-oos-telegram.XXXXXX)"

cleanup() {
    rm -f "$output_file" "$message_file"
}
trap cleanup EXIT

set +e

/opt/finam-core/venv/bin/python \
    /opt/finam-core/scripts/research/run_ngu6_frozen_day_oos_monitor_v1.py \
    2>&1 | tee "$output_file"

monitor_rc=${PIPESTATUS[0]}

set -e

verdict="$(
    grep '^VERDICT=' "$output_file" \
    | tail -1 \
    | cut -d= -f2- \
    || true
)"

dataset_rows="$(
    grep '^DATASET_ROWS=' "$output_file" \
    | tail -1 \
    | cut -d= -f2- \
    || true
)"

dataset_last="$(
    grep '^DATASET_LAST=' "$output_file" \
    | tail -1 \
    | cut -d= -f2- \
    || true
)"

new_trades="$(
    grep '^NEW_COMPLETED_DAY_TRADES=' "$output_file" \
    | tail -1 \
    | cut -d= -f2- \
    || true
)"

case "$monitor_rc" in

    0)
        if [ "$verdict" != "NO_NEW_FROZEN_DAY_TRADES" ]; then
            echo "ERROR: exit=0 with unexpected verdict=$verdict"
            exit 1
        fi

        echo "TELEGRAM_SENT=NO"
        echo "WRAPPER_VERDICT=HEALTHY_NO_EVENT"
        exit 0
        ;;

    2)
        if [ "$verdict" != "NEW_FROZEN_DAY_INVENTORY_READY" ]; then
            echo "ERROR: exit=2 with unexpected verdict=$verdict"
            exit 1
        fi

        freeze_output="$(
            /opt/finam-core/venv/bin/python \
                /opt/finam-core/scripts/research/freeze_ngu6_frozen_day_oos_inventory_v1.py \
                "$output_file"
        )"

        printf '%s\n' "$freeze_output"

        freeze_status="$(
            printf '%s\n' "$freeze_output" \
            | grep '^FREEZE_STATUS=' \
            | tail -1 \
            | cut -d= -f2-
        )"

        freeze_sha="$(
            printf '%s\n' "$freeze_output" \
            | grep '^FREEZE_SHA256=' \
            | tail -1 \
            | cut -d= -f2-
        )"

        freeze_path="$(
            printf '%s\n' "$freeze_output" \
            | grep '^FREEZE_PATH=' \
            | tail -1 \
            | cut -d= -f2-
        )"

        if [ "$freeze_status" = "ALREADY_FROZEN" ]; then
            echo "TELEGRAM_SENT=NO"
            echo "WRAPPER_VERDICT=OOS_INVENTORY_ALREADY_FROZEN"
            exit 0
        fi

        if [ "$freeze_status" != "CREATED" ]; then
            echo "ERROR: unexpected freeze status=$freeze_status"
            exit 1
        fi

        {
            echo "FINAM CORE — OOS EVENT"
            echo
            echo "NGU6@RTSX M5"
            echo "New frozen DAY inventory detected"
            echo
            echo "Dataset rows: ${dataset_rows:-UNKNOWN}"
            echo "Dataset last: ${dataset_last:-UNKNOWN}"
            echo "New completed DAY trades: ${new_trades:-UNKNOWN}"
            echo
            grep '^TRADE_IDENTITY=' "$output_file" \
                | sed 's/^TRADE_IDENTITY=/Trade: /'
            echo
            echo "Inventory frozen: YES"
            echo "Freeze SHA256: ${freeze_sha}"
            echo "Freeze artifact: ${freeze_path}"
            echo "PnL revealed: NO"
            echo "Strategy changed: NO"
            echo "Parameter search: NO"
            echo
            echo "Status: NEW_FROZEN_DAY_INVENTORY_READY"
        } > "$message_file"

        /opt/finam-core/venv/bin/python \
            /opt/finam-core/scripts/research/notify_ngu6_frozen_day_oos_event_v1.py \
            "$message_file"

        echo "WRAPPER_VERDICT=OOS_EVENT_NOTIFIED"

        # exit 2 is a research event, not a systemd failure.
        exit 0
        ;;

    *)
        {
            echo "FINAM CORE — OOS MONITOR ERROR"
            echo
            echo "NGU6@RTSX M5"
            echo "Monitor stopped fail-closed"
            echo
            echo "Exit code: $monitor_rc"
            echo "Dataset rows: ${dataset_rows:-UNKNOWN}"
            echo "Dataset last: ${dataset_last:-UNKNOWN}"
            echo "PnL revealed: NO"
            echo "Strategy changed: NO"
            echo "Parameter search: NO"
            echo
            echo "Last monitor output:"
            tail -20 "$output_file"
        } > "$message_file"

        set +e
        /opt/finam-core/venv/bin/python \
            /opt/finam-core/scripts/research/notify_ngu6_frozen_day_oos_event_v1.py \
            "$message_file"
        telegram_rc=$?
        set -e

        echo "MONITOR_FAIL_CLOSED=YES"
        echo "TELEGRAM_NOTIFY_EXIT=$telegram_rc"

        exit "$monitor_rc"
        ;;
esac
