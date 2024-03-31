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

def get_total_krw_value():
    """사용자의 전체 자산 중 원화(KRW) 및 각 코인의 현재 원화 가치를 합산하여 총 원화 가치를 계산합니다."""
    total_krw_value = 0
    balances = upbit.get_balances()
    for balance in balances:
        if balance['currency'] == "KRW":
            total_krw_value += float(balance['balance'])
        else:
            ticker = f"KRW-{balance['currency']}"
            current_price = pyupbit.get_current_price(ticker)
            if current_price:
                total_krw_value += current_price * float(balance['balance'])
    return total_krw_value

def fetch_data(coin):
    """10분 간격 데이터를 받아와서 기술적 지표를 계산합니다."""
    df = pyupbit.get_ohlcv(f"KRW-{coin}", interval="minute10", count=120)
    df['SMA_20'] = ta.sma(df['close'], length=20)
    df['SMA_60'] = ta.sma(df['close'], length=60)
    df['SMA_120'] = ta.sma(df['close'], length=120)
    df['Volume_MA'] = ta.sma(df['volume'], length=20)
    return df

def decide_action(df, coin):
    """매수, 매도, 보유 결정을 내립니다."""
    last_row = df.iloc[-1]
    is_bullish_candle = last_row['close'] > last_row['open']
    volume_increasing_trend = last_row['volume'] > last_row['Volume_MA']

    if (last_row['SMA_20'] > last_row['SMA_60'] > last_row['SMA_120'] and 
        volume_increasing_trend and 
        is_bullish_candle):
        decision = "buy"
        decision_reason = f"{coin}: SMA_20 > SMA_60 > SMA_120, 거래량 증가 추세 및 양봉 확인."
    elif last_row['SMA_20'] < last_row['SMA_60'] or last_row['SMA_20'] < last_row['SMA_120']:
        decision = "sell"
        decision_reason = f"{coin}: SMA_20이 SMA_60 또는 SMA_120보다 낮습니다."
    else:
        decision = "hold"
        decision_reason = f"{coin}: 매수 또는 매도 조건에 해당하지 않습니다."

    return decision, decision_reason

def execute_trade(decision, decision_reason, coin, total_krw_value, num_coins=2):
    """매수 또는 매도 결정을 실행합니다."""
    print(f"{datetime.now()} - Decision: {decision}, Reason: {decision_reason}")
    max_investment_per_coin = total_krw_value / num_coins
    try:
        if decision == "buy":
            krw_balance = upbit.get_balance("KRW")
            investment_amount = min(krw_balance, max_investment_per_coin)
            if investment_amount > 5000:  # 최소 거래 금액 조건 확인
                response = upbit.buy_market_order(f"KRW-{coin}", investment_amount * 0.9995)  # 수수료 고려
                print(f"Buy order executed: {response}")
        elif decision == "sell":
            coin_balance = float(upbit.get_balance(coin))
            current_price = pyupbit.get_current_price(f"KRW-{coin}")
            if coin_balance * current_price > 5000:  # 최소 거래 가치 조건 확인
                response = upbit.sell_market_order(f"KRW-{coin}", coin_balance)
                print(f"Sell order executed: {response}")
    except Exception as e:
        print(f"Error executing trade: {e}")

def main():
    print(f"{datetime.now()} - Running main function.")
    total_krw_value = get_total_krw_value()  # 전체 KRW 가치 계산
    num_coins = len(["BTC", "BORA"])  # 코인 종류의 수
    for coin in ["BTC", "BORA"]:
        df = fetch_data(coin)
        decision, decision_reason = decide_action(df, coin)
        execute_trade(decision, decision_reason, coin, total_krw_value, num_coins)

# 스케줄 설정 및 실행
schedule.every(10).minutes.do(main)

if __name__ == "__main__":
    main()  # 최초 실행
    while True:
        schedule.run_pending()
        time.sleep(1)
