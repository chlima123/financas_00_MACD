import yfinance as yf
from yfinance import exceptions as yf_exceptions
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import os
import time
from pathlib import Path

# Parâmetros do MACD
FAST = 12
SLOW = 26
SIGNAL = 9

# Criar pasta para gráficos
os.makedirs("macd_graficos", exist_ok=True)
CACHE_DIR = Path("cache_prices")
CACHE_DIR.mkdir(exist_ok=True)

def baixar_com_cache(ticker: str, lookback_update_days: int = 10, period_full: str = "2y") -> pd.DataFrame:
    """Baixa preços usando cache local em Parquet."""
    arq = CACHE_DIR / f"{ticker.replace('.', '_')}.parquet"

    def _download(period: str) -> pd.DataFrame:
        return yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )

    if arq.exists():
        try:
            df_old = pd.read_parquet(arq)
        except Exception:
            df_old = pd.DataFrame()
        try:
            df_new = _download(f"{lookback_update_days}d")
        except yf_exceptions.YFRateLimitError:
            return df_old if not df_old.empty else pd.DataFrame()
        except Exception:
            return df_old if not df_old.empty else pd.DataFrame()
        df = pd.concat([df_old, df_new]).sort_index()
        df = df[~df.index.duplicated(keep="last")]
    else:
        try:
            df = _download(period_full)
        except yf_exceptions.YFRateLimitError:
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    if df is not None and not df.empty:
        try:
            df.to_parquet(arq)
        except Exception:
            pass

    return df

def fetch_data(ticker: str, retries: int = 5, delay: int = 5) -> pd.DataFrame:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            data = baixar_com_cache(ticker, lookback_update_days=10, period_full="2y")
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [c[0] for c in data.columns]
            data = data[['Open', 'High', 'Low', 'Close', 'Volume']].apply(pd.to_numeric, errors='coerce')
            data = data.dropna(subset=['Open', 'High', 'Low', 'Close'])
            if data.empty:
                raise ValueError('Sem dados válidos retornados.')
            return data
        except Exception as e:
            last_err = e
            wait = delay * (2 ** (attempt - 1))
            if isinstance(e, yf_exceptions.YFRateLimitError):
                wait = max(wait, 60)
            print(f"[TENTATIVA {attempt}/{retries}] {ticker} falhou: {e}")
            if attempt < retries:
                time.sleep(wait)
    raise RuntimeError(f"Falha ao obter dados de {ticker} após {retries} tentativas: {last_err}")

def calcular_macd(data):
    data['EMA_fast'] = data['Close'].ewm(span=FAST, adjust=False).mean()
    data['EMA_slow'] = data['Close'].ewm(span=SLOW, adjust=False).mean()
    data['MACD_12_26_9'] = data['EMA_fast'] - data['EMA_slow']
    data['MACDs_12_26_9'] = data['MACD_12_26_9'].ewm(span=SIGNAL, adjust=False).mean()
    return data

def detectar_ultimo_cruzamento(data):
    for i in range(len(data)-1, 0, -1):
        macd_antes = data['MACD_12_26_9'].iloc[i - 1]
        sinal_antes = data['MACDs_12_26_9'].iloc[i - 1]
        macd_agora = data['MACD_12_26_9'].iloc[i]
        sinal_agora = data['MACDs_12_26_9'].iloc[i]
        if macd_antes < sinal_antes and macd_agora > sinal_agora:
            return 'Altista', data.index[i], float(data['Close'].iloc[i].item())
        elif macd_antes > sinal_antes and macd_agora < sinal_agora:
            return 'Baixista', data.index[i], float(data['Close'].iloc[i].item())
    return None, None, None

