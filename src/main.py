"""
Main entry point — runs the multi-agent pipeline for all input cases.

Usage::

    # From project root
    python -m src.main

Owner: Member A
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

from src.config import INPUT_DIR, OUTPUT_DIR, AGENT_MODELS, AGENT_PROVIDERS
from src.data_loader import DataLoader
from src.llm import create_llm
from src.models import CaseInput
from src.tracer import Tracer
from src.agents.coordinator_agent import CoordinatorAgent
from src.utils.formatter import format_output, save_output

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Setup
# ═══════════════════════════════════════════════════════════════════════

def setup_logging() -> None:
    """Configure root logger with a clean format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-5s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Silence noisy third-party loggers
    for name in ("openai", "httpx", "httpcore", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)


def load_case(path: Path) -> CaseInput:
    """Parse and validate one input JSON."""
    with open(path, "r", encoding="utf-8") as fh:
        return CaseInput(**json.load(fh))


def init_llms() -> dict[str, object]:
    """Create an LLM client for every agent defined in config.

    Returns a dict ``{agent_name: BaseLLM | None}``.
    """
    llms: dict = {}
    for name in AGENT_MODELS:
        try:
            llms[name] = create_llm(name)
            logger.info(
                "  LLM  %-14s  model=%-25s  provider=%s",
                name, AGENT_MODELS[name], AGENT_PROVIDERS[name],
            )
        except Exception as exc:
            logger.warning("  LLM  %-14s  FAILED: %s", name, exc)
            llms[name] = None
    return llms


# ═══════════════════════════════════════════════════════════════════════
#  Pipeline
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    """Load data → init LLMs → process 50 cases → save outputs + trace."""
    setup_logging()

    logger.info("=" * 60)
    logger.info("Multi-Agent E-commerce Dispute Resolution System")
    logger.info("=" * 60)

    # ── 1. Load CSV datasets ──────────────────────────────────────
    logger.info("[1/4] Loading Olist datasets ...")
    t0 = time.perf_counter()
    data_loader = DataLoader().load()
    logger.info(
        "       Loaded in %.1fs  (%d orders, %d items, %d payments)",
        time.perf_counter() - t0,
        len(data_loader.orders),
        len(data_loader.order_items),
        len(data_loader.order_payments),
    )

    # ── 2. Initialise LLM clients ────────────────────────────────
    logger.info("[2/4] Initialising LLM clients ...")
    agent_llms = init_llms()

    # ── 3. Build coordinator + tracer ─────────────────────────────
    tracer = Tracer()
    coordinator = CoordinatorAgent(
        data_loader=data_loader,
        llm=agent_llms.get("coordinator"),
        agent_llms=agent_llms,
        tracer=tracer,
    )

    # ── 4. Process cases ──────────────────────────────────────────
    case_files = sorted(INPUT_DIR.glob("EC_*.json"))
    total = len(case_files)
    logger.info("[3/4] Processing %d cases ...", total)

    if total == 0:
        logger.warning("       No input files found in %s", INPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ok_count = 0
    fail_count = 0

    for idx, case_path in enumerate(case_files, 1):
        case_input = load_case(case_path)
        case_id = case_input.case_id
        order_id = case_input.customer_request.claimed_order_id

        t_case = time.perf_counter()
        try:
            output = coordinator.process(order_id, case_id=case_id)
            output = format_output(output)
            save_output(case_id, output)
            elapsed = time.perf_counter() - t_case
            logger.info(
                "  [%02d/%d]  %s  OK   %.1fs  primary=%s",
                idx, total, case_id, elapsed,
                output.get("case_assessment", {}).get("primary_issue", "?"),
            )
            ok_count += 1
        except Exception as exc:
            elapsed = time.perf_counter() - t_case
            logger.error(
                "  [%02d/%d]  %s  FAIL %.1fs  %s",
                idx, total, case_id, elapsed, exc,
            )
            fail_count += 1

    # ── 5. Persist trace + metadata ───────────────────────────────
    logger.info("[4/4] Saving trace and metadata ...")
    trace_path = tracer.save_trace()
    meta_path = tracer.save_metadata()
    logger.info("       trace.jsonl   -> %s  (%d entries)", trace_path, tracer.num_entries)
    logger.info("       metadata.json -> %s", meta_path)

    # ── Summary ───────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(
        "DONE   %d OK  |  %d FAIL  |  %d total",
        ok_count, fail_count, total,
    )
    logger.info("=" * 60)

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
