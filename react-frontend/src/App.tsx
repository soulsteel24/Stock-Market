import { useState, useEffect, useCallback } from 'react'
import './App.css'

// Types
interface StockPick {
  symbol: string
  signal: string
  confidence: number
  current_price: number
  rsi: number | null
  change_pct: number
  data_source: string
}

interface TopPicks {
  generated_at: string
  market_status: string
  buy_recommendations: StockPick[]
  sell_recommendations: StockPick[]
  total_analyzed: number
  disclaimer: string
}

interface AnalysisResult {
  symbol: string
  name: string
  sector: string
  recommendation: string
  confidence_score: number
  current_price: number
  entry_price: number
  target_price: number
  stop_loss: number
  risk_reward_ratio: string
  potential_return_pct: number
  technical_indicators: {
    rsi: number
    ema_200: number
    price_above_ema: boolean
  }
  sentiment_analysis: {
    overall_sentiment: string
    positive_count: number
    neutral_count: number
    negative_count: number
    key_headlines: string[]
  }
  investment_thesis: string[]
  warnings: Array<{ message: string }>
  safety_veto_applied: boolean
  disclaimer: string
}

interface HealthStatus {
  status: string
  version: string
  gemini_connected: boolean
  database_connected: boolean
}

const API_BASE = 'http://127.0.0.1:8000/api/v1'

