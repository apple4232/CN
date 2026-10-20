"""Keep personal network measurements outside the submission checkout."""
import json
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent


def private_output_dir(week):
    if week not in {"w03-dns", "w05-ip-nat"}:
        raise ValueError("Unsupported private measurement folder")
    folder = REPOSITORY.parent / "private-network-records" / "collected" / week
    if folder.resolve().is_relative_to(REPOSITORY):
        raise ValueError("Raw measurements must remain outside the Git checkout")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def append_private_address(record):
    path = private_output_dir("w05-ip-nat") / "addresses.json"
    records = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    records.append(record)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)
    return path


def public_address_record(record, index):
    """Do not copy raw outputs, IPs, SSIDs, or host/device identifiers."""
    return {
        "label": f"network-{index}",
        "when": record.get("when"),
        "local": {"os": record["local"].get("os"),
                  "raw_output": "[WITHHELD: local private archive]"},
        "public": "[REDACTED_PUBLIC_IPV4]",
        "privacy": {"redacted": True,
                    "note": "Original addresses and labels are stored outside Git; this is a public summary."},
    }
