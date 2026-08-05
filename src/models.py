"""
Pydantic v2 models for input/output schema validation.

Mirrors the exact JSON structures from README §3 (input) and §6 (output).
Timestamps are kept as plain strings (CSV format "YYYY-MM-DD HH:MM:SS").

Owner: Member A
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════════════
# INPUT SCHEMA  (README §3)
# ═══════════════════════════════════════════════════════════════════════

class CustomerRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: str
    message: str
    claimed_order_id: str


class InvestigationScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    include_customer_history: bool
    include_product_context: bool


class CaseInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    customer_request: CustomerRequest
    investigation_scope: InvestigationScope
    policy_version: str


# ═══════════════════════════════════════════════════════════════════════
# OUTPUT SCHEMA  (README §6)
# ═══════════════════════════════════════════════════════════════════════

class CaseAssessment(BaseModel):
    primary_issue: str
    secondary_issues: list[str] = Field(default_factory=list)
    case_status: str  # "action_required" | "no_action"
    confidence: float = Field(ge=0.0, le=1.0)


class AffectedEntities(BaseModel):
    order_ids: list[str] = Field(default_factory=list)
    item_ids: list[str] = Field(default_factory=list)
    seller_ids: list[str] = Field(default_factory=list)
    payment_ids: list[str] = Field(default_factory=list)


class CustomerContext(BaseModel):
    customer_unique_id: Optional[str] = None
    related_order_ids: list[str] = Field(default_factory=list)


class ProductContext(BaseModel):
    product_ids: list[str] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)


class SellerHandoffAnalysis(BaseModel):
    seller_id: str
    shipping_limit_at: Optional[str] = None
    handoff_variance_hours: Optional[float] = None
    late_handoff: bool = False


class DeliveryAnalysis(BaseModel):
    delivered_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    carrier_handoff_at: Optional[str] = None
    delivery_variance_hours: Optional[float] = None
    seller_handoff_analysis: list[SellerHandoffAnalysis] = Field(default_factory=list)
    late_handoff_seller_ids: list[str] = Field(default_factory=list)


class PaymentReconciliation(BaseModel):
    currency: str = "BRL"
    item_total_brl: Optional[float] = None
    freight_total_brl: Optional[float] = None
    expected_total_brl: Optional[float] = None
    payment_total_brl: Optional[float] = None
    difference_brl: Optional[float] = None
    reconciled: Optional[bool] = None
    payment_types: list[str] = Field(default_factory=list)


class RankedCause(BaseModel):
    cause_code: str
    rank: int


class ResponsibleParty(BaseModel):
    party_type: str
    party_id: str


class RootCauseAnalysis(BaseModel):
    ranked_causes: list[RankedCause] = Field(default_factory=list)
    responsible_parties: list[ResponsibleParty] = Field(default_factory=list)


class FinancialResolution(BaseModel):
    currency: str = "BRL"
    recommended_refund_brl: float = 0.0


class CaseOutput(BaseModel):
    """Top-level output for one case.  Serialises to the exact JSON required."""

    case_id: str
    case_assessment: CaseAssessment
    affected_entities: AffectedEntities
    customer_context: CustomerContext
    product_context: ProductContext
    delivery_analysis: DeliveryAnalysis
    payment_reconciliation: PaymentReconciliation
    root_cause_analysis: RootCauseAnalysis
    evidence_ids: list[str] = Field(default_factory=list)
    financial_resolution: FinancialResolution
    resolution_actions: list[str] = Field(default_factory=list)

    def to_json_dict(self) -> dict:
        """Plain dict ready for ``json.dump``."""
        return self.model_dump(mode="python")
