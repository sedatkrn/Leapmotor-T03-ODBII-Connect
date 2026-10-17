#!/usr/bin/env python3
"""Leapmotor T03 – salt-okunur izleme arayüzü (Tkinter + bleak).

Yalnızca ELM AT ayarları ve UDS 0x22 (ReadDataByIdentifier) kullanır.
Okunanlar:
  BMU 722/72A : pil V, akım, hücre min/max/ort, sıcaklık, SOC adayları
  CDU 780/788 : DID 0486 (şebeke V/A, pil V)  -> şarj sırasında anlamlı
  VCU 720/728 : DID 02FF kilometre sayacı (yavaş okunur)
Çalıştırma:  python3 t03_izleme.py   (MAC adresini pencereden girin)
CSV: kayitlar/t03_<zaman>.csv  (etiket kutusuna yazdığınız metin satırlara eklenir)
"""
import asyncio
import csv
import os
import queue
import threading
import time
from collections import deque

NOTIFY = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE = "0000fff2-0000-1000-8000-00805f9b34fb"

u = lambda b: int.from_bytes(b, "little")
s = lambda b: int.from_bytes(b, "little", signed=True)

# (did, anahtar, bayt, çözücü)
BMU = [
    ("01A0", "pil_v", 4, lambda b: u(b) / 1000),
    ("01B2", "akim_a", 4, lambda b: s(b) / 1000),
    ("01A1", "h_min_mv", 2, lambda b: float(u(b))),
    ("01A2", "h_max_mv", 2, lambda b: float(u(b))),
    ("0200", "h_ort_mv", 2, lambda b: float(u(b))),
    ("01A5", "t_min", 1, lambda b: float(b[0])),
    ("01A6", "t_max", 1, lambda b: float(b[0])),
    ("0223", "t_ort", 1, lambda b: float(b[0])),
    ("01EE", "soc_01EE", 2, lambda b: u(b) / 10),
    ("01EF", "soc_01EF", 2, lambda b: u(b) / 10),
    ("01F0", "soc_01F0", 2, lambda b: u(b) / 10),
    ("01F1", "soc_gosterge", 2, lambda b: u(b) / 10),
    ("01F2", "x_01F2", 2, lambda b: u(b) / 10),
]

# (anahtar, etiket, birim, format)
ALANLAR = [
    ("pil_v", "Pil voltajı", "V", "{:.3f}"),
    ("akim_a", "Akım (şarjda -)", "A", "{:.3f}"),
    ("guc_kw", "Pil gücü (şarjda -)", "kW", "{:.3f}"),
    ("h_min_mv", "Hücre min", "mV", "{:.0f}"),
    ("h_max_mv", "Hücre max", "mV", "{:.0f}"),
    ("h_ort_mv", "Hücre ort", "mV", "{:.0f}"),
    ("h_fark_mv", "Hücre farkı", "mV", "{:.0f}"),
    ("t_min", "Sıcaklık min", "°C", "{:.0f}"),
    ("t_max", "Sıcaklık max", "°C", "{:.0f}"),
    ("t_ort", "Sıcaklık ort", "°C", "{:.0f}"),
    ("soc_gosterge", "SOC 01F1 (gösterge)", "%", "{:.1f}"),
    ("soc_01EF", "SOC 01EF (pil doluluğu)", "%", "{:.1f}"),
    ("soc_01F0", "SOC 01F0 (pil doluluğu)", "%", "{:.1f}"),
    ("soc_01EE", "SOC 01EE (pil doluluğu)", "%", "{:.1f}"),
    ("x_01F2", "01F2 (üst sınır/SOH?)", "%", "{:.1f}"),
    ("ac_v", "Şebeke voltajı (788)", "V", "{:.0f}"),
    ("ac_a", "Şebeke akımı (788)", "A", "{:.1f}"),
    ("ac_kw", "Şebeke gücü", "kW", "{:.3f}"),
    ("kayip_kw", "Şarj kaybı (şebeke-pil)", "kW", "{:.3f}"),
    ("km", "Kilometre", "km", "{:.0f}"),
]
ANAHTARLAR = [a[0] for a in ALANLAR]


def birlestir(satirlar):
    """ATH1 çıktısını ISO-TP olarak birleştirir; hex bayt listesi döner."""
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
            toplam = p & 0xF
            veri += t[1:1 + toplam]
        elif tip == 1:
            toplam = ((p & 0xF) << 8) | int(t[1], 16)
            veri += t[2:]
        elif tip == 2:
            veri += t[1:]
    return veri[:toplam] if toplam else veri


