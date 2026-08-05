"""
Coordinator Agent — the multi-agent pipeline orchestrator.

Execution flow
--------------
::

    ┌──────────────────────────────────────────────────────────┐
    │  Phase 1 — Data Collection  (independent, parallelisable)│
    │    customer_agent   → customer_context                   │
    │    order_product    → entities + product_context          │
    │    payment_agent    → reconciliation + payment_ids        │
    │    delivery_agent   → delivery_analysis                   │
    ├──────────────────────────────────────────────────────────┤
    │  Phase 2 — Policy Evaluation  (depends on Phase 1)       │
    │    policy_agent     → assessment, root cause, resolution  │
    ├──────────────────────────────────────────────────────────┤
    │  Phase 3 — Verification  (depends on Phase 2)            │
    │    verifier_agent   → validate & correct final output    │
    └──────────────────────────────────────────────────────────┘

Owner: Member A
"""

from __future__ import annotations

import logging
import time
from typing import Any

from src.agents.base_agent import BaseAgent
from src.agents.customer_agent import CustomerAgent
from src.agents.delivery_agent import DeliveryAgent
from src.agents.order_product_agent import OrderProductAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.verifier_agent import VerifierAgent
from src.data_loader import DataLoader
from src.llm.base_llm import BaseLLM
from src.tracer import Tracer

logger = logging.getLogger(__name__)


