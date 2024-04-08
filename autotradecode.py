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
    """10분 간격 데이터를 받아와서 기술적 지표를 계산합니다."""
    df = pyupbit.get_ohlcv(f"KRW-{coin}", interval="minute10", count=120)
    # 최고가 기록
    df['High'] = df['close'].rolling(window=10).max()
    # RSI 계산
    df['RSI'] = ta.rsi(df['close'], length=14)
    return df

def calculate_profit_loss(df):
    """수익률을 계산합니다."""
    current_price = df.iloc[-1]['close']
    highest_price = df['close'].rolling(window=10).max().iloc[-1]
    profit_loss = (current_price - highest_price) / highest_price
    return profit_loss

def calculate_highest_profit(df):
    """코인의 최고 수익률을 계산합니다."""
    highest_price = df['close'].max()
    buy_price = df.iloc[0]['open']  # 처음 매수한 가격
    highest_profit = (highest_price - buy_price) / buy_price
    return highest_profit

def decide_action(df, coin, highest_profit):
    """매수, 매도, 보유 결정을 내립니다."""
    last_row = df.iloc[-1]
    current_price = last_row['close']
    
    # 현재 수익률 계산
    buy_price = df.iloc[0]['open']  # 처음 매수한 가격
    current_profit = (current_price - buy_price) / buy_price
    
    # 최고 수익률 대비 현재 수익률의 하락 비율 계산
    profit_loss = (highest_profit - current_profit) / highest_profit

    # RSI 값 계산
    rsi_value = ta.rsi(df['close'], length=14).iloc[-1]

    # 매수 조건: RSI 30 이하
    if rsi_value <= 30:
        decision = "buy"
        decision_reason = f"{coin}: RSI가 30 이하이므로 매수합니다."
    else:
        # 매도 조건: 수익률이 1% 이상이고, 최고 수익률 대비 -1% 이상 하락하거나 RSI가 70 이상
        if current_profit >= 0.01:  
            if profit_loss >= 0.01 or rsi_value >= 70:
                decision = "sell"
                decision_reason = f"{coin}: 최고 수익률 대비 -1% 이상 하락하거나 RSI가 70 이상이므로 매도합니다."
            else:
                decision = "hold"
                decision_reason = f"{coin}: 수익률이 1% 이상이지만 매도 조건을 만족하지 않아 보유합니다."
        else:
            decision = "hold"
            decision_reason = f"{coin}: 매도 조건을 만족하지 않아 보유합니다."

    return decision, decision_reason

def execute_trade(decision, decision_reason, coin):
    """매수 또는 매도 결정을 실행합니다."""
    print(f"{datetime.now()} - Decision: {decision}, Reason: {decision_reason}")
    try:
        if decision == "buy":
            # 매수 로직 추가
            pass
        elif decision == "sell":
            # 매도 로직 추가
            pass
    except Exception as e:
        print(f"Error executing trade: {e}")

def main():
    print(f"{datetime.now()} - Running main function.")
    for coin in ["BTC", "BORA"]:
        df = fetch_data(coin)
        highest_profit = calculate_highest_profit(df)
        decision, decision_reason = decide_action(df, coin, highest_profit)
        execute_trade(decision, decision_reason, coin)

# 스케줄 설정 및 실행
schedule.every(10).minutes.do(main)

if __name__ == "__main__":
    main()  # 최초 실행
    while True:
        schedule.run_pending()
        time.sleep(1)