def did_verisi(veri, did):
    """Olumlu yanıttan (62 DD DD ...) veri baytlarını döndürür, yoksa None."""
    if veri[:3] == ["62", did[:2], did[2:]]:
        return bytes(int(x, 16) for x in veri[3:])
    return None


def cdu_coz(b):
    """788/0486 baytları (15 bayt). Dönüş: dict ac_v, ac_a."""
    if b is None or len(b) < 9:
        return {}
    return {"ac_v": float((b[5] << 8) | b[6]), "ac_a": ((b[7] << 8) | b[8]) / 10}


class Elm:
    def __init__(self, client):
        self.c = client
        self.buf = ""
        self.ev = asyncio.Event()
        self.ecu = None

    def on(self, _, data):
        self.buf += data.decode("utf-8", "ignore")
        if ">" in self.buf:
            self.ev.set()

    async def cmd(self, c, t=2.0):
        self.buf = ""
        self.ev.clear()
        await self.c.write_gatt_char(WRITE, (c + "\r").encode(), response=False)
        try:
            await asyncio.wait_for(self.ev.wait(), t)
        except asyncio.TimeoutError:
            pass
        return [l.strip() for l in self.buf.replace(">", "").splitlines() if l.strip()]

    async def ecu_sec(self, tx, rx):
        if self.ecu != tx:
            await self.cmd("ATSH" + tx)
            await self.cmd("ATCRA" + rx)
            self.ecu = tx

    async def did(self, did):
        return did_verisi(birlestir(await self.cmd("22" + did)), did)


async def dongu(mac, q, dur, durum):
    from bleak import BleakClient, BleakScanner
    dev = await BleakScanner.find_device_by_address(mac, timeout=10)
    if not dev:
        q.put(("hata", "Adaptör bulunamadı"))
        return
    os.makedirs("kayitlar", exist_ok=True)
    dosya = time.strftime("kayitlar/t03_%Y%m%d_%H%M%S.csv")
    async with BleakClient(dev) as cl:
        elm = Elm(cl)
        await cl.start_notify(NOTIFY, elm.on)
        for c in ["ATZ", "ATE0", "ATL0", "ATH1", "ATS1", "ATSP6", "ATCAF1", "ATST20"]:
            await elm.cmd(c, 3.0)
        q.put(("durum", "Bağlandı – kayıt: " + dosya))
        km, tur = None, 0
        with open(dosya, "w", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["zaman", "etiket"] + ANAHTARLAR)
            while not dur.is_set():
                d = {}
                await elm.ecu_sec("722", "72A")
                for did, ad, n, fn in BMU:
                    b = await elm.did(did)
                    if b is not None and len(b) >= n:
                        d[ad] = fn(b[:n])
                await elm.ecu_sec("780", "788")
                d.update(cdu_coz(await elm.did("0486")))
                if tur % 20 == 0:
                    await elm.ecu_sec("720", "728")
                    b = await elm.did("02FF")
                    if b is not None and len(b) >= 3:
                        km = int.from_bytes(b[:3], "big")
                tur += 1
                if km is not None:
                    d["km"] = float(km)
                # türetilenler
                if "pil_v" in d and "akim_a" in d:
                    d["guc_kw"] = d["pil_v"] * d["akim_a"] / 1000
                if "h_min_mv" in d and "h_max_mv" in d:
                    d["h_fark_mv"] = d["h_max_mv"] - d["h_min_mv"]
                if "ac_v" in d and "ac_a" in d:
                    d["ac_kw"] = d["ac_v"] * d["ac_a"] / 1000
                    if "guc_kw" in d and d.get("akim_a", 0) < -0.5:
                        d["kayip_kw"] = d["ac_kw"] + d["guc_kw"]
                w.writerow([time.strftime("%H:%M:%S"), durum["etiket"]]
                           + [("%g" % d[k]) if k in d else "" for k in ANAHTARLAR])
                f.flush()
                q.put(("veri", d))
    q.put(("durum", "Bağlantı kapandı"))


def isci(mac, q, dur, durum):
    try:
        asyncio.run(dongu(mac, q, dur, durum))
    except Exception as e:  # noqa: BLE001
        q.put(("hata", repr(e)))


