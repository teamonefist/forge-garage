#!/bin/bash
# Gurthang Auto-Monitor — polls training status, advances phases automatically
# Run in background: nohup bash /vault/axiom/training/gurthang/monitor_gurthang.sh > /tmp/gurthang-monitor.log 2>&1 &

SCRIPT_DIR="/vault/axiom/training/gurthang"
LOG="/tmp/gurthang-monitor.log"
POLL=120  # seconds between checks

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "Gurthang Monitor started — polling every ${POLL}s"

while true; do
    STATUS_OUTPUT=$(cd "$SCRIPT_DIR" && python3 launch_gurthang.py --status 2>&1)

    # Check Phase 1
    P1_STATUS=$(echo "$STATUS_OUTPUT" | grep "^Phase 1:" | head -1)
    P2_STATUS=$(echo "$STATUS_OUTPUT" | grep "^Phase 2:" | head -1)
    P3_STATUS=$(echo "$STATUS_OUTPUT" | grep "^Phase 3:" | head -1)

    log "P1: $P1_STATUS | P2: $P2_STATUS | P3: $P3_STATUS"

    # If Phase 3 completed, we're done
    if echo "$P3_STATUS" | grep -qi "COMPLETED\|SUCCEEDED"; then
        log "ALL 3 PHASES COMPLETE — Gurthang forged!"
        STATE=$(cat "$SCRIPT_DIR/gurthang_state.json")
        FINAL_MODEL=$(echo "$STATE" | python3 -c "import sys,json; print(json.load(sys.stdin)['phases']['3'].get('output_model','unknown'))")
        log "Final model: $FINAL_MODEL"
        log "Next: python3 $SCRIPT_DIR/download_and_merge.py --all"
        exit 0
    fi

    # If Phase 3 failed, stop
    if echo "$P3_STATUS" | grep -qi "FAILED\|CANCELLED"; then
        log "Phase 3 FAILED — check Fireworks dashboard"
        exit 1
    fi

    # If Phase 2 completed and Phase 3 not started, launch Phase 3
    if echo "$P2_STATUS" | grep -qi "COMPLETED\|SUCCEEDED"; then
        if echo "$P3_STATUS" | grep -qi "NOT STARTED"; then
            log "Phase 2 done — launching Phase 3..."
            cd "$SCRIPT_DIR" && python3 launch_gurthang.py --phase 3 2>&1 | while read line; do log "  $line"; done
        fi
    fi

    # If Phase 2 failed, stop
    if echo "$P2_STATUS" | grep -qi "FAILED\|CANCELLED"; then
        log "Phase 2 FAILED — check Fireworks dashboard"
        exit 1
    fi

    # If Phase 1 completed and Phase 2 not started, launch Phase 2
    if echo "$P1_STATUS" | grep -qi "COMPLETED\|SUCCEEDED"; then
        if echo "$P2_STATUS" | grep -qi "NOT STARTED"; then
            log "Phase 1 done — launching Phase 2..."
            cd "$SCRIPT_DIR" && python3 launch_gurthang.py --phase 2 2>&1 | while read line; do log "  $line"; done
        fi
    fi

    # If Phase 1 failed, stop
    if echo "$P1_STATUS" | grep -qi "FAILED\|CANCELLED"; then
        log "Phase 1 FAILED — check Fireworks dashboard"
        exit 1
    fi

    sleep $POLL
done
