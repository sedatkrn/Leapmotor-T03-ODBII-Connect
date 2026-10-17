# DID haritası (UDS 0x22; BMU 722, little-endian)

Batarya: LFP, 124S1P (DID F110 = `T3A-124S01P-R1-6-001`), nominal 396 V.

## Doğrulanmış / güçlü
| DID | Anlam | Çözüm |
|---|---|---|
| 01A0 | Pil voltajı | uint32 / 1000 → V |
| 01B2 | Akım (şarjda negatif) | int32 / 1000 → A |
| 01A1 / 01A2 / 0200 | Hücre min / max / ort | uint16 mV |
| 01A5 / 01A6 / 0223 | Sıcaklık min / max / ort | tek bayt, °C |
| 01DD | Nominal voltaj | uint32 / 1000 → 396.000 V |

Diğer ECU'lar:
- VCU 720: `02FF` = kilometre sayacı, 3 bayt big-endian (gösterge ile eşleşti).
- CDU 788: `0486` bayt 0–1 big-endian = pil voltajı (tam volt).

## Aday / çözülmemiş
- SOC: en iyi aday `01F1` (uint16/10, gösterge %99 ↔ 99.0); diğer `01EF`.
- `01EE` (dinlenmede yavaş düşüş, şarjda hızlı artış), `01F0` (93.2 sabit), `01F2` (100.0 sabit), `01E0` (-53.6 sabit).
- `01F3–01F9`, `0202`, `0227`, 788/`0486` diğer baytlar, 720/`0111`,`0113`, `02B0–02D9` bayraklar.
- 124 tek tek hücre voltaj bloğu bulunamadı. Taranan: BMU 0000–2FFF, F100–F4FF (varsayılan oturum). `21` servisi desteklenmiyor (7F 21 11).
- Taranmadı: BMU F000–F0FF, F500–FFFF, 3000–EFFF; 788/720 0500–0FFF; 721 ve 792 0000–04FF.

## DTC
BMU `19 02 FF`: 58 giriş (kod 2B + tip + durum). Çoğu durum 0x10; bir tanesi 0x08 (`D0 84 87`, mesaj eksik). Silinmedi.
