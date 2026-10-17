# ECU haritası (CAN 11-bit, 500 kbit/s; yanıt adresi = istek + 8)

| İstek→Yanıt | Parça | Rol |
|---|---|---|
| 720→728 | LP-VCU020-AA | VCU |
| 721→729 | LP-MCUM103-AA | Motor kontrol |
| **722→72A** | **LP-BMU021-AA (SW 2.99.30)** | **BMS/BMU** |
| 726→72E | LP-BCMB020-AA | BCM |
| 732→73A | LP-IVI020-AA | Multimedya |
| 733→73B | (bilinmiyor, kodlanmamış) | – |
| 750→758 | BNE-HVAC021-AB | Klima |
| 753→75B | LP-ICU020-AA (SW 2.01.15) | Gösterge paneli |
| 780→788 | LP-CDU20002-AC | Şarj / güç dağıtım |
| 792→79A | NAEN-PWU-T030000 | Güç ünitesi |

Standart OBD (7E8) 0100'e boş maske döner; pasif CAN yayını gateway nedeniyle görünmez.
ELM kurulumu: ATZ, ATE0, ATL0, ATH1, ATS1, ATSP6, ATCAF1, ATST20, ATSH<tx>, ATCRA<rx>.
BLE: notify `0000fff1-…`, write `0000fff2-…`.
