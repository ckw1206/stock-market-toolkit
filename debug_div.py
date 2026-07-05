import sys
sys.path.insert(0, '/home/kyle/.hermes/kanban/workspaces/t_9dc0319f/review-pr-293/backend')

import pandas as pd
from app.services.signals import detect_divergence, _local_pivots

# ---- Bullish test ----
rsi_vals = [50.0]*20 + [40.0, 42.0, 44.0, 46.0, 48.0, 45.0, 43.0, 41.0, 47.0, 50.0, 53.0]
close_vals = [100.0]*20 + [95.0, 93.0, 91.0, 90.0, 92.0, 91.0, 90.0, 88.0, 87.0, 86.0]
close = pd.Series(close_vals)
rsi = pd.Series(rsi_vals)

print(f'=== BULLISH TEST ===')
print(f'len={len(close)}, lookback=30, order=3')
c = close.tail(30).reset_index(drop=True)
r = rsi.tail(30).reset_index(drop=True)
print(f'c (last 30): {list(c)}')
print(f'r (last 30): {list(r)}')
lows = _local_pivots(c, order=3, kind='min')
print(f'low pivots: {lows}')
if len(lows) >= 2:
    a, b = lows[-2], lows[-1]
    print(f'  a={a}, b={b}: close[a]={c.iloc[a]}, close[b]={c.iloc[b]}')
    print(f'  rsi[a]={r.iloc[a]}, rsi[b]={r.iloc[b]}')
    print(f'  price lower low: {c.iloc[b] < c.iloc[a]}, rsi higher low: {r.iloc[b] > r.iloc[a]}')
result = detect_divergence(close, rsi, lookback=30, order=3)
print(f'detect_divergence result: {result}')
print()

# ---- Bearish test ----
print('=== BEARISH TEST ===')
close_vals2 = [80.0]*20 + [82.0, 84.0, 86.0, 88.0, 87.0, 86.0, 85.0, 89.0, 91.0, 93.0]
rsi_vals2   = [50.0]*20 + [58.0, 60.0, 62.0, 64.0, 63.0, 61.0, 60.0, 58.0, 56.0, 54.0]
close2 = pd.Series(close_vals2)
rsi2    = pd.Series(rsi_vals2)
c2 = close2.tail(30).reset_index(drop=True)
r2 = rsi2.tail(30).reset_index(drop=True)
print(f'c2 (last 30): {list(c2)}')
print(f'r2 (last 30): {list(r2)}')
highs = _local_pivots(c2, order=3, kind='max')
print(f'high pivots: {highs}')
if len(highs) >= 2:
    a, b = highs[-2], highs[-1]
    print(f'  a={a}, b={b}: close[a]={c2.iloc[a]}, close[b]={c2.iloc[b]}')
    print(f'  rsi[a]={r2.iloc[a]}, rsi[b]={r2.iloc[b]}')
    print(f'  price higher high: {c2.iloc[b] > c2.iloc[a]}, rsi lower high: {r2.iloc[b] < r2.iloc[a]}')
result2 = detect_divergence(close2, rsi2, lookback=30, order=3)
print(f'detect_divergence result: {result2}')