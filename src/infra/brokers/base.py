# src/infra/brokers/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BrokerAdapter(ABC):
    """
    Production contract for broker integration.
    Core must depend ONLY on this interface.
    """

    # -------- ACCOUNT --------

    @abstractmethod
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Return list of trading accounts"""
        pass

    @abstractmethod
    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """Return current open positions"""
        pass

    @abstractmethod
    def get_orders(self, account_id: str) -> List[Dict[str, Any]]:
        """Return active orders"""
        pass

    # -------- TRADING --------

    @abstractmethod
    def place_order(
        self,
        account_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place order and return broker response"""
        pass

    @abstractmethod
    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> Dict[str, Any]:
        """Cancel existing order"""
        pass

    # -------- MARKET DATA --------

    @abstractmethod
    def subscribe_quotes(self, symbols: List[str]) -> None:
        """Subscribe to live quotes stream"""
        pass

    @abstractmethod
    def unsubscribe_quotes(self, symbols: List[str]) -> None:
        """Unsubscribe from quotes"""
        pass

    # -------- LIFECYCLE --------

    @abstractmethod
    def start(self) -> None:
        """Initialize broker connection"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Graceful shutdown"""
        pass