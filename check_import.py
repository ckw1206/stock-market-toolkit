import sys
sys.path.insert(0, '.')
try:
    from app.services import signals
    print("ok")
except Exception as e:
    print(f"ERROR: {e}")