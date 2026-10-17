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

## SOC adayları (uint16 / 10, %)
2026-10-17 şarj kaydı: 7 dk'da pile 0,199 kWh DC girdi (V×I integrali).

| DID | Başlangıç → son | Not |
|---|---|---|
| 01EE | 89,4 → 89,9 | +0,5; pil doluluğu, farklı ofset |
| 01EF | 99,2 → 99,7 | +0,5; pil doluluğu |
| 01F0 | 92,4 → 92,9 | +0,5; pil doluluğu |
| 01F1 | 99,0 → 99,1 | yavaş artıyor; gösterge SOC'sine benziyor (gösterge %99) |
| 01F2 | 100,0 sabit | üst sınır / SOH olabilir |

0,5 puan ↔ 0,199 kWh → yaklaşık 39,8 kWh kapasite ile uyumlu.
Hangisinin "gerçek" ve hangisinin "kullanılabilir" SOC olduğu %99–100 bölgesinde ayrılamıyor; %70–90 aralığında kayıt gerekir.
- `01E0` (-53,6 sabit): bilinmiyor.
- `01F3–01F9`, `0202`, `0227`, 788/`0486` diğer baytlar, 720/`0111`,`0113`, `02B0–02D9` bayraklar.
- 124 tek tek hücre voltaj bloğu bulunamadı. Taranan: BMU 0000–2FFF, F100–F4FF (varsayılan oturum). `21` servisi desteklenmiyor (7F 21 11).
- Taranmadı: BMU F000–F0FF, F500–FFFF, 3000–EFFF; 788/720 0500–0FFF; 721 ve 792 0000–04FF.

## DTC
BMU `19 02 FF`: 58 giriş (kod 2B + tip + durum). Çoğu durum 0x10; bir tanesi 0x08 (`D0 84 87`, mesaj eksik). Silinmedi.

## CDU 780→788, DID 0486 (15 bayt) – şarj kaydıyla çözüldü
| Bayt | Anlam | Not |
|---|---|---|
| b0–1 | Pil voltajı, tam volt (big-endian) | BMU ile uyuyor |
| b5–6 | Şebeke voltajı, V (big-endian) | fiş takılınca 0 → ~241 |
| b8 | Şebeke akımı, 0,1 A | 10 A'da 0x66, 8 A'da 0x4E, 6 A'da 0x3C |
| b9 | b8'in 1/6'sı | anlamı bilinmiyor |
| b4, b14 | Aynı değer, dakikada bir basamak artıyor | muhtemelen sıcaklık (ofsetli); tahmin |
| b2–3 | Akımla değişiyor | anlamı bilinmiyor |

Not: önceki yorum (0x0135 = akım) yanlıştı; o değer boşta kalan b8–9 bayt çiftiydi.

## Şarj ölçümleri (10 / 8 / 6 A ayarı)
| Kademe | DC akım | Pil V | DC güç |
|---|---|---|---|
| 10 A | −5,17 A | ~413,9 | ~2,14 kW |
| 8 A | −3,80 A | ~415,6 | ~1,58 kW |
| 6 A | −2,71 A | ~415,7 | ~1,13 kW |

Şebeke gücü (b8×V) ile DC güç farkı her kademede ≈ 0,28–0,31 kW (kayıp + araç tabanı yükü).
Akım basamaklarından iç direnç ≈ 0,09–0,15 Ω. Hücre farkı şarjda 17 → 24 mV.
