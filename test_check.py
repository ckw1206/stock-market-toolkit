import sys
sys.path.insert(0, 'backend')
try:
    from app.main import app
    print('app import OK')
except Exception as e:
    print(f'app import FAIL: {type(e).__name__}: {e}')

try:
    import pandas_ta
    print('pandas_ta OK')
except Exception as e:
    print(f'pandas_ta FAIL: {type(e).__name__}: {e}')