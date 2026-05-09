# Finam_Core

Production-grade event-driven trading engine for Finam / MOEX.

---

# Status

LEVEL 2.5 — stable PAPER trading system

Stable branch:

```text
feature/exit-alpha-v1
```

---

# Core Principles

- Event-driven architecture
- Strategy isolation
- Centralized Risk Engine
- AI cannot send orders directly
- PostgreSQL only
- Broker reconciliation required
- Multi-stage risk gates

---

# Architecture

```text
┌────────────┐
│ MarketData │
└─────┬──────┘
      ↓
┌────────────┐
│ Strategy   │
└─────┬──────┘
      ↓
┌────────────┐
│ Signal     │
│ Router     │
└─────┬──────┘
      ↓
┌────────────┐
│ RiskStack  │
└─────┬──────┘
      ↓
┌────────────┐
│ Execution  │
│ Decision   │
└─────┬──────┘
      ↓
┌────────────┐
│ Dispatcher │
└─────┬──────┘
      ↓
┌────────────┐
│ Fill Event │
└─────┬──────┘
      ↓
┌────────────┐
│ Portfolio  │
│ Manager    │
└─────┬──────┘
      ↓
┌────────────┐
│ ExitEngine │
└────────────┘
```

---

# Main Features

- PortfolioManager
- RiskStack v2
- ExitEngine
- Replay pipeline
- Broker synchronization
- Telegram notifications
- Execution Decision Layer
- Paper execution engine
- Regime Layer
- Multi-stage risk gates

---

# Project Structure

```text
src/
├── finam_core/
│   ├── adapters/
│   ├── analytics/
│   ├── backtesting/
│   ├── config/
│   ├── core/
│   ├── data/
│   ├── events/
│   ├── execution/
│   ├── market/
│   ├── notifications/
│   ├── oms/
│   ├── pipelines/
│   ├── portfolio/
│   ├── reconciliation/
│   ├── replay/
│   ├── risk/
│   ├── storage/
│   ├── strategies/
│   └── utils/
│
├── scripts/
├── tests/
└── main.py
```

---

# Quick Start

## Clone

```bash
git clone git@github.com:tammat/finam-core.git
cd finam-core
```

---

## Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

# PAPER Run

```bash
PYTHONPATH=src \
EXECUTION_MODE=paper \
SIMULATE_MARKET=1 \
python -m src.scripts.run_market_pipeline
```

---

# Smoke Tests

```bash
bash scripts/test_forced_pipeline_risk_gate_smoke.sh
```

```bash
python -m py_compile src/finam_core/pipelines/paper_pipeline.py
```

---

# PostgreSQL

Production storage:

- PostgreSQL only

SQLite allowed only for:
- local replay
- temporary research
- isolated backtests

---

# ENV

Main env configuration:

```text
env/.env.example
```

Environment reference:

```text
docs/ENV_REFERENCE_RU.md
```

---

# Safety

- Risk layer cannot be bypassed
- Strategies cannot place orders directly
- Broker reconciliation supported
- Kill switch supported
- Portfolio exposure controlled centrally

---

# Current Stable Components

- centralized portfolio risk gate
- broker reconciliation gate
- execution decision layer
- ExitEngine stabilization
- forced pipeline smoke test
- session override log deduplication
- exit-intent direct execution path

---

# Current Limitations

- Futures REAL trading depends on broker category
- REAL execution rollout still staged
- AI layer currently advisory only

---

# Roadmap

- Multi-symbol replay pipeline
- Regime-aware execution
- Real execution OMS
- Correlation exposure engine
- ML signal ranking
- Market radar
- Advanced portfolio analytics

---

# Supported Instruments

- MOEX futures
- Brent
- Natural Gas
- USD/RUB
- Stocks
- ETFs

---

# Notifications

Telegram notifications support:

- entry signals
- exits
- trailing stop events
- risk rejects
- broker synchronization
- ExitEngine events

---

# Technology Stack

- Python 3.13
- PostgreSQL
- Finam Trade API
- Event-driven engine
- PAPER trading infrastructure

---

# RU

## Описание

Finam_Core — production-grade event-driven trading engine
для алгоритмической торговли через Finam API на MOEX.

Система ориентирована на:

- intraday trading
- swing trading
- conservative execution
- multi-asset routing
- institutional risk management

---

## Production Rules

- Только event-driven architecture
- Стратегии не могут отправлять заявки напрямую
- Все сигналы проходят через RiskStack
- PostgreSQL используется как основное production storage
- ExitEngine работает независимо от стратегии