def gerar_grafico(data, ativo, tipo, data_cruz, preco_cruz):
    plt.figure(figsize=(10, 5))
    plt.plot(data.index, data['MACD_12_26_9'], label='MACD', linewidth=1.5)
    plt.plot(data.index, data['MACDs_12_26_9'], label='Signal', linewidth=1.2)

    # Destaque visual no ponto de cruzamento
    if data_cruz in data.index:
        y = data.loc[data_cruz, 'MACD_12_26_9']
        cor = 'green' if tipo == 'Altista' else 'red'
        plt.scatter(data_cruz, y, color=cor, s=60, label=f'Cruzamento {tipo}', zorder=5)

    plt.title(f'MACD - {ativo}')
    plt.legend()
    plt.grid(True)
    caminho = f'macd_graficos/{ativo}.png'
    plt.savefig(caminho)
    plt.close()
    return caminho

def criar_pdf(altistas, baixistas):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Relatório de Cruzamentos MACD", ln=True, align="C")

    # Tabela Altistas
    if altistas:
        pdf.set_font("Helvetica", "B", 12)
        pdf.ln(10)
        pdf.cell(0, 10, "Cruzamentos Altistas", ln=True)
        pdf.cell(50, 10, "Ativo", border=1)
        pdf.cell(45, 10, "Data", border=1)
        pdf.cell(45, 10, "Fechamento", border=1, ln=True)

        pdf.set_font("Helvetica", "", 12)
        for ativo, data, preco in altistas:
            pdf.cell(50, 10, ativo, border=1)
            pdf.cell(45, 10, data.strftime('%Y-%m-%d'), border=1)
            pdf.cell(45, 10, f"R$ {preco:.2f}", border=1, ln=True)

    # Tabela Baixistas
    if baixistas:
        pdf.set_font("Helvetica", "B", 12)
        pdf.ln(10)
        pdf.cell(0, 10, "Cruzamentos Baixistas", ln=True)
        pdf.cell(50, 10, "Ativo", border=1)
        pdf.cell(45, 10, "Data", border=1)
        pdf.cell(45, 10, "Fechamento", border=1, ln=True)

        pdf.set_font("Helvetica", "", 12)
        for ativo, data, preco in baixistas:
            pdf.cell(50, 10, ativo, border=1)
            pdf.cell(45, 10, data.strftime('%Y-%m-%d'), border=1)
            pdf.cell(45, 10, f"R$ {preco:.2f}", border=1, ln=True)

    # Gráficos
    for ativo, data, preco in altistas + baixistas:
        tipo = 'Altista' if (ativo, data, preco) in altistas else 'Baixista'
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, f'Gráfico MACD - {ativo}', ln=True)
        pdf.image(f"macd_graficos/{ativo}.png", x=10, y=30, w=190)

    default_dir = Path("/Users/chlima/Library/CloudStorage/OneDrive-Pessoal/Python/Financas/Relatorios")
    default_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = default_dir / "relatorio_macd_b3_diario.pdf"
    pdf.output(str(pdf_path))

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_tickers = os.path.join(base_dir, "ativos_b3.txt")
    with open(caminho_tickers, "r") as f:
        ativos = [linha.strip().upper() for linha in f if linha.strip()]

    altistas = []
    baixistas = []

    for ativo in ativos:
        try:
            df = fetch_data(ativo)
            df = calcular_macd(df)
            tipo, data_cruz, preco_cruz = detectar_ultimo_cruzamento(df)

            # Filtro: apenas cruzamento no último fechamento
            if tipo and data_cruz == df.index[-1]:
                if tipo == "Altista":
                    altistas.append((ativo, data_cruz, preco_cruz))
                else:
                    baixistas.append((ativo, data_cruz, preco_cruz))

                gerar_grafico(df, ativo, tipo, data_cruz, preco_cruz)
        except Exception as e:
            if isinstance(e, yf_exceptions.YFRateLimitError):
                print(f"[RATE LIMIT] {ativo}: {e}")
            else:
                print(f"Erro com o ativo {ativo}: {e}")

    if altistas or baixistas:
        criar_pdf(altistas, baixistas)
        print("Relatório gerado com sucesso: relatorio_macd_b3_diario.pdf")
    else:
        print("Nenhum cruzamento no último fechamento.")

if __name__ == "__main__":
    main()
