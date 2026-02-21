import requests
import json
import time

def test_api():
    url = "http://127.0.0.1:8000/api/v1/search/comprehensive/RELIANCE"
    print(f"Testing {url}...")
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            data = response.json()
            print("\n✅ API Success!")
            print(f"Symbol: {data['symbol']}")
            print(f"Fundamentals: {data.get('raw_fundamentals', {}).get('company_name')}")
            
            # Check for new fields
            raw = data.get('raw_fundamentals', {})
            print(f"EBITDA: {raw.get('ebitda')}")
            print(f"Promoter Holdings: {raw.get('held_percent_insiders')}")
            print(f"Net Profit Margin: {raw.get('profit_margins')}")
            
            print("\nFull Response Key Structure:")
            print(json.dumps(data, indent=2)[:500] + "...")
        else:
            print(f"❌ API Failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Ensure uvicorn is running.")

if __name__ == "__main__":
    # Wait a bit for reload if needed
    time.sleep(2) 
    test_api()
