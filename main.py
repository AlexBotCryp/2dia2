import time
import openai
import requests
import telegram
from binance.client import Client
from binance.enums import *
import os

# === CONFIGURACIÓN DEL USUARIO ===
# Claves API de Binance
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# OpenAI GPT
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Criptomonedas objetivo
COINS = ["BTCUSDC", "DOGEUSDC", "TRXUSDC"]

# Parámetros
MIN_USDC = 10  # mínimo requerido para operar
MARGIN = 0.004  # margen de beneficio deseado (0.4%)
INTERVAL = 20  # segundos entre cada análisis

# === INICIALIZACIÓN ===
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
openai.api_key = OPENAI_API_KEY
bot = telegram.Bot(token=TELEGRAM_TOKEN)

def get_balance(symbol="USDC"):
    balance = client.get_asset_balance(asset=symbol)
    return float(balance['free']) if balance else 0.0

def get_price(symbol):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def send_telegram(message):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

def analyze_market():
    prompt = f"""
    Analiza el mercado actual de {COINS}. Basado en volumen, variación de precio, y comportamiento reciente,
    decide cuál tiene mejor potencial para microtrading en los próximos minutos. 
    Responde solo con el símbolo exacto (ej: BTCUSDC, TRXUSDC o DOGEUSDC).
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Error en GPT:", e)
        return None

def trade():
    usdc_balance = get_balance("USDC")

    if usdc_balance >= MIN_USDC:
        symbol = analyze_market()
        if symbol not in COINS:
            print("Respuesta inválida de IA:", symbol)
            return

        price = get_price(symbol)
        qty = round(usdc_balance / price * 0.98, 5)  # usa 98% del balance para evitar errores

        try:
            order = client.order_market_buy(symbol=symbol, quantity=qty)
            send_telegram(f"✅ Comprado {qty} de {symbol} a {price}")
        except Exception as e:
            print("Error al comprar:", e)

    else:
        # Si no hay USDC, intentamos vender lo que tengamos
        for coin in COINS:
            coin_name = coin.replace("USDC", "")
            balance = get_balance(coin_name)
            if balance >= 1 or (coin_name == "BTC" and balance >= 0.0001):
                try:
                    price = get_price(coin)
                    sell_qty = round(balance * 0.98, 5)
                    client.order_market_sell(symbol=coin, quantity=sell_qty)
                    send_telegram(f"❌ Vendido {sell_qty} de {coin_name} a {price} por falta de USDC")
                except Exception as e:
                    print(f"Error vendiendo {coin_name}:", e)

# === BUCLE PRINCIPAL ===
while True:
    try:
        trade()
        time.sleep(INTERVAL)
    except Exception as e:
        print("Error general:", e)
        time.sleep(30)
