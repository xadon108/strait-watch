#!/usr/bin/env python3
"""
Strait Watch â AIS Data Fetcher
Connects to AISstream.io WebSocket (server-side, no CORS), collects 60s of
Strait of Hormuz vessel data, and writes data/vessels.json for the dashboard.

Usage: python scripts/fetch_ais.py
Env:   AIS_KEY  â must be set as a GitHub Actions secret (Settings â Secrets â
                   Actions â AIS_KEY). Never hardcode the key here.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

# ââ Config âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# AIS_KEY must be injected via a GitHub Actions secret (secrets.AIS_KEY).
# Never commit a raw key here â GitHub Pages would expose it in the public repo.
AIS_KEY   = os.environ.get('AIS_KEY')
if not AIS_KEY:
    print('ERROR: AIS_KEY environment variable is not set.')
    print('Set it as a GitHub Actions secret: Settings â Secrets â Actions â AIS_KEY')
    sys.exit(1)
BBOX      = [[24.5, 55.5], [27.5, 58.5]]   # Strait of Hormuz + approaches
COLLECT_S = 60                              # Seconds to collect data
OUT_FILE  = 'data/vessels.json'

# ââ Ship type helper ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def ship_type(t):
    if 80 <= t <= 89: return 'Tanker'
    if 70 <= t <= 79: return 'Cargo'
    if 60 <= t <= 69: return 'Passenger'
    if 30 <= t <= 39: return 'Fishing'
    return 'Vessel'

# ââ Nav status â dashboard status ââââââââââââââââââââââââââââââââââââââââââ
def nav_status(nav, sog):
    if nav in (1, 5): return 'anchored'
    if nav in (3, 4): return 'queued'
    if sog is not None and sog < 0.5: return 'anchored'
    return 'transit'

# ââ Main fetch ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def fetch():
    try:
        import websockets
    except ImportError:
        print('ERROR: websockets package not installed. Run: pip install websockets')
        sys.exit(1)

    vessels = {}
    print(f'Connecting to AISstream.ioâ¦')

    try:
        async with websockets.connect(
            'wss://stream.aisstream.io/v0/stream',
            ping_interval=20,
            ping_timeout=10
        ) as ws:
            await ws.send(json.dumps({
                'APIKey': AIS_KEY,
                'BoundingBoxes': [BBOX],
                'FilterMessageTypes': ['PositionReport', 'ShipStaticData']
            }))
            print(f'Subscribed. Collecting {COLLECT_S}s of dataâ¦')

            deadline = asyncio.get_event_loop().time() + COLLECT_S
            while asyncio.get_event_loop().time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    msg  = json.loads(raw)
                    meta = msg.get('MetaData', {})
                    mmsi = meta.get('MMSI')
                    if not mmsi:
                        continue

                    mtype = msg.get('MessageType', '')

                    if mtype == 'PositionReport':
                        pr  = msg.get('Message', {}).get('PositionReport', {})
                        sog = pr.get('Sog')
                        hdg = pr.get('TrueHeading', 511)
                        if hdg >= 360:
                            hdg = pr.get('Cog', 0)

                        existing = vessels.get(mmsi, {})
                        vessels[mmsi] = {
                            **existing,
                            'imo':       mmsi,
                            'name':      (meta.get('ShipName') or '').strip() or existing.get('name', f'MMSI {mmsi}'),
                            'flag':      existing.get('flag', '--'),
                            'type':      existing.get('type', 'Vessel'),
                            'status':    nav_status(pr.get('NavigationalStatus', 15), sog),
                            'speed':     round((sog or 0) * 10) / 10,
                            'heading':   round(hdg, 1),
                            'lat':       meta.get('latitude', existing.get('lat', 0)),
                            'lng':       meta.get('longitude', existing.get('lng', 0)),
                            'last_seen': (meta.get('time_utc', '') or
                                          datetime.now(timezone.utc).isoformat())[:16].replace('T', ' ') + ' UTC',
                        }

                    elif mtype == 'ShipStaticData':
                        sd = msg.get('Message', {}).get('ShipStaticData', {})
                        existing = vessels.get(mmsi, {})
                        vessels[mmsi] = {
                            **existing,
                            'imo':  sd.get('ImoNumber') or mmsi,
                            'name': (sd.get('Name') or meta.get('ShipName') or '').strip() or existing.get('name', f'MMSI {mmsi}'),
                            'flag': sd.get('Destination', '--') or '--',
                            'type': ship_type(sd.get('Type', 0)),
                        }

                except asyncio.TimeoutError:
                    pass  # No message in 5s â keep waiting until deadline

    except Exception as e:
        print(f'Connection error: {e}')
        # If we got some vessels before the error, still save them
        if not vessels:
            print('No data collected â keeping existing vessels.json')
            sys.exit(0)

    # ââ Write output âââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    os.makedirs('data', exist_ok=True)
    output = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'source':  'AISstream.io via GitHub Actions',
        'vessels': list(vessels.values())
    }
    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print(f'â Saved {len(vessels)} vessels â {OUT_FILE}')

if __name__ == '__main__':
    asyncio.run(fetch())
