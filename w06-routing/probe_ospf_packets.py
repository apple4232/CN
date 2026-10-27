"""Short diagnostic on a task-owned container interface; prints OSPF headers only."""
import json
import socket
import struct
import sys
import time

capture = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
capture.bind((sys.argv[1], 0))
capture.settimeout(0.5)
end = time.monotonic() + 12
rows = []
while time.monotonic() < end:
    try:
        data, address = capture.recvfrom(65535)
    except socket.timeout:
        continue
    if len(data) < 54 or data[12:14] != b'\x08\x00' or data[23] != 89:
        continue
    offset = 14 + (data[14] & 15) * 4
    rows.append({'source': socket.inet_ntoa(data[26:30]),
                 'destination': socket.inet_ntoa(data[30:34]),
                 'packet_type': address[2], 'ospf_type': data[offset+1],
                 'router_id': socket.inet_ntoa(data[offset+4:offset+8])})
print(json.dumps(rows, indent=2))
