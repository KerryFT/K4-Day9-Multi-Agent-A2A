"""End-to-end contract tests for the A10 integration boundary."""

from __future__ import annotations

import json

import pytest

from src.agents.coordinator_agent import CoordinatorAgent
from src.config import INPUT_DIR
from src.data_loader import DataLoader
from src.models import CaseInput, CaseOutput


@pytest.fixture(scope="module")
def pipeline() -> tuple[DataLoader, CoordinatorAgent]:
    data = DataLoader().load()
    return data, CoordinatorAgent(data_loader=data)


def _expected_primary(data: DataLoader, order_id: str, output: CaseOutput) -> str:
    status = data.get_order_status(order_id)
    payment_total = output.payment_reconciliation.payment_total_brl or 0.0
    variance = output.delivery_analysis.delivery_variance_hours
    late_sellers = output.delivery_analysis.late_handoff_seller_ids
    payment_rows = data.get_order_payments(order_id)

    if status == "canceled" and payment_total > 0:
        return "canceled_order_paid"
    if status == "unavailable" and payment_total > 0:
        return "unavailable_order_paid"
    if variance is not None and variance > 0 and late_sellers:
        return "late_delivery_seller"
    if variance is not None and variance > 0:
        return "late_delivery_logistics"
    if len(payment_rows) >= 2 and output.payment_reconciliation.reconciled is True:
        return "valid_split_payment"
    return "unsupported_late_claim"


def test_all_submission_cases_cross_agent_contracts(
    pipeline: tuple[DataLoader, CoordinatorAgent],
) -> None:
    """Every input traverses collection, policy, verification, and schema gates."""
    data, coordinator = pipeline
    case_paths = sorted(INPUT_DIR.glob("EC_*.json"))
    assert len(case_paths) == 50

    for path in case_paths:
        case = CaseInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
        order_id = case.customer_request.claimed_order_id
        raw = coordinator.process(order_id, case_id=case.case_id)
        output = CaseOutput.model_validate(raw)

        items = data.get_order_items(order_id)
        payments = data.get_order_payments(order_id)
        assert output.case_assessment.primary_issue == _expected_primary(
            data, order_id, output
        )
        assert output.affected_entities.order_ids == [order_id]
        assert len(output.affected_entities.item_ids) == min(len(items), 5)
        assert len(output.affected_entities.payment_ids) == min(len(payments), 5)
        assert f"order:{order_id}" in output.evidence_ids
        assert output.root_cause_analysis.ranked_causes


def test_phase_one_agent_failure_is_not_silently_persisted(
    pipeline: tuple[DataLoader, CoordinatorAgent], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A critical handoff failure must fail the case instead of fabricating data."""
    _, coordinator = pipeline
    case_path = sorted(INPUT_DIR.glob("EC_*.json"))[0]
    case = CaseInput.model_validate_json(case_path.read_text(encoding="utf-8"))

    def fail(*args: object, **kwargs: object) -> dict:
        raise ValueError("synthetic failure")

    monkeypatch.setattr(coordinator._agents["customer"], "process", fail)
    with pytest.raises(RuntimeError, match="customer agent failed"):
        coordinator.process(
            case.customer_request.claimed_order_id,
            case_id=case.case_id,
        )
