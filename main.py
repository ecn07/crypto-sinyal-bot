import asyncio
import requests
import pandas as pd
from telegram import Bot

# Telegram ayarları
TOKEN = "8107305284:AAHpE6C6wS8JuzW_4Hd-HJMuGqVPI0q45XI"
CHAT_IDS = [1542821447]
bot = Bot(token=TOKEN)

def get_top_20_symbols():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = requests.get(url).json()
    filtered = [d for d in data if d['symbol'].endswith('USDT') and float(d['quoteVolume']) > 0]
    filtered = sorted(filtered, key=lambda x: float(x['quoteVolume']), reverse=True)
    return [x['symbol'] for x in filtered[:20]]

def get_klines(symbol, interval='1h', limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=[
        'open_time','open','high','low','close','volume',
        'close_time','quote_asset_volume','number_of_trades',
        'taker_buy_base_asset_volume','taker_buy_quote_asset_volume','ignore'])
    df['close'] = df['close'].astype(float)
    return df

def calculate_indicators(df):
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    def mad(x):
        return (x - x.mean()).abs().mean()
    df['mad'] = df['close'].rolling(window=14).apply(mad, raw=False)

    return df

def generate_signal(rsi, close, ema_20, mad):
    if pd.isna(rsi) or pd.isna(ema_20) or pd.isna(mad):
        return "Neutral", 0

    confidence = 0
    signal = "Neutral"

    if rsi >= 70:
        signal = "SHORT"
        confidence += (rsi - 70) * 3
    elif rsi <= 30:
        signal = "LONG"
        confidence += (30 - rsi) * 3

    if signal == "SHORT" and close < ema_20:
        confidence += 15
    elif signal == "LONG" and close > ema_20:
        confidence += 15

    confidence += min(mad * 20, 20)

    if signal == "Neutral" or confidence < 10:
        return "Neutral", 0

    return signal, round(min(confidence, 100), 1)

def calculate_entry_exit(close, signal):
    if signal == "LONG":
        entry = close * 1.05
        exit_price = close * 0.95
    elif signal == "SHORT":
        entry = close * 0.95
        exit_price = close * 1.05
    else:
        entry = 0.0
        exit_price = 0.0
    return round(entry, 6), round(exit_price, 6)

def get_24h_high_low(symbol):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    data = requests.get(url).json()
    try:
        high = float(data.get('highPrice', 0))
        low = float(data.get('lowPrice', 0))
    except:
        high, low = 0.0, 0.0
    return high, low

def estimate_time_to_target(df, close, target, interval_minutes):
    df = df.tail(15)  # son 15 mum
    price_changes = df['close'].diff().abs().dropna()
    avg_change_per_candle = price_changes.mean()
    if avg_change_per_candle == 0:
        return None

    price_diff = abs(close - target)
    candles_needed = price_diff / avg_change_per_candle
    minutes_needed = candles_needed * interval_minutes
    if minutes_needed > 240:  # max 4 saat
        return None
    return minutes_needed

def format_price(price):
    if price >= 1:
        formatted = f"{price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        formatted = f"{price:.8f}".rstrip('0').rstrip('.').replace('.', ',')
    return f"{formatted} $"

def format_time(minutes):
    if minutes is None:
        return "Belirsiz"
    if minutes > 60:
        hours = minutes / 60
        return f"{hours:.2f} saat"
    else:
        return f"{int(minutes)} dk"

def send_telegram_message_sync(message):
    for chat_id in CHAT_IDS:
        bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

async def main():
    intervals = ['15m', '30m', '1h']
    interval_minutes_map = {'15m': 15, '30m': 30, '1h': 60}
    symbols = get_top_20_symbols()

    for symbol in symbols:
        best_signal = None
        best_confidence = -1
        best_interval = None
        best_entry = 0.0
        best_exit = 0.0
        best_rsi = 0.0
        best_ema = 0.0
        best_mad = 0.0
        best_close = 0.0
        best_time_to_target = None
        high_24h, low_24h = get_24h_high_low(symbol)

        for interval in intervals:
            df = get_klines(symbol, interval=interval)
            df = calculate_indicators(df)
            last = df.iloc[-1]

            signal, confidence = generate_signal(last['rsi'], last['close'], last['ema_20'], last['mad'])
            if signal == "Neutral":
                continue

            entry, exit_price = calculate_entry_exit(last['close'], signal)
            minutes_to_target = estimate_time_to_target(df, last['close'], entry, interval_minutes_map[interval])

            if confidence > best_confidence:
                best_confidence = confidence
                best_signal = signal
                best_interval = interval
                best_entry = entry
                best_exit = exit_price
                best_rsi = last['rsi']
                best_ema = last['ema_20']
                best_mad = last['mad']
                best_close = last['close']
                best_time_to_target = minutes_to_target

        if best_signal is None:
            continue

        emoji = {
            "LONG": "📈",
            "SHORT": "📉"
        }.get(best_signal, "⚪️")

        message = (
            f"🚀 *Ecn Sinyal*\n\n"
            f"🪙 *Coin:* {symbol}\n"
            f"💰 *Güncel Fiyat:* {format_price(best_close)}\n"
            f"⏳ *Zaman Dilimi:* {best_interval}\n"
            f"📉 *Sinyal:* {best_signal} {emoji} (%{best_confidence})\n\n"
            f"📊 *RSI(14):* {best_rsi:.2f}\n"
            f"📈 *EMA(20):* {format_price(best_ema)}\n"
            f"📉 *MAD(14):* {best_mad:.4f}\n"
            f"🔺 *Günün En Yükseği:* {format_price(high_24h)}\n"
            f"🔻 *Günün En Düşüğü:* {format_price(low_24h)}\n\n"
            f"🎯 *Hedef fiyat:* {format_price(best_entry)}\n"
            f"🛑 *Stop loss:* {format_price(best_exit)}\n"
            f"⏱ *Tahmini hedefe ulaşma süresi:* {format_time(best_time_to_target)}\n\n"
            f"✨ *Ecn farkı!*"
        )

        send_telegram_message_sync(message)

if __name__ == "__main__":
    asyncio.run(main())
