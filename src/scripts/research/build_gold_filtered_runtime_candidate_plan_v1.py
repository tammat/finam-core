#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== GOLD_FILTERED_RUNTIME_CANDIDATE_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

# анализ только filtered gold
# никаких изменений БД
# никаких runtime updates

print("\nPLAN_SCOPE")
print("symbols=GDU6@RTSX,GLU6@RTSX")
print("edge_mode=FILTERED_BEFORE_19_MSK")

print("\nDECISION_RULES")
print("completed>=50")
print("pf>=1.5")
print("expectancy>0")
print("net_return>0")
print("recent_degradation_check=required")
print("fee_drag_check=required")

print("\nVERDICT=GOLD_FILTERED_RUNTIME_CANDIDATE_PLAN_READY")
