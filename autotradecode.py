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

    # 양봉 확인: 종가 > 시가
    is_bullish_candle = last_row['close'] > last_row['open']
    # 거래량 증가 추세 확인: 현재 거래량 > 20기간 거래량 이동 평균
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
    """전체 KRW 가치를 기반으로 투자할 금액을 계산하고 거래를 실행합니다."""
    print(f"{datetime.now()} - Decision: {decision}, Reason: {decision_reason}")
    try:
        max_investment_per_coin = total_krw_value / num_coins
    except Exception as e:
        print(f"Error executing trade: {e}")
