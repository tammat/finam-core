class RiskEngine:
    """
    RiskEngine 2.1
    Adds Portfolio Heat Control
    """

    def __init__(
        self,
        position_manager=None,
        portfolio_manager=None,
        max_position_pct=None,
        max_gross_exposure_pct=None,
        max_portfolio_heat=None,
        correlation_matrix=None,
        rules=None,
        max_drawdown_pct: float | None = None,
        max_daily_loss_pct: float | None = None,
        **kwargs,
    ):
        self.position_manager = position_manager
        self.portfolio_manager = portfolio_manager
        self.max_drawdown_pct = max_drawdown_pct
        self.max_position_pct = max_position_pct
        self.max_gross_exposure_pct = max_gross_exposure_pct
        self.max_portfolio_heat = max_portfolio_heat
        self.correlation_matrix = correlation_matrix or {}
        self.max_daily_loss_pct = max_daily_loss_pct
        self.rules = rules or []
        self.is_frozen = False
        self.freeze_date = None
        self.base_risk_multiplier = 1.0
        self.current_risk_multiplier = 1.0
        # ---------------------------------
        # Internal equity tracking (HWM)
        # ---------------------------------
        self.equity_high_watermark = None
        self.current_drawdown = 0.0

    def evaluate(self, signal=None, context=None):
        from datetime import datetime

        # ---------------------------------
        # Daily reset logic
        # ---------------------------------
        today = datetime.utcnow().date()
        if self.freeze_date and self.freeze_date != today:
            self.is_frozen = False
            self.freeze_date = None

        # ---------------------------------
        # Internal High-Water Mark tracking
        # ---------------------------------
        if context is not None and hasattr(context, "equity"):
            equity = context.equity

            if self.equity_high_watermark is None:
                # Attempt to reconstruct initial capital if possible
                realized = getattr(context, "realized_pnl", 0.0)
                unrealized = getattr(context, "unrealized_pnl", 0.0)
                reconstructed_peak = equity - realized - unrealized
                self.equity_high_watermark = max(equity, reconstructed_peak)

            if equity > self.equity_high_watermark:
                self.equity_high_watermark = equity

            if self.equity_high_watermark:
                self.current_drawdown = (
                    equity - self.equity_high_watermark
                ) / self.equity_high_watermark
            else:
                self.current_drawdown = 0.0

        # ---------------------------------
        # Freeze state guard
        # ---------------------------------
        if self.is_frozen:
            return None

        # ---------------------------------
        # Daily loss guard
        # ---------------------------------
        if self.max_daily_loss_pct is not None and context is not None:
            daily_dd = getattr(context, "daily_drawdown", None)
            if daily_dd is not None and daily_dd <= -abs(self.max_daily_loss_pct):
                self.is_frozen = True
                from datetime import datetime
                self.freeze_date = datetime.utcnow().date()
                return None

        # ---------------------------------
        # Global drawdown guard
        # ---------------------------------
        if self.max_drawdown_pct is not None and context is not None:
            dd = self.current_drawdown
            # Adaptive scaling logic
            if dd is not None:
                abs_dd = abs(dd)
                if abs_dd >= 0.15:
                    self.current_risk_multiplier = 0.0
                elif abs_dd >= 0.10:
                    self.current_risk_multiplier = 0.4
                elif abs_dd >= 0.05:
                    self.current_risk_multiplier = 0.7
                else:
                    self.current_risk_multiplier = 1.0
            if dd is not None and dd <= -abs(self.max_drawdown_pct):
                self.is_frozen = True
                from datetime import datetime
                self.freeze_date = datetime.utcnow().date()
                return None

        # ---------------------------------
        # Position size limit
        # ---------------------------------
        if self.max_position_pct is not None and context is not None and signal is not None:
            raw_notional = abs(getattr(signal, "qty", 0)) * abs(getattr(signal, "price", 0))
            notional = raw_notional * self.current_risk_multiplier
            if context.equity and notional / context.equity > self.max_position_pct:
                return None

        # ---------------------------------
        # Gross exposure limit
        # ---------------------------------
        if self.max_gross_exposure_pct is not None and context is not None and signal is not None:
            current_exposure = getattr(context, "gross_exposure", 0)
            new_notional = abs(getattr(signal, "qty", 0)) * abs(getattr(signal, "price", 0))
            if context.equity and (current_exposure + new_notional) / context.equity > self.max_gross_exposure_pct:
                return None

        # ---------------------------------
        # Portfolio heat limit
        # ---------------------------------
        if self.max_portfolio_heat is not None and context is not None and signal is not None:
            current_heat = getattr(context, "portfolio_heat", 0)
            atr = getattr(signal, "atr", None)
            if atr:
                additional_heat = abs(signal.qty) * atr
            else:
                additional_heat = abs(signal.qty) * abs(signal.price)
            if (current_heat + additional_heat) > self.max_portfolio_heat:
                return None

        # ---------------------------------
        # Correlation block
        # ---------------------------------
        if self.correlation_matrix and context is not None and signal is not None:
            correlated = self.correlation_matrix.get(signal.symbol, {})
            for sym, corr in correlated.items():
                pos = context.positions.get(sym)
                if pos and abs(getattr(pos, "qty", 0)) > 0 and abs(corr) >= 0.8:
                    return None

        return signal