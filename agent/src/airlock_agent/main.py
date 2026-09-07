"""CLI entrypoint: run one refund request from the terminal."""
import sys

from airlock_agent.core import run_agent


def main() -> None:
    order_id = sys.argv[1] if len(sys.argv) > 1 else "ORD-1001"
    out = run_agent(
        f"I'd like a refund for order {order_id}. Please take the appropriate action now — "
        "do not ask me to confirm."
    )
    o = out["outcome"]
    print("\n" + o["customer_message"])
    print(f"\n--- run #{out['run_id']} ---  outcome={o['final']}  "
          f"policy=v{o['policy']['version']}:{o['policy']['recommendation']}  "
          f"tools={out['tool_calls']}  tokens={out['tokens_in']}/{out['tokens_out']}  "
          f"latency_ms={out['latency_ms']}")


if __name__ == "__main__":
    main()
