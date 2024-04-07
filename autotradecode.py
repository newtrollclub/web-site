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

# 선택된 코인을 저장할 전역 변수
selected_coins = []

def get_top_return_coins(n=2):
    tickers = pyupbit.get_tickers(fiat="KRW")
    returns = []
    for ticker in tickers:
        try:
            ohlcv = pyupbit.get_ohlcv(ticker, interval="day", count=7)
            if ohlcv is not None and len(ohlcv) >= 7:
                weekly_return = (ohlcv['close'].iloc[-1] - ohlcv['close'].iloc[0]) / ohlcv['close'].iloc[0]
                returns.append((ticker, weekly_return))
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    sorted_returns = sorted(returns, key=lambda x: x[1], reverse=True)
    return [ticker for ticker, _ in sorted_returns[:n]]

def select_coins():
    global selected_coins
    selected_coins = get_top_return_coins(2)
    print(f"Selected coins: {selected_coins}", datetime.now())
    # 여기에 추가 로그
    print(f"After selecting coins: {selected_coins}")

def fetch_data(coin):
    """10분 간격 데이터를 받아와서 기술적 지표를 계산합니다."""
    try:
        df = pyupbit.get_ohlcv(f"KRW-{coin}", interval="minute10", count=120)
        if df is None:
            print(f"No data returned for {coin}")
            return pd.DataFrame()  # 빈 데이터 프레임 반환

        df['SMA_20'] = ta.sma(df['close'], length=20)
        df['SMA_60'] = ta.sma(df['close'], length=60)
        df['SMA_120'] = ta.sma(df['close'], length=120)
        df['Volume_MA'] = ta.sma(df['volume'], length=20)
        return df
    except Exception as e:
        print(f"Error fetching data for {coin}: {e}")
        return pd.DataFrame()  # 예외 발생 시 빈 데이터 프레임 반환

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

def main():
    print(f"{datetime.now()} - Running main function.")
    if not selected_coins:
        print("No coins selected yet. Skipping trade execution.")
        return
    for coin in selected_coins:
        print(f"Deciding action for {coin}")
        df = fetch_data(coin)
        if df.empty:
            print(f"No data returned for {coin}")
            continue
        decision, decision_reason = decide_action(df, coin)
        print(f"Decision: {decision}, Reason: {decision_reason}")

# 스케줄 설정 및 실행
schedule.every(10).minutes.do(main)
schedule.every().day.at("00:00").do(select_coins)

if __name__ == "__main__":
    select_coins()  # 최초 실행 시 코인 선택
    main()  # 최초 실행 시에도 매수/매도 결정 및 실행
    while True:
        schedule.run_pending()
        time.sleep(1)
