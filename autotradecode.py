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

def fetch_data(coin):
    # 10분 간격 데이터
    df = pyupbit.get_ohlcv(f"KRW-{coin}", interval="minute10", count=120)
    # 기술적 지표 추가
    df['SMA_20'] = ta.sma(df['close'], length=20)
    df['SMA_60'] = ta.sma(df['close'], length=60)
    df['SMA_120'] = ta.sma(df['close'], length=120)
    df['Volume_MA'] = ta.sma(df['volume'], length=20)   # 거래량의 20기간 이동평균
    return df

def decide_action(df, coin):
    last_row = df.iloc[-1]
    decision_reason = ""
    if last_row['SMA_20'] > last_row['SMA_60'] > last_row['SMA_120'] and last_row['volume'] > df['volume'].mean():
        decision = "buy"
        decision_reason = f"{coin}: SMA_20 > SMA_60 > SMA_120 and have more current volume than average volume."
    elif last_row['SMA_20'] < last_row['SMA_60'] or last_row['SMA_20'] < last_row['SMA_120']:
        decision = "sell"
        decision_reason = f"{coin}: SMA_20 is lower than SMA_60 or SMA_120."
    else:
        decision = "hold"
        decision_reason = f"{coin}: Current conditions do not meet buy or sell criteria."
    return decision, decision_reason

def execute_trade(decision, decision_reason, coin):
    print(f"{datetime.now()} - Decision: {decision}, Reason: {decision_reason}")
    try:
        if decision == "buy":
            krw_balance = upbit.get_balance("KRW")
            if krw_balance > 5000:  # 최소 거래 금액 조건 확인
                response = upbit.buy_market_order(f"KRW-{coin}", krw_balance * 0.9995)  # 수수료 고려
                print(f"Buy order executed: {response}")
        elif decision == "sell":
            coin_balance = float(upbit.get_balance(coin))
            if coin_balance > 0.00008:  # 최소 거래 단위 조건 확인
                response = upbit.sell_market_order(f"KRW-{coin}", coin_balance)
                print(f"Sell order executed: {response}")
    except Exception as e:
        print(f"Error executing trade: {e}")

def main():
    print(f"{datetime.now()} - Running main function.")
    for coin in ["BTC", "BORA"]:
        df = fetch_data(coin)
        decision, decision_reason = decide_action(df, coin)
        execute_trade(decision, decision_reason, coin)

# 스케줄 설정 및 실행
schedule.every(10).minutes.do(main)

if __name__ == "__main__":
    main()  # 최초 실행
    while True:
        schedule.run_pending()
        time.sleep(1)
