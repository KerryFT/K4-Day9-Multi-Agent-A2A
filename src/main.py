"""Main entry point — runs the multi-agent pipeline for all 50 cases.

Usage:
    python -m src.main

Owner: Member A
"""

import json
import time
from pathlib import Path

from src.config import (
    INPUT_DIR, OUTPUT_DIR, LOGGING_DIR,
    AGENT_MODELS, AGENT_PROVIDERS, LLM_PROVIDERS,
)
from src.data_loader import DataLoader
from src.models import CaseInput
from src.tracer import Tracer
from src.agents.coordinator_agent import CoordinatorAgent
from src.llm.local_llm import LocalLLM
from src.llm.api_llm import ApiLLM
from src.utils.formatter import save_output, format_output


def create_llm_client(agent_name: str):
    """Create the appropriate LLM client for an agent."""
    model = AGENT_MODELS[agent_name]
    provider_name = AGENT_PROVIDERS[agent_name]
    provider = LLM_PROVIDERS[provider_name]

    if provider_name == "local":
        return LocalLLM(
            model_name=model,
            base_url=provider["base_url"],
            api_key=provider["api_key"],
        )
    else:
        return ApiLLM(
            model_name=model,
            base_url=provider["base_url"],
            api_key=provider["api_key"],
        )


def load_case(case_path: Path) -> CaseInput:
    """Load and validate a case input JSON."""
    with open(case_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return CaseInput(**data)


def main():
    """Run the full pipeline."""
    print("=" * 60)
    print("Multi-Agent E-commerce Dispute Resolution System")
    print("=" * 60)

    # Initialize
    print("\n[1/4] Loading data...")
    data_loader = DataLoader().load()
    tracer = Tracer()

    # Create LLM clients for each agent
    print("[2/4] Initializing LLM clients...")
    agent_llms = {}
    for agent_name in AGENT_MODELS:
        try:
            agent_llms[agent_name] = create_llm_client(agent_name)
            print(f"  ✓ {agent_name}: {AGENT_MODELS[agent_name]} ({AGENT_PROVIDERS[agent_name]})")
        except Exception as e:
            print(f"  ✗ {agent_name}: Failed - {e}")
            agent_llms[agent_name] = None

    # Initialize coordinator
    coordinator = CoordinatorAgent(
        data_loader=data_loader,
        llm=agent_llms.get("coordinator"),
        agent_llms=agent_llms,
        tracer=tracer,
    )

    # Process all cases
    print("\n[3/4] Processing cases...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    case_files = sorted(INPUT_DIR.glob("EC_*.json"))
    total = len(case_files)
    print(f"  Found {total} cases\n")

    for i, case_path in enumerate(case_files, 1):
        case_input = load_case(case_path)
        case_id = case_input.case_id
        order_id = case_input.customer_request.claimed_order_id

        print(f"  [{i:02d}/{total}] {case_id} (order: {order_id[:12]}...)")

        start = time.time()
        try:
            output = coordinator.process(order_id, case_id=case_id)
            output = format_output(output)
            save_output(case_id, output)
            elapsed = time.time() - start
            print(f"         ✓ Done in {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"         ✗ Error in {elapsed:.1f}s: {e}")

    # Save trace and metadata
    print("\n[4/4] Saving trace and metadata...")
    tracer.save_trace()
    tracer.save_metadata()
    print(f"  ✓ trace.jsonl: {LOGGING_DIR / 'trace.jsonl'}")
    print(f"  ✓ metadata.json: {LOGGING_DIR / 'metadata.json'}")

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
