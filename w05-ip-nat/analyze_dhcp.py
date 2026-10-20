"""Extract DHCP messages from the official Ethernet/IPv4 pcapng trace."""
import hashlib
import json
import socket
import struct
from pathlib import Path

OUT = Path(__file__).parent / "out"


def analyze(path):
    raw = path.read_bytes()
    offset = number = 0
    endian = "<"
    links = []
    rows = []
    names = {1: "Discover", 2: "Offer", 3: "Request", 5: "Ack",
             6: "Nak", 7: "Release", 8: "Inform"}
    while offset < len(raw):
        if raw[offset:offset + 4] == b"\x0a\x0d\x0d\x0a":
            endian = "<" if raw[offset + 8:offset + 12] == b"\x4d\x3c\x2b\x1a" else ">"
            links = []
        kind, size = struct.unpack_from(endian + "II", raw, offset)
        if size < 12 or offset + size > len(raw):
            raise ValueError("Invalid pcapng block")
        assert struct.unpack_from(endian + "I", raw, offset + size - 4)[0] == size
        body = raw[offset + 8:offset + size - 4]
        if kind == 1:
            links.append(struct.unpack_from(endian + "H", body)[0])
        if kind == 6:
            number += 1
            iface, hi, lo, caplen, original = struct.unpack_from(endian + "IIIII", body)
            if links[iface] != 1:
                raise ValueError("Expected Ethernet")
            frame = body[20:20 + caplen]
            if frame[12:14] == b"\x08\x00":
                ip = frame[14:]
                ihl = (ip[0] & 15) * 4
                if ip[9] == 17:
                    udp = ip[ihl:]
                    sport, dport, length, checksum = struct.unpack_from("!HHHH", udp)
                    data = udp[8:length]
                    if {sport, dport} == {67, 68} and data[236:240] == b"\x63\x82\x53\x63":
                        opts = {}
                        pos = 240
                        while pos < len(data):
                            code = data[pos]
                            pos += 1
                            if code == 255:
                                break
                            if code == 0:
                                continue
                            length = data[pos]
                            pos += 1
                            opts[code] = data[pos:pos + length]
                            pos += length
                        row = {
                            "packet": number,
                            "type": names.get(opts.get(53, b"\0")[0], "Other"),
                            "xid": f"0x{int.from_bytes(data[4:8], 'big'):08x}",
                            "source": socket.inet_ntoa(ip[12:16]),
                            "destination": socket.inet_ntoa(ip[16:20]),
                            "source_port": sport, "destination_port": dport,
                            "ethernet_destination": ":".join(f"{b:02x}" for b in frame[:6]),
                            "client_hardware_address": ":".join(
                                f"{b:02x}" for b in data[28:28 + data[2]]),
                            "broadcast_flag": bool(int.from_bytes(data[10:12], "big") & 0x8000),
                            "ciaddr": socket.inet_ntoa(data[12:16]),
                            "yiaddr": socket.inet_ntoa(data[16:20]),
                        }
                        for code, field in ((51, "lease_seconds"), (58, "renewal_seconds"),
                                            (59, "rebinding_seconds")):
                            if code in opts:
                                row[field] = int.from_bytes(opts[code], "big")
                        for code, field in ((54, "server_identifier"), (50, "requested_ip"),
                                            (1, "subnet_mask"), (3, "router")):
                            if code in opts:
                                row[field] = socket.inet_ntoa(opts[code][:4])
                        rows.append(row)
        offset += size
    return {"source": "Official 9e dhcp-wireshark-trace1-1.pcapng; not our capture",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "total_frames": number, "messages": rows}


if __name__ == "__main__":
    result = analyze(OUT / "dhcp.pcapng")
    transactions = {}
    for row in result["messages"]:
        transactions.setdefault(row["xid"], set()).add(row["type"])
    assert any({"Discover", "Offer", "Request", "Ack"} <= kinds
               for kinds in transactions.values()), "No complete DORA transaction"
    text = json.dumps(result, indent=2)
    (OUT / "dhcp-analysis.json").write_text(text, encoding="utf-8")
    print(text)
