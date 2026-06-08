import asyncio
from bleak import BleakClient, BleakScanner

DEVICE_ADDRESS = "66:1E:11:0E:C0:85"
CHAR_13 = "0000fff1-0000-1000-8000-00805f9b34fb"
CHAR_16 = "0000fff2-0000-1000-8000-00805f9b34fb"

def notification_handler(sender, data):
    text = data.decode("utf-8", errors="ignore").replace(">", "").replace("\r", "").replace("\n", "").strip()
    if text:
        print(f"[Araç]: {text}")

async def send_cmd(client, cmd_text, delay=1.2):
    print(f"\nGönderiliyor -> {cmd_text}")
    await client.write_gatt_char(CHAR_16, f"{cmd_text}\r".encode(), response=False)
    await asyncio.sleep(delay)

async def main():
    device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)
    if not device: return
    async with BleakClient(device) as client:
        await client.start_notify(CHAR_13, notification_handler)
        await send_cmd(client, "AT Z", 0.5)
        await send_cmd(client, "AT SH 7E3", 0.5)
        
        # Programlama oturumu denemesi
        print("\n=== PROGRAMLAMA OTURUMU DENEMESİ ===")
        await send_cmd(client, "1002", 1.5)
        
        # Eğer 1002 başarılıysa (50 02 dönerse), 220200 ü tekrar isteyelim
        await send_cmd(client, "220200", 1.5)
        
        while True: await asyncio.sleep(1)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nKapatıldı.")
