"""Coordinator Agent — orchestrates all other agents.

Receives a case, dispatches to domain agents, collects results,
and assembles the final output.

Owner: Member A
"""

import time
from typing import Any

from src.agents.base_agent import BaseAgent
from src.agents.customer_agent import CustomerAgent
from src.agents.order_product_agent import OrderProductAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.delivery_agent import DeliveryAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.verifier_agent import VerifierAgent
from src.data_loader import DataLoader
from src.llm.base_llm import BaseLLM
from src.tracer import Tracer


class CoordinatorAgent(BaseAgent):
    """Orchestrates the multi-agent pipeline for each case."""

    agent_name = "coordinator"

    def __init__(
        self,
        data_loader: DataLoader,
        llm: BaseLLM | None = None,
        agent_llms: dict[str, BaseLLM] | None = None,
        tracer: Tracer | None = None,
    ):
        super().__init__(data_loader, llm)
        self.tracer = tracer

        # Initialize all domain agents
        llms = agent_llms or {}
        self.customer_agent = CustomerAgent(data_loader, llms.get("customer"))
        self.order_product_agent = OrderProductAgent(data_loader, llms.get("order_product"))
        self.payment_agent = PaymentAgent(data_loader, llms.get("payment"))
        self.delivery_agent = DeliveryAgent(data_loader, llms.get("delivery"))
        self.policy_agent = PolicyAgent(data_loader, llms.get("policy"))
        self.verifier_agent = VerifierAgent(data_loader, llms.get("verifier"))

    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Run full investigation pipeline for a single case."""
        case_id = kwargs.get("case_id", "unknown")
        results = {}

        # Phase 1: Parallel data collection
        agents_phase1 = [
            ("customer", self.customer_agent),
            ("order_product", self.order_product_agent),
            ("payment", self.payment_agent),
            ("delivery", self.delivery_agent),
        ]

        for agent_name, agent in agents_phase1:
            start = time.time()
            result = agent.process(order_id)
            duration_ms = (time.time() - start) * 1000
            results[agent_name] = result

            if self.tracer:
                self.tracer.log_agent_call(
                    case_id=case_id,
                    agent_name=agent_name,
                    input_data={"order_id": order_id},
                    output_data=result,
                    duration_ms=duration_ms,
                )

        # Phase 2: Policy decision (needs all Phase 1 results)
        start = time.time()
        policy_result = self.policy_agent.process(order_id, **results)
        duration_ms = (time.time() - start) * 1000
        results["policy"] = policy_result

        if self.tracer:
            self.tracer.log_agent_call(
                case_id=case_id,
                agent_name="policy",
                input_data={"order_id": order_id, "context_keys": list(results.keys())},
                output_data=policy_result,
                duration_ms=duration_ms,
            )

        # Phase 3: Assemble output
        output = self._assemble_output(case_id, order_id, results)

        # Phase 4: Verify
        start = time.time()
        verified = self.verifier_agent.process(order_id, draft_output=output)
        duration_ms = (time.time() - start) * 1000

        if self.tracer:
            self.tracer.log_agent_call(
                case_id=case_id,
                agent_name="verifier",
                input_data={"order_id": order_id},
                output_data=verified,
                duration_ms=duration_ms,
            )

        # Use corrected output if verifier made changes
        if verified.get("corrected_output"):
            output = verified["corrected_output"]

        return output

    def _assemble_output(self, case_id: str, order_id: str, results: dict) -> dict:
        """Assemble the final output dict from all agent results."""
        # TODO: Implement assembly logic combining all agent results
        # This is where all handoff data gets merged into the output schema
        return {
            "case_id": case_id,
            "case_assessment": results.get("policy", {}).get("case_assessment", {}),
            "affected_entities": results.get("order_product", {}).get("affected_entities", {}),
            "customer_context": results.get("customer", {}).get("customer_context", {}),
            "product_context": results.get("order_product", {}).get("product_context", {}),
            "delivery_analysis": results.get("delivery", {}).get("delivery_analysis", {}),
            "payment_reconciliation": results.get("payment", {}).get("payment_reconciliation", {}),
            "root_cause_analysis": results.get("policy", {}).get("root_cause_analysis", {}),
            "evidence_ids": results.get("policy", {}).get("evidence_ids", []),
            "financial_resolution": results.get("policy", {}).get("financial_resolution", {}),
            "resolution_actions": results.get("policy", {}).get("resolution_actions", []),
        }
