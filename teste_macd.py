import yfinance as yf
import pandas as pd
import os

os.makedirs("macd_graficos", exist_ok=True)

# Ler apenas os primeiros 3 ativos para teste rápido
tickers = ["PETR4.SA", "VALE3.SA", "ITUB4.SA"]

for ticker in tickers:
    try:
        print(f"Processando {ticker}...", end=" ", flush=True)
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=False, progress=False, threads=False)
        
        # Calcular MACD
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['HISTOGRAM'] = df['MACD'] - df['SIGNAL']
        
        # Detectar cruzamento no último candle
        if len(df) >= 2:
            macd_prev = df['MACD'].iloc[-2]
            signal_prev = df['SIGNAL'].iloc[-2]
            macd_curr = df['MACD'].iloc[-1]
            signal_curr = df['SIGNAL'].iloc[-1]
            
            # Cruzamento: MACD passou de baixo para cima da SIGNAL ou vice-versa
            if (macd_prev < signal_prev and macd_curr >= signal_curr) or \
               (macd_prev > signal_prev and macd_curr <= signal_curr):
                print(f"✓ CRUZAMENTO DETECTADO!")
            else:
                print("OK")
        else:
            print("Sem dados suficientes")
    except Exception as e:
        print(f"Erro: {e}")

print("\nTeste concluído!")
