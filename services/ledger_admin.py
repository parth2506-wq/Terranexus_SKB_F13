"""Admin-only CLI helper for CarbonKarma ledger inspection and export."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import config
from services.ledger_service import read_ledger_entries, verify_chain


def _format_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "index": entry.get("index"),
        "timestamp": entry.get("timestamp"),
        "hash": entry.get("hash"),
        "prev_hash": entry.get("prev_hash"),
        "proof_hash": entry.get("proof_hash"),
    }


def _load_entries(path: str) -> List[Dict[str, Any]]:
    entries = read_ledger_entries(path)
    for index, entry in enumerate(entries):
        entry["index"] = index
    return entries


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _list_entries(entries: List[Dict[str, Any]], count: int) -> None:
    if not entries:
        print("No ledger entries found.")
        return

    latest = entries[-count:]
    for entry in latest:
        summary = _format_entry(entry)
        print(f"[{summary['index']}] {summary['timestamp']} | hash={summary['hash']}\n" \
              f"      prev_hash={summary['prev_hash']} proof_hash={summary['proof_hash']}")


def _show_entry(entries: List[Dict[str, Any]], index: int) -> None:
    if not entries:
        raise SystemExit("No ledger entries found.")
    if index < 0 or index >= len(entries):
        raise SystemExit(f"Entry index {index} is out of range.")
    _print_json(entries[index])


def _export_entries(entries: List[Dict[str, Any]], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2, ensure_ascii=False)
    print(f"Ledger exported to {output_path}")


def _verify_path(path: str) -> None:
    if path != config.LEDGER_PATH:
        raise SystemExit("Ledger verification only supports the configured ledger path.")
    result = verify_chain()
    _print_json(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CarbonKarma ledger admin helper (local inspection/export only)."
    )
    parser.add_argument(
        "--ledger-path",
        default=config.LEDGER_PATH,
        help="Path to the local ledger file.",
    )
    parser.add_argument(
        "--list",
        type=int,
        metavar="N",
        help="List the latest N ledger entries.",
    )
    parser.add_argument(
        "--show",
        type=int,
        metavar="INDEX",
        help="Show a single ledger entry by index.",
    )
    parser.add_argument(
        "--export",
        metavar="OUTPUT",
        help="Export the ledger entries to a JSON file.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the ledger chain integrity and signatures.",
    )
    args = parser.parse_args()

    entries = _load_entries(args.ledger_path)

    if args.verify:
        _verify_path(args.ledger_path)
        return

    if args.list is not None:
        _list_entries(entries, args.list)
        return

    if args.show is not None:
        _show_entry(entries, args.show)
        return

    if args.export:
        _export_entries(entries, args.export)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