function App() {
  const [topPicks, setTopPicks] = useState<TopPicks | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [searchSymbol, setSearchSymbol] = useState('')
  const [loading, setLoading] = useState(false)
  const [topPicksLoading, setTopPicksLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [activeTab, setActiveTab] = useState<'dashboard' | 'search'>('dashboard')
  const [stockList, setStockList] = useState<string[]>([])
  const [filteredStocks, setFilteredStocks] = useState<string[]>([])
  const [showDropdown, setShowDropdown] = useState(false)

  // Check health on mount and poll every 30 seconds
  useEffect(() => {
    const checkHealth = () => {
      fetch(`${API_BASE}/health`)
        .then(res => res.json())
        .then(setHealth)
        .catch(() => setHealth(null))
    }
    
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    
    // Fetch stock list
    fetch(`${API_BASE}/stocks/list`)
      .then(res => res.json())
      .then(data => {
        const allStocks = [...(data.nifty_50 || []), ...(data.nifty_next_50 || [])]
        setStockList(allStocks)
        setFilteredStocks(allStocks.slice(0, 20))
      })
      .catch(() => setStockList([]))

    return () => clearInterval(interval)
  }, [])

  // Filter stocks based on search input
  useEffect(() => {
    if (searchSymbol.length > 0) {
      const filtered = stockList.filter(s => 
        s.toLowerCase().includes(searchSymbol.toLowerCase())
      ).slice(0, 15)
      setFilteredStocks(filtered)
      setShowDropdown(filtered.length > 0 && searchSymbol.length > 0)
    } else {
      setFilteredStocks(stockList.slice(0, 15))
      setShowDropdown(false)
    }
  }, [searchSymbol, stockList])

  // Fetch top picks
  const fetchTopPicks = useCallback(async () => {
    setTopPicksLoading(true)
    setError(null)
    try {
      // Request 500 stocks (backend handles bulk scan efficiently now)
      const res = await fetch(`${API_BASE}/top-picks?limit=5&max_stocks=500`)
      if (!res.ok) throw new Error('Failed to fetch top picks')
      const data = await res.json()
      setTopPicks(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch top picks')
    } finally {
      setTopPicksLoading(false)
    }
  }, [])

  // Analyze single stock
  const analyzeStock = async (symbol: string) => {
    if (!symbol.trim()) return
    setLoading(true)
    setError(null)
    setAnalysisResult(null)
    setShowDropdown(false)
    
    try {
      const res = await fetch(`${API_BASE}/analyze/${symbol.toUpperCase()}`, {
        method: 'POST'
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Analysis failed')
      }
      const data = await res.json()
      setAnalysisResult(data)
      setActiveTab('search')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    analyzeStock(searchSymbol)
  }

  const selectStock = (symbol: string) => {
    setSearchSymbol(symbol)
    setShowDropdown(false)
    analyzeStock(symbol)
  }


  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(price)
  }

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY': return 'var(--success)'
      case 'SELL': return 'var(--danger)'
      default: return 'var(--warning)'
    }
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="logo">
          <span className="logo-icon">📊</span>
          <span className="logo-text">Quant Research</span>
        </div>
        <nav className="nav">
          <button 
            className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            Dashboard
          </button>
          <button 
            className={`nav-btn ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            Search
          </button>
        </nav>
        <div className="status">
          <span className={`status-dot ${health?.status === 'healthy' ? 'online' : 'offline'}`}></span>
          <span>{health?.status === 'healthy' ? 'Connected' : 'Offline'}</span>
        </div>
      </header>

      <main className="main">
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="dashboard">
            <div className="dashboard-header">
              <div>
                <h1>Daily Stock Picks</h1>
                <p className="subtitle">AI-powered recommendations from Nifty 50</p>
              </div>
              <button 
                className="refresh-btn" 
                onClick={fetchTopPicks}
                disabled={topPicksLoading}
              >
                {topPicksLoading ? '⏳ Analyzing...' : '🔄 Refresh Picks'}
              </button>
            </div>

            {error && <div className="error-banner">{error}</div>}

            {!topPicks && !topPicksLoading && !error && (
              <div className="empty-state">
                <span className="empty-icon">📈</span>
                <h3>Get Today's Top Picks</h3>
                <p>Click refresh to analyze Nifty 50 stocks and get AI recommendations</p>
                <button className="cta-btn" onClick={fetchTopPicks}>
                  Generate Recommendations
                </button>
              </div>
            )}

            {topPicksLoading && (
              <div className="loading-state">
                <div className="loader"></div>
                <p>Analyzing stocks... This may take a minute</p>
              </div>
            )}

            {topPicks && !topPicksLoading && (
              <div className="picks-grid">
                {/* Buy Recommendations */}
                <div className="picks-card buy">
                  <div className="picks-header">
                    <span className="picks-icon">📈</span>
                    <h2>Top Buy Picks</h2>
                  </div>
                  {topPicks.buy_recommendations.length === 0 ? (
                    <p className="no-picks">No strong buy signals today</p>
                  ) : (
                    <div className="picks-list">
                      {topPicks.buy_recommendations.map((pick, idx) => (
                        <div 
                          key={pick.symbol} 
                          className="pick-item"
                          onClick={() => analyzeStock(pick.symbol)}
                        >
                          <div className="pick-rank">{idx + 1}</div>
                          <div className="pick-info">
                            <div className="pick-symbol">{pick.symbol}</div>
                            <div className="pick-price">{formatPrice(pick.current_price)}</div>
                          </div>
                          <div className="pick-metrics">
                            <span className="pick-confidence" style={{ color: 'var(--success)' }}>
                              {pick.confidence}%
                            </span>
                            <span className={`pick-change ${pick.change_pct >= 0 ? 'positive' : 'negative'}`}>
                              {pick.change_pct >= 0 ? '+' : ''}{pick.change_pct}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Sell Recommendations */}
                <div className="picks-card sell">
                  <div className="picks-header">
                    <span className="picks-icon">📉</span>
                    <h2>Top Sell Picks</h2>
                  </div>
                  {topPicks.sell_recommendations.length === 0 ? (
                    <p className="no-picks">No strong sell signals today</p>
                  ) : (
                    <div className="picks-list">
                      {topPicks.sell_recommendations.map((pick, idx) => (
                        <div 
                          key={pick.symbol} 
                          className="pick-item"
                          onClick={() => analyzeStock(pick.symbol)}
                        >
                          <div className="pick-rank">{idx + 1}</div>
                          <div className="pick-info">
                            <div className="pick-symbol">{pick.symbol}</div>
                            <div className="pick-price">{formatPrice(pick.current_price)}</div>
                          </div>
                          <div className="pick-metrics">
                            <span className="pick-confidence" style={{ color: 'var(--danger)' }}>
                              {pick.confidence}%
                            </span>
                            <span className={`pick-change ${pick.change_pct >= 0 ? 'positive' : 'negative'}`}>
                              {pick.change_pct >= 0 ? '+' : ''}{pick.change_pct}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {topPicks && (
              <div className="picks-meta">
                <span>Generated: {new Date(topPicks.generated_at).toLocaleString()}</span>
                <span>Market: {topPicks.market_status}</span>
                <span>Stocks Analyzed: {topPicks.total_analyzed}</span>
              </div>
            )}
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div className="search-section">
            <div className="search-header">
              <h1>Stock Analysis</h1>
              <p className="subtitle">Select or search for any NSE stock</p>
            </div>

            <form onSubmit={handleSearch} className="search-form">
              <div className="search-wrapper">
                <input
                  type="text"
                  value={searchSymbol}
                  onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
                  onFocus={() => setShowDropdown(filteredStocks.length > 0)}
                  placeholder="Type to search stocks (e.g., RELIANCE)"
                  className="search-input"
                  disabled={loading}
                />
                {showDropdown && (
                  <div className="stock-dropdown">
                    {filteredStocks.map(stock => (
                      <div 
                        key={stock}
                        className="stock-option"
                        onClick={() => selectStock(stock)}
                      >
                        {stock}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <button type="submit" className="search-btn" disabled={loading}>
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </form>

            <div className="quick-picks">
              <span className="quick-label">Popular:</span>
              {['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'TATAMOTORS', 'SBIN', 'ITC', 'BHARTIARTL'].map(sym => (
                <button 
                  key={sym} 
                  className="quick-btn"
                  onClick={() => selectStock(sym)}
                  disabled={loading}
                >
                  {sym}
                </button>
              ))}
            </div>

            {error && <div className="error-banner">{error}</div>}

            {loading && (
              <div className="loading-state">
                <div className="loader"></div>
                <p>Analyzing {searchSymbol}...</p>
              </div>
            )}

            {analysisResult && !loading && (
              <div className="analysis-results">
                {/* Stock Header */}
                <div className="stock-card">
                  <div className="stock-info">
                    <h2>{analysisResult.name}</h2>
                    <span className="badge">{analysisResult.symbol}</span>
                    <span className="sector">{analysisResult.sector}</span>
                  </div>
                  <div className="stock-price">
                    <span className="price">{formatPrice(analysisResult.current_price)}</span>
                  </div>
                </div>

                {/* Recommendation */}
                <div className="recommendation-card">
                  <div 
                    className="recommendation-badge"
                    style={{ background: getSignalColor(analysisResult.recommendation) + '22', 
                             color: getSignalColor(analysisResult.recommendation),
                             border: `2px solid ${getSignalColor(analysisResult.recommendation)}` }}
                  >
                    {analysisResult.recommendation}
                  </div>
                  <div className="confidence">
                    <span className="label">Confidence</span>
                    <div className="confidence-bar">
                      <div 
                        className="confidence-fill" 
                        style={{ width: `${analysisResult.confidence_score}%` }}
                      ></div>
                    </div>
                    <span className="value">{analysisResult.confidence_score.toFixed(1)}%</span>
                  </div>
                </div>

                {/* Price Targets */}
                <div className="targets-grid">
                  <div className="target-card entry">
                    <span className="label">Entry</span>
                    <span className="value">{formatPrice(analysisResult.entry_price)}</span>
                  </div>
                  <div className="target-card target">
                    <span className="label">Target</span>
                    <span className="value">{formatPrice(analysisResult.target_price)}</span>
                  </div>
                  <div className="target-card stoploss">
                    <span className="label">Stop Loss</span>
                    <span className="value">{formatPrice(analysisResult.stop_loss)}</span>
                  </div>
                  <div className="target-card ratio">
                    <span className="label">Risk:Reward</span>
                    <span className="value">{analysisResult.risk_reward_ratio}</span>
                  </div>
                </div>

                {/* Technical Indicators */}
                <div className="section-card">
                  <h3>📈 Technical Indicators</h3>
                  <div className="indicators-grid">
                    <div className="indicator">
                      <span className="label">RSI (14)</span>
                      <span className="value">{analysisResult.technical_indicators?.rsi?.toFixed(1) || 'N/A'}</span>
                    </div>
                    <div className="indicator">
                      <span className="label">EMA 200</span>
                      <span className="value">{analysisResult.technical_indicators?.ema_200?.toFixed(2) || 'N/A'}</span>
                    </div>
                    <div className="indicator">
                      <span className="label">Price vs EMA</span>
                      <span className={`value ${analysisResult.technical_indicators?.price_above_ema ? 'positive' : 'negative'}`}>
                        {analysisResult.technical_indicators?.price_above_ema ? 'Above' : 'Below'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Sentiment */}
                <div className="section-card">
                  <h3>📰 Sentiment Analysis</h3>
                  <div className="sentiment-row">
                    <span className={`sentiment-badge ${analysisResult.sentiment_analysis?.overall_sentiment?.toLowerCase()}`}>
                      {analysisResult.sentiment_analysis?.overall_sentiment || 'N/A'}
                    </span>
                    <div className="sentiment-counts">
                      <span className="positive">+{analysisResult.sentiment_analysis?.positive_count || 0}</span>
                      <span className="neutral">○{analysisResult.sentiment_analysis?.neutral_count || 0}</span>
                      <span className="negative">-{analysisResult.sentiment_analysis?.negative_count || 0}</span>
                    </div>
                  </div>
                  {analysisResult.sentiment_analysis?.key_headlines?.slice(0, 3).map((headline, i) => (
                    <div key={i} className="headline">{headline}</div>
                  ))}
                </div>

                {/* Investment Thesis */}
                {analysisResult.investment_thesis?.length > 0 && (
                  <div className="section-card">
                    <h3>💡 Investment Thesis</h3>
                    {analysisResult.investment_thesis.map((point, i) => (
                      <div key={i} className="thesis-point">
                        <span className="number">{i + 1}</span>
                        <span className="text">{point}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Disclaimer */}
                <div className="disclaimer">
                  {analysisResult.disclaimer}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="footer">
        <p>Agentic Quantitative Research System • Built with FastAPI + React + NSEPython</p>
        <p className="small">Data Source: NSE India • v{health?.version || '1.0.0'}</p>
      </footer>
    </div>
  )
}

export default App