class CoordinatorAgent(BaseAgent):
    """Orchestrates the full investigation pipeline for each case."""

    agent_name = "coordinator"

    def __init__(
        self,
        data_loader: DataLoader,
        llm: BaseLLM | None = None,
        agent_llms: dict[str, BaseLLM | None] | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        super().__init__(data_loader, llm)
        self.tracer = tracer

        # Instantiate every domain agent once; they share the DataLoader.
        llms = agent_llms or {}
        self._agents: dict[str, BaseAgent] = {
            "customer":      CustomerAgent(data_loader, llms.get("customer")),
            "order_product": OrderProductAgent(data_loader, llms.get("order_product")),
            "payment":       PaymentAgent(data_loader, llms.get("payment")),
            "delivery":      DeliveryAgent(data_loader, llms.get("delivery")),
            "policy":        PolicyAgent(data_loader, llms.get("policy")),
            "verifier":      VerifierAgent(data_loader, llms.get("verifier")),
        }

    # ═══════════════════════════════════════════════════════════════
    #  Public API
    # ═══════════════════════════════════════════════════════════════

    def process(self, order_id: str, **kwargs: Any) -> dict[str, Any]:
        """Run the full investigation and return a CaseOutput-shaped dict."""
        case_id: str = kwargs.get("case_id", "unknown")

        # ── Phase 1: Data Collection (independent) ────────────────
        customer_res = self._run("customer", order_id, case_id)
        order_res    = self._run("order_product", order_id, case_id)
        payment_res  = self._run("payment", order_id, case_id)
        delivery_res = self._run("delivery", order_id, case_id)

        # ── Phase 2: Policy Evaluation ────────────────────────────
        order_status = self.data.get_order_status(order_id)
        policy_ctx = dict(
            order_status=order_status,
            customer=customer_res,
            order_product=order_res,
            payment=payment_res,
            delivery=delivery_res,
        )
        policy_res = self._run("policy", order_id, case_id, **policy_ctx)

        # ── Phase 3: Assemble + Verify ────────────────────────────
        output = self._assemble(
            case_id, order_id,
            customer_res, order_res, payment_res, delivery_res, policy_res,
        )

        verified = self._run(
            "verifier", order_id, case_id, draft_output=output,
        )
        if verified.get("corrected_output"):
            output = verified["corrected_output"]

        return output

    # ═══════════════════════════════════════════════════════════════
    #  Agent Runner (timing + tracing + error-safety)
    # ═══════════════════════════════════════════════════════════════

    def _run(
        self,
        name: str,
        order_id: str,
        case_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute one agent with timing, tracing, and error isolation."""
        agent = self._agents[name]
        error_msg: str | None = None

        t0 = time.perf_counter()
        try:
            result = agent.process(order_id, **kwargs)
        except Exception as exc:
            logger.error("[%s] %s agent failed: %s", case_id, name, exc)
            result = {}
            error_msg = str(exc)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Trace
        if self.tracer is not None:
            self.tracer.log(
                case_id=case_id,
                agent_name=name,
                input_summary={"order_id": order_id, **{k: type(v).__name__ for k, v in kwargs.items()}},
                output_summary=result,
                duration_ms=elapsed_ms,
                error=error_msg,
            )

        logger.debug(
            "[%s] %-14s %6.0f ms  keys=%s",
            case_id, name, elapsed_ms, sorted(result.keys()) if result else "∅",
        )
        return result

    # ═══════════════════════════════════════════════════════════════
    #  Output Assembly — maps agent results → CaseOutput schema
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _assemble(
        case_id: str,
        order_id: str,
        customer: dict[str, Any],
        order_product: dict[str, Any],
        payment: dict[str, Any],
        delivery: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge all agent results into the final CaseOutput dict.

        Field mapping
        -------------
        - ``case_assessment``       ← policy
        - ``affected_entities``     ← order_product (orders, items, sellers)
                                      + payment (payment_ids)
        - ``customer_context``      ← customer
        - ``product_context``       ← order_product
        - ``delivery_analysis``     ← delivery
        - ``payment_reconciliation``← payment
        - ``root_cause_analysis``   ← policy
        - ``evidence_ids``          ← policy
        - ``financial_resolution``  ← policy
        - ``resolution_actions``    ← policy
        """
        return {
            "case_id": case_id,

            # ── Policy-driven fields ──────────────────────────────
            "case_assessment": {
                "primary_issue":    policy.get("primary_issue", ""),
                "secondary_issues": policy.get("secondary_issues", []),
                "case_status":      policy.get("case_status", "no_action"),
                "confidence":       policy.get("confidence", 0.0),
            },

            # ── Affected entities (order_product + payment) ───────
            "affected_entities": {
                "order_ids":   order_product.get("order_ids", [order_id]),
                "item_ids":    order_product.get("item_ids", []),
                "seller_ids":  order_product.get("seller_ids", []),
                "payment_ids": payment.get("payment_ids", []),
            },

            # ── Customer context ──────────────────────────────────
            "customer_context": {
                "customer_unique_id": customer.get("customer_unique_id"),
                "related_order_ids":  customer.get("related_order_ids", []),
            },

            # ── Product context ───────────────────────────────────
            "product_context": {
                "product_ids":    order_product.get("product_ids", []),
                "category_names": order_product.get("category_names", []),
            },

            # ── Delivery analysis ─────────────────────────────────
            "delivery_analysis": {
                "delivered_at":            delivery.get("delivered_at"),
                "estimated_delivery_at":   delivery.get("estimated_delivery_at"),
                "carrier_handoff_at":      delivery.get("carrier_handoff_at"),
                "delivery_variance_hours": delivery.get("delivery_variance_hours"),
                "seller_handoff_analysis": delivery.get("seller_handoff_analysis", []),
                "late_handoff_seller_ids": delivery.get("late_handoff_seller_ids", []),
            },

            # ── Payment reconciliation ────────────────────────────
            "payment_reconciliation": {
                "currency":          "BRL",
                "item_total_brl":    payment.get("item_total_brl"),
                "freight_total_brl": payment.get("freight_total_brl"),
                "expected_total_brl": payment.get("expected_total_brl"),
                "payment_total_brl": payment.get("payment_total_brl"),
                "difference_brl":    payment.get("difference_brl"),
                "reconciled":        payment.get("reconciled"),
                "payment_types":     payment.get("payment_types", []),
            },

            # ── Root cause analysis ───────────────────────────────
            "root_cause_analysis": {
                "ranked_causes":      policy.get("ranked_causes", []),
                "responsible_parties": policy.get("responsible_parties", []),
            },

            # ── Evidence, resolution ──────────────────────────────
            "evidence_ids":      policy.get("evidence_ids", []),
            "financial_resolution": {
                "currency":              "BRL",
                "recommended_refund_brl": policy.get("recommended_refund_brl", 0.0),
            },
            "resolution_actions": policy.get("resolution_actions", []),
        }
