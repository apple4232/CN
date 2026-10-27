"""Measure real FRR containers from inside Linux/WSL; never simulate timings."""
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
ROUTERS = ('r1', 'r2', 'r3')
REMOTE = {'r1': '10.206.63.0/29', 'r2': '10.206.61.0/29', 'r3': '10.206.62.0/29'}
BASE = {'r1': {'10.206.61.3', '10.206.62.3'},
        'r2': {'10.206.62.2', '10.206.63.3'},
        'r3': {'10.206.61.2', '10.206.63.2'}}
EXPECTED = {'baseline': BASE,
            'cut': {'r1': {'10.206.61.3'}, 'r2': {'10.206.63.3'}, 'r3': {'10.206.63.2'}},
            'cost': {'r1': {'10.206.62.3'}, 'r2': {'10.206.63.3'}, 'r3': BASE['r3']},
            'silent': {'r1': {'10.206.61.3'}, 'r2': {'10.206.63.3'}, 'r3': BASE['r3']}}


def run(args, check=True):
    result = subprocess.run(args, text=True, capture_output=True, timeout=40)
    if check and result.returncode:
        raise RuntimeError(f'{args}: {result.stderr.strip()} {result.stdout.strip()}')
    return result.stdout


def compose(*args):
    return run(['docker', 'compose', '-f', str(HERE / 'compose.yml'), *args])


def inside(router, *args, check=True):
    return run(['docker', 'exec', f'cnw06-{router}-1', *args], check=check)


def vty(router, *commands):
    arguments = [item for cmd in commands for item in ('-c', cmd)]
    return inside(router, 'vtysh', *arguments)


def routes():
    return {router: json.loads(vty(router, 'show ip route ospf json')) for router in ROUTERS}


def next_hops(table, prefix):
    entries = table.get(prefix, [])
    if isinstance(entries, dict):
        entries = [entries]
    return {nh['ip'] for entry in entries if entry.get('selected', True)
            for nh in entry.get('nexthops', [])
            if 'ip' in nh and nh.get('active', True) and nh.get('fib', True)}


def wait_for(mode, start, timeout=180):
    expected = EXPECTED[mode]
    first = None
    last_wrong = 0.0
    confirmations = 0
    observations = []
    last_print = -10
    while time.monotonic() - start < timeout:
        current = routes()
        elapsed = time.monotonic() - start
        observed = {router: next_hops(current[router], REMOTE[router]) for router in ROUTERS}
        correct = observed == expected
        observations.append({'elapsed_s': elapsed, 'correct': correct,
                             'next_hops': {r: sorted(h) for r, h in observed.items()}})
        if correct:
            first = elapsed if first is None else first
            confirmations += 1
            if confirmations >= 2:
                return {'first_correct_s': first, 'confirmed_s': elapsed,
                        'last_incorrect_s': last_wrong, 'observations': observations,
                        'final_routes': current}
        else:
            last_wrong, first, confirmations = elapsed, None, 0
        if elapsed - last_print >= 10:
            print(f'  waiting {mode}: {elapsed:.1f}s {observed}', flush=True)
            last_print = elapsed
        time.sleep(0.25)
    raise TimeoutError(f'expected {mode} next hops were not reached in {timeout}s')


def snapshot(name):
    text = []
    for router in ROUTERS:
        text += [f'===== {router} =====', vty(router, 'show ip route ospf'),
                 vty(router, 'show ip ospf neighbor')]
    (OUT / name).write_text('\n'.join(text), encoding='utf-8')


def interface(router, address):
    data = json.loads(inside(router, 'ip', '-j', '-4', 'address'))
    return next(item['ifname'] for item in data
                if any(addr.get('local') == address for addr in item['addr_info']))


