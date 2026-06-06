"""Read-only airdrop research CLI."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECTS_PATH = ROOT / "projects.json"
EVM_ADDRESS = re.compile(r"^0x[a-fA-F0-9]{40}$")


@dataclass(frozen=True)
class Eligibility:
    address: str
    transactions: int
    unique_days: int
    eligible: bool
    reasons: list[str]


def load_projects(path: Path = PROJECTS_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def estimate_cost(transactions: int, fee_usd: float) -> float:
    if transactions < 0 or fee_usd < 0:
        raise ValueError("transactions and fee_usd must be non-negative")
    return round(transactions * fee_usd, 2)


def check_eligibility(
    address: str,
    transactions: int,
    unique_days: int,
    min_transactions: int = 10,
    min_unique_days: int = 5,
) -> Eligibility:
    if not EVM_ADDRESS.fullmatch(address):
        raise ValueError("address must be a public EVM address")

    reasons: list[str] = []
    if transactions < min_transactions:
        reasons.append(f"transactions below {min_transactions}")
    if unique_days < min_unique_days:
        reasons.append(f"unique days below {min_unique_days}")
    return Eligibility(address, transactions, unique_days, not reasons, reasons)


def build_report(
    address: str,
    transactions: int,
    unique_days: int,
    fee_usd: float,
) -> dict[str, Any]:
    eligibility = check_eligibility(address, transactions, unique_days)
    return {
        "mode": "read-only",
        "eligibility": asdict(eligibility),
        "estimated_cost_usd": estimate_cost(transactions, fee_usd),
        "projects": load_projects(),
    }


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="Read-only airdrop research and cost estimator")
    commands = cli.add_subparsers(dest="command", required=True)

    commands.add_parser("scan", help="List the local project research catalog")

    cost = commands.add_parser("estimate-cost", help="Estimate activity fees")
    cost.add_argument("--transactions", type=int, required=True)
    cost.add_argument("--fee-usd", type=float, required=True)

    eligibility = commands.add_parser("check-eligibility", help="Check local threshold rules")
    eligibility.add_argument("--address", required=True)
    eligibility.add_argument("--transactions", type=int, required=True)
    eligibility.add_argument("--unique-days", type=int, required=True)

    report = commands.add_parser("report", help="Create a combined read-only report")
    report.add_argument("--address", required=True)
    report.add_argument("--transactions", type=int, required=True)
    report.add_argument("--unique-days", type=int, required=True)
    report.add_argument("--fee-usd", type=float, required=True)
    return cli


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "scan":
        result: Any = load_projects()
    elif args.command == "estimate-cost":
        result = {"estimated_cost_usd": estimate_cost(args.transactions, args.fee_usd)}
    elif args.command == "check-eligibility":
        result = asdict(check_eligibility(args.address, args.transactions, args.unique_days))
    else:
        result = build_report(args.address, args.transactions, args.unique_days, args.fee_usd)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
