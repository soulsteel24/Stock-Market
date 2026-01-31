# 📊 Agentic Quantitative Stock Research System

An AI-powered stock analysis platform for Indian markets (NSE), featuring multi-agent reasoning, technical analysis, fundamental analysis, and real-time news sentiment.

![Tech Stack](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![NSE](https://img.shields.io/badge/NSE-India-orange)

## ✨ Features

### 📈 Stock Analysis

- **500+ Indian Stocks** - Nifty 50, Next 50, Midcap, Smallcap, Sector indices
- **Technical Indicators** - RSI, EMA (20/50/200), MACD, Bollinger Bands
- **Fundamental Analysis** - P/E, P/B, ROE, Debt/Equity, Profit Margins
- **AI Recommendations** - BUY/SELL/HOLD with confidence scores

### 🤖 Multi-Agent Architecture

- **Contrarian Agent** - Challenges consensus with alternative viewpoints
- **Momentum Agent** - Analyzes price trends and volume patterns
- **Synthesis Agent** - Aggregates signals with conflict resolution
- **Safety Veto Agent** - Risk management and position limits

### 📰 News & Sentiment

- **Real-time News Scraping** - Google News RSS for financial news
- **Stock-specific News** - Targeted news for individual stocks
- **Sentiment Analysis** - Positive/Negative/Neutral classification
- **Category Filters** - Market, IPO, Earnings, RBI, FII, Global

### 💻 Modern React Frontend

- **Premium Dark Theme** - Glassmorphism design
- **Dashboard View** - Daily top buy/sell recommendations
- **Stock Search** - Searchable dropdown with 70+ stocks
- **Detailed Analysis** - Full technical and sentiment breakdown

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+

### 1. Clone & Setup

```bash
cd Stock-Market

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```env
# Required for full AI features (optional for basic analysis)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional settings
LOG_LEVEL=INFO
CACHE_ENABLED=true
```

### 3. Run Backend

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Run Frontend

```bash
cd react-frontend
npm install
npm run dev -- --port 5173
```

### 5. Access

- **React App**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

---

## 📡 API Endpoints

### Stock Analysis

| Endpoint                                   | Description                        |
| ------------------------------------------ | ---------------------------------- |
| `POST /api/v1/analyze/{symbol}`            | Full analysis with recommendation  |
| `GET /api/v1/top-picks?max_stocks=500`     | Daily buy/sell recommendations     |
| `GET /api/v1/fundamentals/{symbol}`        | Comprehensive fundamental analysis |
| `GET /api/v1/fundamentals/{symbol}/ratios` | Key financial ratios only          |

### News & Sentiment

| Endpoint                                  | Description                     |
| ----------------------------------------- | ------------------------------- |
| `GET /api/v1/news/trending`               | Trending financial news         |
| `GET /api/v1/news/financial?category=ipo` | Category-specific news          |
| `GET /api/v1/fundamentals/{symbol}/news`  | Stock-specific news + sentiment |
| `GET /api/v1/sentiment/{symbol}`          | News sentiment analysis         |

### Market Data

| Endpoint                                 | Description           |
| ---------------------------------------- | --------------------- |
| `GET /api/v1/stocks/list?sector=banking` | Stocks by sector      |
| `GET /api/v1/top-picks/sector/{sector}`  | Sector-specific picks |
| `GET /api/v1/market/vix`                 | India VIX value       |

---

## 📊 Stock Universe (500+ Stocks)

| Category       | Count | Examples                  |
| -------------- | ----- | ------------------------- |
| Nifty 50       | 50    | RELIANCE, TCS, HDFCBANK   |
| Nifty Next 50  | 50    | ADANIGREEN, BIOCON, DLF   |
| Midcap 150     | 150   | ABB, ASTRAL, DIXON        |
| Smallcap 250   | 250   | AAVAS, AMBER, CAMPUS      |
| Sector Indices | 150+  | Banking, IT, Pharma, Auto |

### Sectors

- `banking` - HDFCBANK, ICICIBANK, SBIN...
- `it` - TCS, INFY, WIPRO, TECHM...
- `pharma` - SUNPHARMA, DRREDDY, CIPLA...
- `auto` - MARUTI, TATAMOTORS, M&M...
- `fmcg` - HINDUNILVR, ITC, NESTLE...
- `metal` - TATASTEEL, JSWSTEEL, HINDALCO...
- `energy` - RELIANCE, ONGC, NTPC, BPCL...
- `realty` - DLF, GODREJPROP, OBEROIRLTY...

---

## 🔧 Project Structure

```
Stock-Market/
├── app/
│   ├── api/
│   │   └── routes.py          # API endpoints
│   ├── data/
│   │   └── stock_universe.py  # 500+ stock symbols
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── services/
│   │   ├── technical_analyzer.py
│   │   ├── fundamental_analyzer.py
│   │   ├── sentiment_analyzer.py
│   │   ├── financial_news_scraper.py
│   │   ├── stock_analyzer.py
│   │   ├── memory_loop.py
│   │   └── gemini_client.py
│   └── main.py
├── react-frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   └── App.css
│   └── package.json
├── requirements.txt
├── .env
└── README.md
```

---

## 🔬 Analysis Features

### Technical Analysis

- **RSI (14)** - Overbought (>70) / Oversold (<30)
- **EMA Crossovers** - 20/50/200 day
- **MACD** - Trend momentum
- **Price vs EMA** - Above/below trend
- **Technical Score** - 0-100 composite

### Fundamental Analysis

- **Valuation** - P/E, P/B, PEG ratios
- **Profitability** - ROE, ROA, Margins
- **Financial Health** - D/E, Current Ratio
- **Growth** - Revenue & Earnings growth
- **Score** - 0-100 with STRONG/GOOD/FAIR/WEAK rating

### Sentiment Analysis

- **News Aggregation** - Multiple financial sources
- **Keyword Classification** - Positive/Negative keywords
- **Confidence Score** - Based on news distribution
- **Headlines** - Top relevant headlines

---

## ⚠️ Disclaimer

> **This is an educational project for learning purposes only.**
>
> - All recommendations are AI-generated and should NOT be used for actual trading decisions
> - Past performance does not guarantee future results
> - Always consult a SEBI-registered investment advisor before investing
> - The creators are not responsible for any financial losses

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **NSE Python** - NSE data access
- **yfinance** - Yahoo Finance fallback
- **Google Gemini** - AI reasoning
- **FastAPI** - Backend framework
- **React** - Frontend framework
