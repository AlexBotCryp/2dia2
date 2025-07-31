import os
import time
import json
import requests
import pytz
from datetime import datetime
from binance.client import Client
from apscheduler.schedulers.background import BackgroundScheduler

# Configuración
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = Client(API_KEY, API_SECRET)
PORCENTAJE_USDC = 0.8
TAKE_PROFIT = 0.004
STOP_LOSS = -0.015
PERDIDA_MAXIMA_DIARIA = 50
MONEDA_BASE = "USDC"
RESUMEN_HORA = 23

TIMEZONE = pytz.timezone("UTC")

def enviar_telegram(mensaje):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
        )
    except:
        pass

def cargar_registro():
    if os.path.exists("registro.json"):
        with open("registro.json", "r") as f:
            return json.load(f)
    return {}

def guardar_registro(data):
    with open("registro.json", "w") as f:
        json.dump(data, f)

def mejores_criptos():
    try:
        tickers = client.get_ticker()
        return sorted(
            [t for t in tickers if t["symbol"].endswith(MONEDA_BASE) and float(t.get("quoteVolume", 0)) > 100000],
            key=lambda x: float(x.get("priceChangePercent", 0)),
            reverse=True
        )
    except:
        return []

def comprar():
    saldo = float(client.get_asset_balance(asset=MONEDA_BASE)["free"])
    if saldo < 10: return
    cantidad_usdc = saldo * PORCENTAJE_USDC
    criptos = mejores_criptos()
    registro = cargar_registro()

    for cripto in criptos:
        symbol = cripto["symbol"]
        if symbol in registro: continue
        try:
            precio = float(cripto["lastPrice"])
            cantidad = round(cantidad_usdc / precio, 4)
            orden = client.order_market_buy(symbol=symbol, quantity=cantidad)
            registro[symbol] = {"cantidad": cantidad, "precio_compra": precio}
            guardar_registro(registro)
            enviar_telegram(f"🟢 Comprado {symbol} - {cantidad:.4f} a {precio:.4f}")
            break
        except Exception:
            continue

def vender():
    registro = cargar_registro()
    nuevos_registro = {}
    for symbol in list(registro):
        try:
            cantidad = registro[symbol]["cantidad"]
            precio_compra = registro[symbol]["precio_compra"]
            trades = client.get_recent_trades(symbol=symbol)
            precio_actual = float(trades[-1]["price"]) if trades else precio_compra
            cambio = (precio_actual - precio_compra) / precio_compra

            if cambio >= TAKE_PROFIT or cambio <= STOP_LOSS:
                client.order_market_sell(symbol=symbol, quantity=cantidad)
                enviar_telegram(f"🔴 Vendido {symbol} - {cantidad:.4f} a {precio_actual:.4f} (Cambio: {cambio*100:.2f}%)")
            else:
                nuevos_registro[symbol] = registro[symbol]
        except Exception:
            nuevos_registro[symbol] = registro[symbol]
    guardar_registro(nuevos_registro)

def resumen_diario():
    cuenta = client.get_account()
    mensaje = "📊 Resumen diario:\n"
    for b in cuenta["balances"]:
        total = float(b["free"]) + float(b["locked"])
        if total > 0:
            mensaje += f"{b['asset']}: {total:.4f}\n"
    enviar_telegram(mensaje)

enviar_telegram("🤖 Bot IA activo. Operando con USDC de forma inteligente.")

scheduler = BackgroundScheduler(timezone=TIMEZONE)
scheduler.add_job(comprar, 'interval', seconds=30)
scheduler.add_job(vender, 'interval', seconds=30)
scheduler.add_job(resumen_diario, 'cron', hour=RESUMEN_HORA, minute=0)
scheduler.start()

while True:
    time.sleep(10)
