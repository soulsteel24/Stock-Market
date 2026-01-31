import time
start = time.time()
print("Importing nsepython...")
try:
    from nsepython import quote_equity, equity_history, indiavix
    print(f"Imported in {time.time() - start:.2f} seconds")
except ImportError:
    print("ImportError")
except Exception as e:
    print(f"Failed: {e}")
