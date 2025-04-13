import streamlit as st
import requests
import pandas as pd
import os
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from datetime import datetime

st.set_page_config(page_title="Sniper XRP", layout="wide")
st.title("🎯 Assistant Sniper - XRP")

CMC_API_KEY = "f006ad5a-b9cb-4992-aea9-0d041baae842"
TELEGRAM_TOKEN = "7888257756:AAEw4_9voW1UxH0souXHTU8qMtpmnkFUbPM"
TELEGRAM_CHAT_ID = "6590810363"
SYMBOL = "XRP"
CSV_FILE = "signaux_valides.csv"

@st.cache_data(ttl=120)
def get_price():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": CMC_API_KEY,
    }
    params = {"symbol": SYMBOL, "convert": "USD"}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    return float(data["data"][SYMBOL]["quote"]["USD"]["price"])

def calculate_indicators(prices):
    df = pd.DataFrame(prices, columns=['close'])
    rsi = RSIIndicator(close=df['close'], window=14).rsi().iloc[-1]
    ma10 = SMAIndicator(close=df['close'], window=10).sma_indicator().iloc[-1]
    ma30 = SMAIndicator(close=df['close'], window=30).sma_indicator().iloc[-1]
    return rsi, ma10, ma30

def detect_support(prices, tolerance=0.005):
    supports = []
    for i in range(2, len(prices)):
        if prices[i - 2] > prices[i - 1] < prices[i]:
            supports.append(prices[i - 1])
    if supports:
        last = supports[-1]
        return abs(prices[-1] - last) / last < tolerance
    return False

def save_signal_to_csv(timestamp, price, rsi, ma10, ma30):
    data = {
        "Date/Heure": [timestamp],
        "Prix": [price],
        "RSI": [rsi],
        "MA10": [ma10],
        "MA30": [ma30]
    }
    df = pd.DataFrame(data)
    if not os.path.exists(CSV_FILE):
        df.to_csv(CSV_FILE, index=False)
    else:
        df.to_csv(CSV_FILE, mode='a', header=False, index=False)

def load_signal_history():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        return pd.DataFrame()

def clear_signal_history():
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        st.error(f"Erreur d'envoi Telegram : {e}")

# Simule historique local
price_now = get_price()
history = [price_now] * 40

for _ in range(10):
    history.append(get_price())
    if len(history) > 100:
        history.pop(0)

rsi, ma10, ma30 = calculate_indicators(history)
support_ok = detect_support(history)

col1, col2, col3 = st.columns(3)

col1.metric("Prix actuel", f"{price_now:.4f} $")
col2.metric("RSI (14)", f"{rsi:.2f}", delta="🔻" if rsi < 30 else "")
col3.metric("MA10 vs MA30", f"{ma10:.4f} > {ma30:.4f}" if ma10 > ma30 else f"{ma10:.4f} < {ma30:.4f}")

st.markdown("---")

if rsi < 30 and ma10 > ma30 and support_ok:
    st.success("✅ Signal achat validé : RSI < 30, rebond support, MA10 > MA30")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_signal_to_csv(timestamp, price_now, rsi, ma10, ma30)
    message = (
        f"📈 Signal achat validé pour {SYMBOL} !\\n"
        f"Prix : {price_now:.4f} $\\n"
        f"RSI : {rsi:.2f} | MA10: {ma10:.4f} > MA30: {ma30:.4f}\\n"
        f"Lien : https://www.tradingview.com/symbols/{SYMBOL}USDT/"
    )
    send_telegram_message(message)
else:
    st.warning("🚫 Conditions non réunies pour un signal achat fiable.")

if st.button("✉️ Envoyer une alerte manuelle sur Telegram"):
    message = (
        f"📈 Alerte manuelle déclenchée pour {SYMBOL} !\\n"
        f"Prix : {price_now:.4f} $\\n"
        f"RSI : {rsi:.2f} | MA10: {ma10:.4f} | MA30: {ma30:.4f}\\n"
        f"Lien : https://www.tradingview.com/symbols/{SYMBOL}USDT/"
    )
    send_telegram_message(message)
    st.success("Alerte Telegram envoyée manuellement ✅")

st.markdown("[📊 Voir XRP sur TradingView](https://www.tradingview.com/symbols/XRPUSDT/)")

st.markdown("---")
st.subheader("📜 Historique des signaux validés")

col4, col5 = st.columns([1, 1])

with col4:
    if st.button("🗑️ Vider l'historique"):
        clear_signal_history()
        st.success("Historique supprimé avec succès !")

with col5:
    history_df = load_signal_history()
    if not history_df.empty:
        csv = history_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger l'historique (.csv)",
            data=csv,
            file_name='signaux_valides.csv',
            mime='text/csv'
        )

history_df = load_signal_history()
if not history_df.empty:
    st.dataframe(history_df)
else:
    st.info("Aucun signal validé enregistré pour le moment.")
