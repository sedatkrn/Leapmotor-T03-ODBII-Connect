#!/usr/bin/env python3
"""T03 BMU çekirdek DID'lerini salt-okunur olarak CSV'ye kaydeder.
Kullanım: ADAPTOR_MAC=XX:XX:XX:XX:XX:XX python3 t03_oku.py
Yalnızca ELM AT ayarları + UDS 0x22 kullanır."""
import asyncio, csv, os, sys, time
from bleak import BleakClient, BleakScanner

MAC = os.environ.get("ADAPTOR_MAC")
NOTIFY = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE = "0000fff2-0000-1000-8000-00805f9b34fb"
TX, RX = "722", "72A"

u = lambda b: int.from_bytes(b, "little")
s = lambda b: int.from_bytes(b, "little", signed=True)
DIDS = [  # (did, ad, bayt, çözücü)
    ("01A0", "pil_v", 4, lambda b: u(b) / 1000),
    ("01B2", "akim_a", 4, lambda b: s(b) / 1000),
    ("01A1", "h_min_v", 2, lambda b: u(b) / 1000),
    ("01A2", "h_max_v", 2, lambda b: u(b) / 1000),
    ("0200", "h_ort_v", 2, lambda b: u(b) / 1000),
    ("01A5", "t_min", 1, lambda b: b[0]),
    ("01A6", "t_max", 1, lambda b: b[0]),
    ("0223", "t_ort", 1, lambda b: b[0]),
    ("01F1", "soc_adayi_01F1", 2, lambda b: u(b) / 10),
]

buf = ""
ev = asyncio.Event()

def on_data(_, data):
    global buf
    buf += data.decode("utf-8", "ignore")
    if ">" in buf:
        ev.set()

async def cmd(c, client, timeout=2.0):
    global buf
    buf = ""; ev.clear()
    await client.write_gatt_char(WRITE, (c + "\r").encode(), response=False)
    try:
        await asyncio.wait_for(ev.wait(), timeout)
    except asyncio.TimeoutError:
        pass
    return [l.strip() for l in buf.replace(">", "").splitlines() if l.strip()]

def birlestir(satirlar):
    """ISO-TP birleştirme; ATH1 ile satır başında CAN id bulunur."""
    veri, toplam = [], None
    for sat in satirlar:
        t = sat.split()[1:]
        if not t:
            continue
        try:
            p = int(t[0], 16)
        except ValueError:
            continue
        tip = p >> 4
        if tip == 0:
            toplam = p & 0xF; veri += t[1:1 + toplam]
        elif tip == 1:
            toplam = ((p & 0xF) << 8) | int(t[1], 16); veri += t[2:]
        elif tip == 2:
            veri += t[1:]
    return veri[:toplam] if toplam else veri

async def main():
    if not MAC:
        sys.exit("ADAPTOR_MAC ortam değişkenini ayarlayın.")
    dev = await BleakScanner.find_device_by_address(MAC, timeout=10)
    if not dev:
        sys.exit("Adaptör bulunamadı.")
    os.makedirs("kayitlar", exist_ok=True)
    ad = time.strftime("kayitlar/t03_%Y%m%d_%H%M%S.csv")
    async with BleakClient(dev) as client:
        await client.start_notify(NOTIFY, on_data)
        for c in ["ATZ", "ATE0", "ATL0", "ATH1", "ATS1", "ATSP6", "ATCAF1", "ATST20",
                  f"ATSH{TX}", f"ATCRA{RX}"]:
            await cmd(c, client, 3.0)
        with open(ad, "w", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["zaman"] + [d[1] for d in DIDS] + ["guc_kw"])
            print("Kayıt:", ad, "(Ctrl+C ile durdur)")
            try:
                while True:
                    satir, vals = [time.strftime("%H:%M:%S")], {}
                    for did, ad_, n, fn in DIDS:
                        yanit = birlestir(await cmd("22" + did, client))
                        if yanit[:3] == ["62", did[:2], did[2:]] and len(yanit) >= 3 + n:
                            v = fn(bytes(int(x, 16) for x in yanit[3:3 + n]))
                        else:
                            v = ""
                        vals[ad_] = v; satir.append(v)
                    try:
                        satir.append(round(vals["pil_v"] * vals["akim_a"] / 1000, 3))
                    except TypeError:
                        satir.append("")
                    w.writerow(satir); f.flush(); print(satir)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nKapatıldı.")