def arayuz():
    import tkinter as tk
    from tkinter import ttk

    kok = tk.Tk()
    kok.title("Leapmotor T03 izleme (salt-okunur)")
    q = queue.Queue()
    dur = threading.Event()
    durum = {"etiket": "-"}
    gecmis = {k: deque(maxlen=400) for k in ANAHTARLAR}
    secili = {"k": "pil_v"}

    ust = ttk.Frame(kok, padding=6)
    ust.pack(fill="x")
    ttk.Label(ust, text="Adaptör MAC:").pack(side="left")
    mac = tk.StringVar(value=os.environ.get("ADAPTOR_MAC", ""))
    ttk.Entry(ust, textvariable=mac, width=20).pack(side="left", padx=4)
    dugme = ttk.Button(ust, text="Bağlan")
    dugme.pack(side="left", padx=4)
    ttk.Label(ust, text="Etiket:").pack(side="left", padx=(12, 0))
    etk = tk.StringVar(value="-")
    giris = ttk.Entry(ust, textvariable=etk, width=24)
    giris.pack(side="left", padx=4)

    def etiket_uygula(_=None):
        durum["etiket"] = etk.get().strip() or "-"
    giris.bind("<Return>", etiket_uygula)
    ttk.Button(ust, text="Uygula", command=etiket_uygula).pack(side="left")
    ust2 = ttk.Label(kok, text="Hazır", padding=(6, 0))
    ust2.pack(fill="x")

    tree = ttk.Treeview(kok, columns=("ad", "deger", "birim"), show="headings", height=len(ALANLAR))
    for c, t, wd in (("ad", "Alan", 230), ("deger", "Değer", 110), ("birim", "Birim", 50)):
        tree.heading(c, text=t)
        tree.column(c, width=wd, anchor="w" if c == "ad" else "e")
    for k, ad, bi, _ in ALANLAR:
        tree.insert("", "end", iid=k, values=(ad, "-", bi))
    tree.pack(fill="x", padx=6, pady=4)
    cv = tk.Canvas(kok, width=560, height=180, bg="white", highlightthickness=1)
    cv.pack(padx=6, pady=4)

    def sec(_):
        s_ = tree.selection()
        if s_:
            secili["k"] = s_[0]
            ciz()
    tree.bind("<<TreeviewSelect>>", sec)

    def ciz():
        cv.delete("all")
        k = secili["k"]
        v = list(gecmis[k])
        ad = next(a[1] for a in ALANLAR if a[0] == k)
        cv.create_text(6, 4, anchor="nw", text=ad + "  (satıra tıklayın)")
        if len(v) < 2:
            return
        lo, hi = min(v), max(v)
        if hi == lo:
            hi, lo = hi + 1, lo - 1
        W, H, P = 560, 180, 24
        pts = []
        for i, y in enumerate(v):
            pts += [P + i * (W - 2 * P) / (len(v) - 1), H - P - (y - lo) / (hi - lo) * (H - 2 * P)]
        cv.create_line(*pts, fill="#1f77b4", width=2)
        cv.create_text(W - 4, P, anchor="e", text="%g" % hi)
        cv.create_text(W - 4, H - P, anchor="e", text="%g" % lo)

    def poll():
        try:
            while True:
                t, x = q.get_nowait()
                if t == "veri":
                    for k, ad, bi, fm in ALANLAR:
                        if k in x:
                            tree.set(k, "deger", fm.format(x[k]))
                            gecmis[k].append(x[k])
                    ciz()
                elif t in ("durum", "hata"):
                    ust2.config(text=("HATA: " if t == "hata" else "") + x)
                    if t == "hata" or x == "Bağlantı kapandı":
                        dugme.config(text="Bağlan")
        except queue.Empty:
            pass
        kok.after(200, poll)

    def tikla():
        if dugme["text"] == "Bağlan":
            if not mac.get().strip():
                ust2.config(text="MAC adresini girin")
                return
            dur.clear()
            threading.Thread(target=isci, args=(mac.get().strip(), q, dur, durum), daemon=True).start()
            dugme.config(text="Durdur")
            ust2.config(text="Bağlanıyor…")
        else:
            dur.set()
            dugme.config(text="Bağlan")
    dugme.config(command=tikla)
    kok.protocol("WM_DELETE_WINDOW", lambda: (dur.set(), kok.destroy()))
    poll()
    kok.mainloop()


if __name__ == "__main__":
    arayuz()
