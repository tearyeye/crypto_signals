from flask import Flask, render_template
import numpy as np
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from scipy.stats import norm

app = Flask(__name__)

HISTORICAL_API_URL = "https://api.delta.exchange/v2/history/candles"
TICKER_API_URL = "https://api.delta.exchange/v2/tickers"

def fetch_data(symbol):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    if now.hour < 17 or (now.hour == 17 and now.minute < 30):
        last_close = (now - timedelta(days=1)).replace(hour=17, minute=30, second=0, microsecond=0)
    else:
        last_close = now.replace(hour=17, minute=30, second=0, microsecond=0)
    
    last_close_utc = last_close.astimezone(pytz.utc)
    start_date = last_close - timedelta(days=7)
    start_date_utc = start_date.astimezone(pytz.utc)
    
    start_timestamp = int(start_date_utc.timestamp())
    end_timestamp = int(datetime.now(pytz.utc).timestamp())

    params = {
        "symbol": symbol,
        "resolution": "1d",
        "start": start_timestamp,
        "end": end_timestamp
    }
    
    headers = {
        "Accept": "application/json"
    }

    response = requests.get(HISTORICAL_API_URL, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if not data['result']:
            raise Exception(f"No data received for {symbol} from API.")
        df = pd.DataFrame(data["result"])
        df["time"] = pd.to_datetime(df["time"], unit='s')
        df.set_index("time", inplace=True)
        return df
    else:
        raise Exception(f"Error fetching data for {symbol}: {response.status_code} - {response.text}")

def fetch_current_price(symbol):
    response = requests.get(TICKER_API_URL)
    if response.status_code == 200:
        data = response.json()
        for ticker in data['result']:
            if ticker['symbol'] == symbol:
                return ticker['close']
        raise Exception(f"{symbol} ticker not found in response.")
    else:
        raise Exception(f"Error fetching current price for {symbol}: {response.status_code} - {response.text}")

def calculate_parameters(data):
    data['Daily Return'] = data['close'].pct_change()
    mu = data['Daily Return'].mean()
    sigma = data['Daily Return'].std()
    return mu, sigma

def simulate_prices(S0, mu, sigma, T=1, num_simulations=10000):
    prices = []
    for _ in range(num_simulations):
        W_T = np.random.normal(0, 1)
        S_T = S0 * np.exp((mu - 0.5 * sigma**2) * T + sigma * W_T * np.sqrt(T))
        prices.append(S_T)

    price_5th_percentile = np.percentile(prices, 5)
    price_95th_percentile = np.percentile(prices, 95)
    return price_5th_percentile, price_95th_percentile

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/btc')
def btc_levels():
    try:
        data = fetch_data('BTCUSD')
        current_price = fetch_current_price('BTCUSD')
        mu, sigma = calculate_parameters(data)
        price_5th_percentile, price_95th_percentile = simulate_prices(current_price, mu, sigma)
        return f"${price_5th_percentile:.2f} to ${price_95th_percentile:.2f}"
    except Exception as e:
        return f"Error: {e}"

@app.route('/eth')
def eth_levels():
    try:
        data = fetch_data('ETHUSD')
        current_price = fetch_current_price('ETHUSD')
        mu, sigma = calculate_parameters(data)
        price_5th_percentile, price_95th_percentile = simulate_prices(current_price, mu, sigma)
        return f"${price_5th_percentile:.2f} to ${price_95th_percentile:.2f}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == '__main__':
    app.run(debug=True)
