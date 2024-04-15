import os
from dotenv import load_dotenv
import pyupbit
import pandas as pd
import pandas_ta as ta
import schedule
import time
from datetime import datetime

# 환경 변수 로드
load_dotenv()
access_key = os.getenv("UPBIT_ACCESS_KEY")
secret_key = os.getenv("UPBIT_SECRET_KEY")
upbit = pyupbit.Upbit(access_key, secret_key)
highest_profits = {}  # 각 코인의 최고 수익률을 기록하는 딕셔너리
bought_prices = {}  # 각 코인의 매수 가격을 기록하는 딕셔너리

def fetch_data(coin):
    """5분 간격 데이터를 받아와서 기술적 지표를 계산합니다."""
    df = pyupbit.get_ohlcv(f"KRW-{coin}", interval="minute5", count=120)
    # 최고가 기록
    df['High'] = df['close'].rolling(window=10).max()
    # RSI 계산
    df['RSI'] = ta.rsi(df['close'], length=14)
    return df

def calculate_profit_loss(coin):
    """수익률을 계산합니다."""
    df = fetch_data(coin)
    current_price = df.iloc[-1]['close']
    bought_price = bought_prices.get(coin)
    if bought_price is None:
        return None
    profit_loss = (current_price - bought_price) / bought_price
    return profit_loss

def decide_action(df, coin):
    """매수, 매도, 보유 결정을 내립니다."""
    current_profit = calculate_profit_loss(coin)
    highest_profit = highest_profits.get(coin)

    if current_profit is None or highest_profit is None:
        # 매수 이후 데이터가 없는 경우 또는 최고 수익률이 없는 경우
        return "hold", f"{coin}: 매수 이후 데이터가 없거나 최고 수익률이 없어 보유합니다."

    # RSI 값 계산
    rsi_value = ta.rsi(df['close'], length=14).iloc[-1]
    rsi_previous = ta.rsi(df['close'], length=14).shift(1).iloc[-1]

    # RSI가 30 이하이고 이전 값보다 증가하거나, RSI가 30 이하에서 30 이상으로 증가한 경우 매수
    if (rsi_value <= 30 and rsi_value > rsi_previous) or (rsi_previous <= 30 and rsi_value > 30 and rsi_value > rsi_previous):
        return "buy", f"{coin}: RSI가 30 이하에서 증가하였거나 30 이하에서 30 이상으로 증가하였으므로 매수합니다."
    else:
        # 매수 이후 최고 수익률이 3% 이상이면서 현재 수익률이 최고 수익률의 70% 이하로 떨어졌을 때 매도
        if highest_profit > 0.03 and current_profit <= highest_profit * 0.70:
            return "sell", f"{coin}: 최고 수익률이 3% 이상이었고 현재 수익률이 최고 수익률의 70% 이하로 하락하였으므로 매도합니다."
        else:
            return "hold", f"{coin}: 매도 조건을 만족하지 않아 보유합니다."

def execute_trade(decision, decision_reason, coin):
    """매수 또는 매도 결정을 실행합니다."""
    print(f"{datetime.now()} - Decision: {decision}, Reason: {decision_reason}")
    try:
        if decision == "buy":
            krw_balance = upbit.get_balance("KRW")  # 사용 가능한 KRW 잔액
            current_price = pyupbit.get_current_price(f"KRW-{coin}")  # 해당 코인의 현재 가격

            # 추가로 매수 가능한 최대 금액 계산
            max_additional_buy = krw_balance / 2

            if max_additional_buy > 5000:  # 최소 거래 금액 조건 확인
                investment_amount = min(max_additional_buy, krw_balance)
                response = upbit.buy_market_order(f"KRW-{coin}", investment_amount * 0.9995)  # 수수료 고려
                print(f"Buy order executed for {coin}: {response}")
                bought_prices[coin] = current_price  # 매수한 가격 기록
        elif decision == "sell":
            coin_balance = float(upbit.get_balance(coin))
            if coin_balance > 0:  # 보유한 코인이 있는지 확인
                response = upbit.sell_market_order(f"KRW-{coin}", coin_balance)
                print(f"Sell order executed for {coin}: {response}")
                bought_prices.pop(coin)  # 매도한 코인의 매수 가격 기록 제거
    except Exception as e:
        print(f"Error executing trade for {coin}: {e}")

def main():
    print(f"{datetime.now()} - Running main function.")
    for coin in ["BTC", "BORA", "SOL", "ETH", "DOGE"]:
        df = fetch_data(coin)
        highest_profits[coin] = calculate_highest_profit(coin)
        decision, decision_reason = decide_action(df, coin)
        execute_trade(decision, decision_reason, coin)

def calculate_highest_profit(coin):
    """코인의 최고 수익률을 계산하고 기록합니다."""
    df = fetch_data(coin)
    highest_price = df['close'].max()
    bought_price = bought_prices.get(coin)
    if bought_price is None:
        return None
    highest_profit = (highest_price - bought_price) / bought_price
    highest_profits[coin] = highest_profit
    return highest_profit

# 스케줄 설정 및 실행
schedule.every(5).minutes.do(main)

if __name__ == "__main__":
    main()  # 최초 실행
    while True:
        schedule.run_pending()
        time.sleep(1)
