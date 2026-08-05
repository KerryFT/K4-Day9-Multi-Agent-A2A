"""Delivery Agent — analyzes delivery timing and seller handoff.

Calculates delivery_variance_hours and handoff_variance_hours
for each seller in the order.

Owner: Member B
"""

from typing import Any

import pandas as pd

from src.agents.base_agent import BaseAgent
from src.config import DECIMAL_PLACES


def _parse_dt(val: Any) -> pd.Timestamp | None:
    if pd.isna(val) or not val or str(val).strip() == "":
        return None
    try:
        dt = pd.to_datetime(val)
        return dt if not pd.isna(dt) else None
    except Exception:
        return None


def _format_dt(dt: pd.Timestamp | None) -> str | None:
    if dt is None or pd.isna(dt):
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class DeliveryAgent(BaseAgent):
    """Agent responsible for delivery and handoff analysis."""

    agent_name = "delivery"

    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Analyze delivery timing and seller handoffs.

        Returns:
            dict with 'delivery_analysis' key containing:
            - delivered_at, estimated_delivery_at, carrier_handoff_at
            - delivery_variance_hours
            - seller_handoff_analysis (per seller)
            - late_handoff_seller_ids
        """
        order = self.data.get_order(order_id)
        if order is None:
            return {
                "delivery_analysis": {
                    "delivered_at": None,
                    "estimated_delivery_at": None,
                    "carrier_handoff_at": None,
                    "delivery_variance_hours": None,
                    "seller_handoff_analysis": [],
                    "late_handoff_seller_ids": [],
                }
            }

        delivered_dt = _parse_dt(order.get("order_delivered_customer_date"))
        estimated_dt = _parse_dt(order.get("order_estimated_delivery_date"))
        carrier_dt = _parse_dt(order.get("order_delivered_carrier_date"))

        # delivery_variance_hours = delivered_at - estimated_delivery_at
        delivery_variance_hours = None
        if delivered_dt is not None and estimated_dt is not None:
            diff_sec = (delivered_dt - estimated_dt).total_seconds()
            delivery_variance_hours = round(diff_sec / 3600.0, DECIMAL_PLACES)

        items_df = self.data.get_order_items(order_id)
        seller_handoff_analysis: list[dict[str, Any]] = []
        late_handoff_seller_ids: list[str] = []

        if not items_df.empty and "seller_id" in items_df.columns:
            # Preserve seller order
            unique_sellers: list[str] = []
            for s_id in items_df["seller_id"].dropna():
                s_id_str = str(s_id)
                if s_id_str not in unique_sellers:
                    unique_sellers.append(s_id_str)

            for s_id_str in unique_sellers:
                s_items = items_df[items_df["seller_id"] == s_id_str]
                shipping_limits = s_items["shipping_limit_date"].dropna()

                ship_limit_dt = None
                if not shipping_limits.empty:
                    parsed_limits = [_parse_dt(l) for l in shipping_limits]
                    valid_limits = [l for l in parsed_limits if l is not None]
                    if valid_limits:
                        ship_limit_dt = min(valid_limits)

                handoff_variance_hours = None
                late_handoff = False

                if carrier_dt is not None and ship_limit_dt is not None:
                    diff_sec = (carrier_dt - ship_limit_dt).total_seconds()
                    handoff_variance_hours = round(diff_sec / 3600.0, DECIMAL_PLACES)
                    late_handoff = bool(carrier_dt > ship_limit_dt)

                if late_handoff:
                    late_handoff_seller_ids.append(s_id_str)

                seller_handoff_analysis.append(
                    {
                        "seller_id": s_id_str,
                        "shipping_limit_at": _format_dt(ship_limit_dt),
                        "handoff_variance_hours": handoff_variance_hours,
                        "late_handoff": late_handoff,
                    }
                )

        return {
            "delivery_analysis": {
                "delivered_at": _format_dt(delivered_dt),
                "estimated_delivery_at": _format_dt(estimated_dt),
                "carrier_handoff_at": _format_dt(carrier_dt),
                "delivery_variance_hours": delivery_variance_hours,
                "seller_handoff_analysis": seller_handoff_analysis,
                "late_handoff_seller_ids": late_handoff_seller_ids,
            }
        }
