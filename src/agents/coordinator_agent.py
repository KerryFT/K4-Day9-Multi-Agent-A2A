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

import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
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
from src.models import CaseOutput
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
        phase_one = ("customer", "order_product", "payment", "delivery")
        with ThreadPoolExecutor(max_workers=len(phase_one)) as executor:
            futures = {
                name: executor.submit(self._run, name, order_id, case_id)
                for name in phase_one
            }
            results = {name: future.result() for name, future in futures.items()}

        # Normalize the nested/flat contracts currently returned by B/C agents.
        customer_ctx = self._section(results["customer"], "customer_context")
        affected_entities = self._section(results["order_product"], "affected_entities")
        product_ctx = self._section(results["order_product"], "product_context")
        payment_ctx = self._section(results["payment"], "payment_reconciliation")
        delivery_ctx = self._section(results["delivery"], "delivery_analysis")

        # Counts and sequences must come from raw rows. Output arrays may have
        # already been truncated and therefore cannot drive policy decisions.
        items = self.data.get_order_items(order_id)
        payments = self.data.get_order_payments(order_id)
        item_sequentials = (
            items["order_item_id"].tolist() if "order_item_id" in items.columns else []
        )
        payment_sequentials = (
            payments["payment_sequential"].tolist()
            if "payment_sequential" in payments.columns else []
        )
        payment_ids = [f"{order_id}:{seq}" for seq in payment_sequentials]
        payment_ctx["payment_ids"] = payment_ids
        seller_count = (
            int(items["seller_id"].dropna().nunique())
            if "seller_id" in items.columns else 0
        )

        # ── Phase 2: Policy Evaluation ────────────────────────────
        order_status = self.data.get_order_status(order_id)
        policy_ctx = dict(
            order_status=order_status,
            customer={"customer_context": customer_ctx},
            order_product={
                "affected_entities": affected_entities,
                "product_context": product_ctx,
            },
            payment={"payment_reconciliation": payment_ctx},
            delivery={"delivery_analysis": delivery_ctx},
            affected_entities={**affected_entities, "payment_ids": payment_ids},
            raw_items_count=len(items),
            raw_sellers_count=seller_count,
            raw_pmts_count=len(payments),
            item_sequentials=item_sequentials,
            payment_sequentials=payment_sequentials,
        )
        policy_res = self._run("policy", order_id, case_id, **policy_ctx)

        # ── Phase 3: Assemble + Verify ────────────────────────────
        output = self._assemble(
            case_id, order_id,
            customer_ctx, affected_entities, product_ctx,
            payment_ctx, delivery_ctx, policy_res,
        )

        verified = self._run(
            "verifier", order_id, case_id, draft_output=output,
        )
        if verified.get("corrected_output"):
            output = verified["corrected_output"]
        if not verified.get("valid", False):
            # Verify the corrected draft once more. Corrections such as array
            # truncation are recoverable; fabricated evidence/schema errors are not.
            verified = self._run(
                "verifier", order_id, case_id, draft_output=output,
            )
            if not verified.get("valid", False):
                raise ValueError(
                    f"Verifier rejected {case_id}: {verified.get('errors', [])}"
                )

        return CaseOutput.model_validate(output).to_json_dict()

    @staticmethod
    def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
        """Return a defensive copy of a nested section or a flat payload."""
        nested = payload.get(key)
        source = nested if isinstance(nested, dict) else payload
        return dict(source) if isinstance(source, dict) else {}

    def review_batch(self, case_summaries: list[dict[str, Any]]) -> bool:
        """Run one advisory LLM audit over the deterministic batch summary."""
        if self.llm is None:
            logger.warning("Batch LLM review skipped: no coordinator LLM configured")
            return False

        system_prompt = (
            "You audit an e-commerce dispute batch. Return one compact JSON "
            "object with keys valid, reviewed_cases, and concerns. Do not "
            "invent order facts; inspect only completeness and taxonomy."
        )
        user_message = json.dumps(
            {"policy": "EC_POLICY_V2", "cases": case_summaries},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        calls_before = self.llm_call_count
        successes_before = self.llm_success_count
        started = time.perf_counter()
        response = self._call_llm(
            system_prompt,
            user_message,
            json_mode=True,
            temperature=0.0,
            max_tokens=512,
        )
        duration_ms = (time.perf_counter() - started) * 1000

        if self.tracer is not None:
            self.tracer.log(
                case_id="BATCH_REVIEW",
                agent_name=self.agent_name,
                input_summary={"policy": "EC_POLICY_V2", "case_count": len(case_summaries)},
                output_summary={
                    "response_received": bool(response),
                    "response_chars": len(response),
                    "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest()
                    if response else None,
                },
                duration_ms=duration_ms,
                error=None if response else "LLM review returned no response",
                llm_called=self.llm_call_count > calls_before,
                llm_succeeded=self.llm_success_count > successes_before,
            )
        return bool(response)

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
        llm_calls_before = agent.llm_call_count
        llm_successes_before = agent.llm_success_count

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
                llm_called=agent.llm_call_count > llm_calls_before,
                llm_succeeded=agent.llm_success_count > llm_successes_before,
            )

        logger.debug(
            "[%s] %-14s %6.0f ms  keys=%s",
            case_id, name, elapsed_ms, sorted(result.keys()) if result else "∅",
        )
        if error_msg is not None:
            raise RuntimeError(f"{name} agent failed for {case_id}: {error_msg}")
        return result

    # ═══════════════════════════════════════════════════════════════
    #  Output Assembly — maps agent results → CaseOutput schema
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _assemble(
        case_id: str,
        order_id: str,
        customer_context: dict[str, Any],
        affected_entities: dict[str, Any],
        product_context: dict[str, Any],
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
        assessment = CoordinatorAgent._section(policy, "case_assessment")
        root_cause = CoordinatorAgent._section(policy, "root_cause_analysis")
        financial = CoordinatorAgent._section(policy, "financial_resolution")

        return {
            "case_id": case_id,

            # ── Policy-driven fields ──────────────────────────────
            "case_assessment": {
                "primary_issue":    assessment.get("primary_issue", ""),
                "secondary_issues": assessment.get("secondary_issues", []),
                "case_status":      assessment.get("case_status", "no_action"),
                "confidence":       assessment.get("confidence", 0.0),
            },

            # ── Affected entities (order_product + payment) ───────
            "affected_entities": {
                "order_ids":   affected_entities.get("order_ids", [order_id]),
                "item_ids":    affected_entities.get("item_ids", []),
                "seller_ids":  affected_entities.get("seller_ids", []),
                "payment_ids": payment.get("payment_ids", []),
            },

            # ── Customer context ──────────────────────────────────
            "customer_context": {
                "customer_unique_id": customer_context.get("customer_unique_id"),
                "related_order_ids":  customer_context.get("related_order_ids", []),
            },

            # ── Product context ───────────────────────────────────
            "product_context": {
                "product_ids":    product_context.get("product_ids", []),
                "category_names": product_context.get("category_names", []),
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
                "ranked_causes":      root_cause.get("ranked_causes", []),
                "responsible_parties": root_cause.get("responsible_parties", []),
            },

            # ── Evidence, resolution ──────────────────────────────
            "evidence_ids":      policy.get("evidence_ids", []),
            "financial_resolution": {
                "currency":              "BRL",
                "recommended_refund_brl": financial.get("recommended_refund_brl", 0.0),
            },
            "resolution_actions": policy.get("resolution_actions", []),
        }
