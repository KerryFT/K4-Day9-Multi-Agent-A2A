"""Verifier Agent — validates output against schema and business rules.

Checks evidence IDs, array limits, null handling, and data consistency.

Owner: Member C
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import LIMITS


class VerifierAgent(BaseAgent):
    """Agent responsible for output validation and correction."""

    agent_name = "verifier"

    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Validate the draft output and correct if needed.

        Expects kwargs:
        - draft_output: the assembled output dict to validate

        Returns:
            dict with:
            - valid: bool
            - errors: list of error descriptions
            - corrected_output: corrected dict (or None if valid)
        """
        draft = kwargs.get("draft_output", {})

        # TODO: Member C implements this
        # 1. Check all required fields present
        # 2. Validate evidence_id format (order:, item:, payment:, seller:, policy:)
        # 3. Enforce array limits from LIMITS
        # 4. Check confidence in [0, 1]
        # 5. Check case_status is valid
        # 6. Validate timestamp format
        # 7. Check numeric rounding
        return {
            "valid": True,
            "errors": [],
            "corrected_output": None,
        }
