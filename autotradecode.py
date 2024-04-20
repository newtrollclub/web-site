import os
from dotenv import load_dotenv
import pyupbit
import logging
import pandas as pd
import pandas_ta as ta
import schedule
import time
import json
from datetime import datetime

# 환경 변수 로드
load_dotenv()
access_key = os.getenv("UPBIT_ACCESS_KEY")
secret_key = os.getenv("UPBIT_SECRET_KEY")
upbit = pyupbit.Upbit(access_key, secret_key)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

# 매수 가격 정보를 저장하거나 불러오는 파일명
prices_file = 'bought_prices.json'
highest_profits_file = 'highest_profits.json'

def save_prices(prices):
    with open(prices_file, 'w') as file:
        json.dump(prices, file)

def load_prices():
    try:
        with open(prices_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_highest_profits(profits):
    with open(highest_profits_file, 'w') as file:
        json.dump(profits, file)

def load_highest_profits():
    try:
        with open(highest_profits_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# 매수 가격 정보와 최고 수익률 정보를 불러옵니다.
bought_prices = load_prices()
highest_profits = load_highest_profits()

def sync_and_backup_prices():
    """API로부터 계좌 정보를 가져오고 로컬 파일에 백업합니다."""
    try:
        balances = upbit.get_balances()
        prices = {}
        for item in balances:
            if item['currency'] in ["BTC", "BORA", "SOL", "ETH", "DOGE"]:
                currency = f"KRW-{item['currency']}"
                prices[currency] = float(item['avg_buy_price'])
        save_prices(prices)
        logging.info("Account prices updated and backed up successfully.")
    except Exception as e:
        logging.error(f"Failed to update prices from API, will use backup data: {e}")
        return load_prices()

def fetch_data(coin):
    """5분 간격 데이터를 받아와서 기술적 지표를 계산합니다."""
    df = pyupbit.get_ohlcv(f"KRW-{coin}", interval="minute5", count=120)
    df['High'] = df['close'].rolling(window=10).max()
    df['RSI'] = ta.rsi(df['close'], length=14)
    return df

def calculate_profit_loss(coin):
    """수익률을 계산합니다."""
    df = fetch_data(coin)
    current_price = df.iloc[-1]['close']
    bought_price = bought_prices.get(f"KRW-{coin}", None)
    if bought_price is None or bought_price == 0:
        logging.info(f'{coin}: No bought price available, unable to calculate profit/loss.')
        return 0
    profit_loss = (current_price - bought_price) / bought_price
    highest_profit = highest_profits.get(coin, 0)

    logging.info(f'{coin}: Current price = {current_price}, Bought price = {bought_price}, Profit/Loss = {profit_loss}, Highest Profit = {highest_profit}')

    
    # 최고 수익률 업데이트 및 저장
    highest_profit = highest_profits.get(coin, 0)
    if profit_loss > highest_profit:
        highest_profits[coin] = profit_loss
        save_highest_profits(highest_profits)
        logging.info(f'Updated highest profit for {coin}: {profit_loss:.2%}')

    return profit_loss

def decide_action(df, coin):
    """매수, 매도, 보유 결정을 내립니다."""
    current_profit = calculate_profit_loss(coin)
    highest_profit = highest_profits.get(coin, 0)
    rsi_value = ta.rsi(df['close'], length=14).iloc[-1]
    rsi_previous = ta.rsi(df['close'], length=14).shift(1).iloc[-1]

    logging.debug(f'{coin}: RSI Current = {rsi_value}, RSI Previous = {rsi_previous}')
    logging.debug(f'{coin}: Current Profit = {current_profit}, Highest Profit = {highest_profit}')

    if (rsi_value <= 30 and rsi_value > rsi_previous) or (rsi_previous <= 30 and rsi_value > 30 and rsi_value > rsi_previous):
        logging.info(f'{coin}: Condition for BUY met.')
        return "buy", f"{coin}: RSI가 30 이하에서 증가하였거나 30 이하에서 30 이상으로 증가하였으므로 매수합니다."
    else:
        logging.info(f'{coin}: Conditions for BUY not met, evaluating SELL conditions.')
        if highest_profit <= 0.03 and current_profit <= highest_profit - 0.01:
            logging.info(f'{coin}: Condition for SELL met. Profit drop detected.')
            return "sell", f"{coin}: 최고 수익률이 3% 이하이고 현재 수익률이 최고 수익률 대비 1% 포인트 하락하였으므로 매도합니다."
        elif highest_profit > 0.03 and current_profit <= highest_profit * 0.70:
            logging.info(f'{coin}: Condition for SELL met. Significant profit reduction.')
            return "sell", f"{coin}: 최고 수익률이 3% 이상이었고 현재 수익률이 최고 수익률의 70% 이하로 하락하였으므로 매도합니다."
        else:
            logging.info(f'{coin}: Condition for SELL not met. Holding.')
            return "hold", f"{coin}: 매도 조건을 만족하지 않아 보유합니다."

def execute_trade(decision, decision_reason, coin):
    """매수 또는 매도 결정을 실행합니다."""
    print(f"{datetime.now()} - Decision: {decision}, Reason: {decision_reason}")
    try:
        if decision == "buy":
            krw_balance = upbit.get_balance("KRW")
            if krw_balance > 5000:
                investment_amount = krw_balance / 2
                response = upbit.buy_market_order(f"KRW-{coin}", investment_amount)
                print(f"Buy order executed for {coin}: {response}")
        elif decision == "sell":
            coin_balance = float(upbit.get_balance(coin))
            if coin_balance > 0:
                response = upbit.sell_market_order(f"KRW-{coin}", coin_balance)
                print(f"Sell order executed for {coin}: {response}")
                bought_prices.pop(coin)  # Remove from prices dictionary
                save_prices(bought_prices)  # Save the updated prices to file
    except Exception as e:
        print(f"Error executing trade for {coin}: {e}")

def main():
    """메인 함수에서 모든 코인에 대해 데이터를 가져오고 RSI 및 수익률을 로깅합니다."""
    sync_and_backup_prices()  # 계좌 정보 동기화 및 백업
    print(f"{datetime.now()} - Running main function.")
    for coin in ["BTC", "BORA", "SOL", "ETH", "DOGE"]:
        df = fetch_data(coin)
        current_rsi = df['RSI'].iloc[-1]
        current_profit_loss = calculate_profit_loss(coin)
        logging.info(f'{coin}: RSI = {current_rsi}, Profit/Loss = {current_profit_loss}')
        decision, decision_reason = decide_action(df, coin)
        execute_trade(decision, decision_reason, coin)

# 스케줄 설정 및 실행
schedule.every(5).minutes.do(main)

if __name__ == "__main__":
    main()
    while True:
        schedule.run_pending()
        time.sleep(1)
