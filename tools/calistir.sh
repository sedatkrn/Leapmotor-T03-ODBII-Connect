#!/usr/bin/env bash
# Leapmotor T03 izleme programını başlatır (salt-okunur).
# İsteğe bağlı: aynı klasöre adaptor_mac.txt koyup içine adaptör MAC adresini yazarsanız
# pencerede otomatik dolar (bu dosyayı depoya eklemeyin).
cd "$(dirname "$(readlink -f "$0")")" || exit 1

if ! python3 -c "import bleak" 2>/dev/null; then
  echo "Eksik: bleak  ->  sudo pacman -S python-bleak"; exit 1
fi
if ! python3 -c "import tkinter" 2>/dev/null; then
  echo "Eksik: tkinter  ->  sudo pacman -S tk"; exit 1
fi
if [ -z "$ADAPTOR_MAC" ] && [ -f adaptor_mac.txt ]; then
  ADAPTOR_MAC="$(tr -d '[:space:]' < adaptor_mac.txt)"
  export ADAPTOR_MAC
fi
if ! systemctl is-active --quiet bluetooth; then
  echo "Bluetooth servisi kapalı  ->  sudo systemctl start bluetooth"; exit 1
fi
echo "Not: adaptör tek bağlantı destekler; başka betik/REPL açıksa kapatın."
exec python3 t03_izleme.py "$@"