def main():
    OUT.mkdir(exist_ok=True)
    result = {'started_at': datetime.now(timezone.utc).isoformat(),
              'runtime': platform.platform(), 'status': 'running', 'events': {},
              'method': 'real FRR 9.1 containers; monotonic clock; exact selected/FIB next-hop sets; two matching polls',
              'poll_sleep_s': 0.25, 'quiescent_delay_before_actions_s': 6}
    blocked = []
    multicast_rules = []
    touched_link = None
    cost_interface = None

    def save():
        (OUT / 'ospf-measurements.json').write_text(json.dumps(result, indent=2), encoding='utf-8')

    def measure(name, action, mode, output):
        time.sleep(6)  # Let the previous LSA/SPF throttles settle; excluded from timing.
        start = time.monotonic()
        action()
        action_done = time.monotonic() - start
        measurement = wait_for(mode, start)
        measurement['action_completed_s'] = action_done
        result['events'][name] = measurement
        snapshot(output)
        save()
        print(f'{name}: first correct {measurement["first_correct_s"]:.3f}s; '
              f'confirmed {measurement["confirmed_s"]:.3f}s', flush=True)

    try:
        print(compose('up', '-d'), flush=True)
        # Docker internal bridges drop even same-bridge 224.0.0.5/6 OSPF.
        # Keep Internal=true and all external isolation rules. Permit ONLY
        # protocol 89 between ports on the SAME task-created bridge/subnet.
        # No default route, external egress, published port or global policy change.
        result['network_isolation'] = []
        for name in ('cnw06_net_a', 'cnw06_net_b', 'cnw06_net_c'):
            net = json.loads(run(['docker', 'network', 'inspect', name]))[0]
            if not net['Internal'] or net['Driver'] != 'bridge':
                raise RuntimeError('refusing a lab network without internal bridge isolation')
            bridge = 'br-' + net['Id'][:12]
            subnet = net['IPAM']['Config'][0]['Subnet']
            if subnet not in ('10.206.61.0/29', '10.206.62.0/29', '10.206.63.0/29'):
                raise RuntimeError('unexpected lab subnet')
            result['network_isolation'].append({'network': name, 'internal': True, 'subnet': subnet})
            for destination in ('224.0.0.5/32', '224.0.0.6/32'):
                match = ['-i', bridge, '-o', bridge, '-s', subnet, '-d', destination,
                         '-p', '89', '-j', 'ACCEPT']
                run(['iptables', '-w', '5', '-I', 'DOCKER-USER', '1', *match])
                multicast_rules.append(match)
        result['local_ospf_multicast_rules'] = multicast_rules.copy()
        wait_for('baseline', time.monotonic())
        snapshot('route-before.txt')
        result['version'] = vty('r1', 'show version')
        result['image_digest'] = run(['docker', 'image', 'inspect', 'quay.io/frrouting/frr:9.1.0', '--format', '{{json .RepoDigests}}']).strip()
        result['interface_state_before'] = {r: json.loads(vty(r, 'show ip ospf interface json')) for r in ROUTERS}
        cut_if = interface('r1', '10.206.62.2')
        peer_if = interface('r2', '10.206.62.3')
        cost_interface = interface('r1', '10.206.61.2')
        result['interfaces'] = {'r1_to_r2': cut_if, 'r2_to_r1': peer_if, 'r1_to_r3': cost_interface}
        touched_link = cut_if
        measure('interface_down', lambda: inside('r1', 'ip', 'link', 'set', cut_if, 'down'), 'cut', 'route-after.txt')
        measure('interface_restore', lambda: inside('r1', 'ip', 'link', 'set', cut_if, 'up'), 'baseline', 'route-restored.txt')
        snapshot('route-cost-before.txt')
        measure('cost_10_to_100', lambda: vty('r1', 'configure terminal', f'interface {cost_interface}', 'ip ospf cost 100'),
                'cost', 'route-cost-after.txt')
        measure('cost_restore', lambda: vty('r1', 'configure terminal', f'interface {cost_interface}', 'ip ospf cost 10'),
                'baseline', 'route-cost-restored.txt')

        def block_hellos():
            for router, iface in [('r1', cut_if), ('r2', peer_if)]:
                inside(router, 'iptables', '-I', 'INPUT', '-i', iface, '-p', '89', '-j', 'DROP')
                blocked.append((router, iface))

        def unblock_hellos():
            while blocked:
                router, iface = blocked[-1]
                inside(router, 'iptables', '-D', 'INPUT', '-i', iface, '-p', '89', '-j', 'DROP')
                blocked.pop()

        snapshot('route-silent-before.txt')
        measure('silent_hello_loss', block_hellos, 'silent', 'route-silent-after.txt')
        measure('silent_restore', unblock_hellos, 'baseline', 'route-silent-restored.txt')
        result['status'] = 'completed'
    except Exception as exc:
        result['status'], result['error'] = 'failed', repr(exc)
        raise
    finally:
        # Restore only settings/rules on these task-owned containers, then remove them.
        for router, iface in blocked:
            inside(router, 'iptables', '-D', 'INPUT', '-i', iface, '-p', '89', '-j', 'DROP', check=False)
        if touched_link:
            inside('r1', 'ip', 'link', 'set', touched_link, 'up', check=False)
        if cost_interface:
            vty('r1', 'configure terminal', f'interface {cost_interface}', 'ip ospf cost 10')
        for match in multicast_rules:
            run(['iptables', '-w', '5', '-D', 'DOCKER-USER', *match], check=False)
        result['temporary_multicast_rules_removed'] = True
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        result['cleanup'] = compose('down')
        save()
        summary = ['Real FRR / Docker / WSL measurement; all IPs below are task-created lab addresses.',
                   f'Status: {result["status"]}',
                   'Time starts before the change command. It includes command execution and route observation latency.',
                   'Checks use the selected/FIB next hops for all three routers; route-age text is ignored.', '']
        for name, event in result['events'].items():
            summary.append(f'{name}: first_correct={event["first_correct_s"]:.6f}s; '
                           f'last_incorrect={event["last_incorrect_s"]:.6f}s; '
                           f'confirmed={event["confirmed_s"]:.6f}s; '
                           f'action_completed={event["action_completed_s"]:.6f}s')
        (OUT / 'reconverge.txt').write_text('\n'.join(summary)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
