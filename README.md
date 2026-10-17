# Leapmotor T03 – OBD2 (ELM327 BLE) tersine mühendislik notları

Leapmotor T03'ün bataryasını/aracı BLE ELM327 adaptörü ile **yalnızca okuyarak** izlemek için notlar ve araçlar.

- Bkz. [docs/ecu_haritasi.md](docs/ecu_haritasi.md) – ECU adresleri
- Bkz. [docs/did_haritasi.md](docs/did_haritasi.md) – doğrulanmış / aday DID'ler
- Bkz. [docs/bulgular.md](docs/bulgular.md) – ölçümler, açık sorular
- `tools/t03_izleme.py` – Tkinter izleme arayüzü (tablo, grafik, CSV, etiket kutusu)
- `tools/t03_oku.py` – BMU'dan çekirdek DID'leri okuyup CSV'ye yazan basit betik

## Güvenlik ilkeleri
- Yalnızca okuma: UDS 0x22, 0x19 02 FF, 0x3E ve ELM AT ayarları.
- Oturum kontrolü (10 xx), güvenlik erişimi, yazma, kodlama, DTC silme, balans/reset **kullanılmaz**.
- VIN ve adaptör MAC adresi bu depoya yazılmaz (`ADAPTOR_MAC` ortam değişkeni ile verin).
- Üretici bulut kimlik doğrulamasını aşmaya yönelik hiçbir şey içermez.

## Kurulum (Manjaro)
```
sudo pacman -S python-bleak
# /etc/bluetooth/main.conf  [General] altında:  ControllerMode = le
sudo systemctl restart bluetooth
```
İş bitince `ControllerMode = le` satırını geri alın ve bluetooth'u yeniden başlatın (klasik BT cihazları için).
Adaptör tek bağlantı destekler; başka betik/REPL açıksa kapatın.

## Kullanım
Arayüz: `python3 tools/t03_izleme.py` (MAC'i pencereden girin; Arch/Manjaro'da `tk` paketi gerekir).

Komut satırı:
```
ADAPTOR_MAC=XX:XX:XX:XX:XX:XX python3 tools/t03_oku.py
```
Çıktı: `kayitlar/t03_<zaman>.csv`.
