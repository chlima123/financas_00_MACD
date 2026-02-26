# 00_MACD

Monitoramento de cruzamentos do indicador MACD para ativos da B3, com versões diária e semanal e geração de relatório em PDF.

## O que esta pasta contém

- `MACD_diario.py`: script principal do MACD diário (`interval="1d"`), com cache local em Parquet e retentativas para falhas/rate limit.
- `MACD_semanal.py`: script do MACD semanal (`interval="1wk"`).
- `MACD_diario_B3.ipynb` e `MACD_semanal_B3.ipynb`: notebooks com versões de desenvolvimento/execução manual.
- `ativos_b3.txt`: lista de tickers (um por linha) usada pelos scripts.
- `cache_prices/`: cache local de preços (usado pelo script diário).
- `macd_graficos/`: gráficos `.png` gerados para os ativos com cruzamento no último fechamento.
- `macd_erros.txt`: arquivo auxiliar para registrar erros (quando utilizado).

## Requisitos

Python 3.10+.

Instalação de dependências:

```bash
pip install yfinance pandas matplotlib fpdf pyarrow
```

## Execução

No terminal, dentro de `00_MACD`:

```bash
python MACD_diario.py
python MACD_semanal.py
```

## Saídas

- PDF diário: `../Relatorios/relatorio_macd_b3_diario.pdf`
- PDF semanal: `../Relatorios/relatorio_macd_b3_semanal.pdf`
- Gráficos por ativo: `macd_graficos/*.png`
- Cache de preços (diário): `cache_prices/*.parquet`

## Observações

- Os scripts consideram apenas cruzamento ocorrido no último candle disponível.
- Os tickers devem estar no formato Yahoo para B3 (ex.: `PETR4.SA`).
- O script diário usa cache e backoff de retentativas para reduzir impacto de `YFRateLimitError`.
