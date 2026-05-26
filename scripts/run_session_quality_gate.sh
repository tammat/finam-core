#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

./scripts/run_session_edge_buckets.sh | awk '
/SESSION_EDGE / {
  session=""; ids=""; strategy=""; timeframe=""; closed=0; net=0; winrate=0;

  for (i=1; i<=NF; i++) {
    split($i, a, "=");
    if (a[1]=="session") session=a[2];
    if (a[1]=="ids") ids=a[2];
    if (a[1]=="strategy") strategy=a[2];
    if (a[1]=="timeframe") timeframe=a[2];
    if (a[1]=="closed") closed=a[2]+0;
    if (a[1]=="net") net=a[2]+0;
    if (a[1]=="winrate") winrate=a[2]+0;
  }

  if (strategy=="NA" || timeframe=="NA" || closed < 3) {
    print "EXCLUDED_PROFILE", "session=" session, "ids=" ids, "strategy=" strategy, "timeframe=" timeframe, "closed=" closed, "net=" net, "reason=insufficient_or_unclassified";
  } else if (net > 0 && winrate >= 0.45) {
    print "VALID_PROFILE", "session=" session, "ids=" ids, "strategy=" strategy, "timeframe=" timeframe, "closed=" closed, "net=" net, "winrate=" winrate;
  } else {
    print "WEAK_PROFILE", "session=" session, "ids=" ids, "strategy=" strategy, "timeframe=" timeframe, "closed=" closed, "net=" net, "winrate=" winrate;
  }
}
'
