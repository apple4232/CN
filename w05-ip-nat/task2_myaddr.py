#!/usr/bin/env python3
"""Week 5 · Task 2 — Where exactly are you on the internet?

Textbook §4.3.2 (addressing, DHCP) and §4.3.3 (NAT).

This is the hands-on task. It asks what address your machine has, what address
the rest of the world sees, and why those two are usually different.

    python3 task2_myaddr.py --collect     # gather what your OS will tell you
    python3 task2_myaddr.py --report      # your analysis

Raw measurements are archived outside Git; out/ receives a redacted summary.

Run it on **two networks**. Campus Wi-Fi and phone tethering behave differently
here, and the difference is the lesson.
"""
import argparse, json, os, platform, subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, str(Path(HERE).parent))
from network_privacy import append_private_address, public_address_record


def sh(*cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or str(result.returncode))
        return result.stdout
    except Exception as e:
        return f"<failed: {e}>"


def local_facts():
    """Raw output only. Reading it is your job, not this script's."""
    osname = platform.system()
    if osname == "Darwin":
        return {"os": osname,
                "ifconfig": sh("ifconfig"),
                "route": sh("route", "-n", "get", "default"),
                "dns": sh("scutil", "--dns")}
    if osname == "Linux":
        return {"os": osname,
                "ip_addr": sh("ip", "addr"),
                "ip_route": sh("ip", "route"),
                "dns": sh("cat", "/etc/resolv.conf")}
    return {"os": osname,
            "ipconfig": sh("ipconfig", "/all"),
            "route": sh("route", "print")}


def public_address():
    """What a server on the outside says your address is."""
    from task1_forward import address_int
    out = sh("curl", "-4", "--fail", "-sS", "--max-time", "10",
             "https://api.ipify.org").strip()
    address_int(out)  # Reject error text instead of storing it as an IP.
    return out


def collect(label):
    os.makedirs(OUT, exist_ok=True)
    record = {"label": label, "local": local_facts(), "public": public_address(),
              "when": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")}
    private_path = append_private_address(record)
    path = os.path.join(OUT, "addresses.json")
    all_records = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            all_records = json.load(f)
    all_records.append(public_address_record(record, len(all_records) + 1))
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)
    os.replace(path + ".tmp", path)
    print("  Measurement collected; literal public IP withheld from console/public output.")
    print(f"  private original -> {private_path}")
    print(f"  -> out/addresses.json  ({len(all_records)} record(s))")
    print("\n  Read the private original for task2.md; publish only a redacted summary.")


def report():
    path = os.path.join(OUT, "report.md")
    if not os.path.exists(path):
        raise SystemExit("Write out/report.md from your real measurements first.")
    with open(path, encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--collect", metavar="LABEL",
                   help='where you are, e.g. "campus wifi"')
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    if a.collect:
        collect(a.collect)
    elif a.report:
        report()
    else:
        p.print_help()
