import asyncio
import websockets
import subprocess
import socket

PORT = 8765
connected_clients = set()

async def stream_sensor_data(websocket):
    connected_clients.add(websocket)
    try:
        if len(connected_clients) == 1:
            print("[+] Starting sensor stream...")

        async for message in read_sensor():
            await asyncio.gather(*[client.send(message) for client in connected_clients])
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)

import json

async def read_sensor():
    process = await asyncio.create_subprocess_exec(
        'termux-sensor', '-s', 'light', '-d', '50',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    buffer = ""
    braces_open = 0
    braces_closed = 0

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        decoded = line.decode('utf-8').strip()

        # Track opening and closing braces to detect a full JSON object
        braces_open += decoded.count('{')
        braces_closed += decoded.count('}')
        buffer += decoded

        if braces_open > 0 and braces_open == braces_closed:
            try:
                data = json.loads(buffer)
                if isinstance(data, dict) and data:
                    first_key = next(iter(data))
                    light_value = data[first_key]["values"][0]
                    yield str(light_value)
            except Exception as e:
                print(f"[!] Error parsing JSON: {e}")
            finally:
                # Reset for next JSON chunk
                buffer = ""
                braces_open = 0
                braces_closed = 0


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    return local_ip

def ip_normal():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    return local_ip

def ip_hotspot():
    cmd = "busybox ifconfig wlan0"
    c = subprocess.run(cmd.split(), capture_output=True)

    o = c.stdout.decode()
    ip = "127.0.0.1"
    for i in o.splitlines():
        if "inet addr" in i:
            l = i.strip().split()[1]
            ip = l.split(":")[1]
    return ip




async def main():
    server = await websockets.serve(stream_sensor_data, '0.0.0.0', PORT)
    iph = ip_hotspot()
    ipn = ip_normal()
    print(f"[+] WebSocket server is running at:\nHOTSPOT: ws://{iph}:{PORT}\nNORMAL: ws://{ipn}:{PORT}")
    await server.wait_closed()

if __name__ == "__main__":
    import sys
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Server stopped by user.")
