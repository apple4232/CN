"""Real Windows traceroutes, with intermediate addresses kept outside Git."""
from datetime import datetime, timezone
import argparse
import ipaddress
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
PRIVATE = HERE.parent.parent / 'private-network-records' / 'collected' / 'w06-routing'
TARGETS = [('domestic', 'www.korea.ac.kr'), ('overseas-site', 'www.stanford.edu'),
           ('anycast', '1.1.1.1'), ('additional-overseas-probe', 'gaia.cs.umass.edu')]


def main(reanalyze=False):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    records, text = [], ['Local Windows PC; home/personal network (confirmed by user).',
                         'Real tracert -d -h 30 -w 300 output; intermediate IP addresses replaced by stable hop labels.',
                         'Hop numbers, RTTs, timeout markers, and public destination addresses are unchanged.',
                         'Raw evidence remains outside the repository. Labels do not encode IP addresses.', '']
    labels = {}
    for kind, target in TARGETS:
        print(f'Tracing {kind}: {target}', flush=True)
        filename = f'{kind}.txt'
        if reanalyze:
            data = (PRIVATE / filename).read_bytes()
            returncode = None
        else:
            result = subprocess.run(['tracert', '-d', '-h', '30', '-w', '300', target], capture_output=True)
            data = result.stdout + result.stderr
            returncode = result.returncode
            (PRIVATE / filename).write_bytes(data)
        raw = data.decode('utf-8', errors='replace')
        if '\ufffd' in raw:
            raw = data.decode('cp949', errors='replace')
        header = re.split(r'(?m)^\s*1\s', raw)[0]
        destination_match = re.search(r'\[(\d+\.\d+\.\d+\.\d+)\]', header)
        destination = destination_match.group(1) if destination_match else (target if kind == 'anycast' else None)
        hops, public_lines = [], []
        for line in raw.splitlines():
            match = re.match(r'^\s*(\d+)\s+', line)
            if not match:
                continue
            ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', line)
            hop = {'hop': int(match.group(1)), 'rtt_ms': [int(value) for value in re.findall(r'<?\s*(\d+)\s*ms', line)],
                   'stars': line.count('*'), 'destination': destination in ips if destination else False}
            for ip in ips:
                if ip != destination:
                    label = labels.setdefault(ip, f'path-node-{len(labels)+1:02d}')
                    hop['node'] = label
                    hop['scope'] = 'private' if ipaddress.ip_address(ip).is_private else 'public'
                    line = line.replace(ip, f'[{label}]')
            hops.append(hop)
            public_lines.append(line)
        destination_hops = [hop['hop'] for hop in hops if hop['destination']]
        record = {'kind': kind, 'target': target, 'destination': destination,
                  'collected_at': datetime.fromtimestamp((PRIVATE / filename).stat().st_mtime, timezone.utc).isoformat(),
                  'returncode': returncode, 'destination_address_observed': bool(destination_hops),
                  'first_destination_hop': min(destination_hops) if destination_hops else None,
                  'repeated_destination_at_multiple_ttls': len(destination_hops) > 1,
                  'reached': len(destination_hops) == 1, 'hops': hops}
        records.append(record)
        text += [f'=== {kind}: {target} (destination {destination or "unresolved"}) ===', *public_lines, '']
        (OUT / 'traceroute.txt').write_text('\n'.join(text)+'\n', encoding='utf-8')
        (OUT / 'traceroute-summary.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
        print(f'{target}: {len(hops)} hops observed, destination reached={record["reached"]}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reanalyze', action='store_true')
    main(parser.parse_args().reanalyze)
