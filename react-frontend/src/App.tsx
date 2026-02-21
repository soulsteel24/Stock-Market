import { useState, useEffect, useCallback } from 'react'
import './App.css'
import ForecastChart from './components/ForecastChart'
import PriceChart from './components/PriceChart'

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
  current_price: number
  recommendation: string
  confidence_score: number
  confidence_breakdown: {
    technical_score: number
    financial_score: number
    sentiment_score: number
  }
  technical_indicators: {
    rsi: number
    ema_200: number
  }
  fundamentals?: {
    ratios?: {
      pe_ratio?: number
      earnings_growth?: number
    }
    financials?: {
      revenue_cr?: number
      net_profit_margin?: number
      debt_to_equity?: number
    }
    holdings?: {
      promoters?: number
      institutions?: number
    }
  }
  sentiment_analysis?: {
    overall_sentiment: string
    confidence: number
    normalized_score: number
    ml_breakdown?: {
      positive: number
      neutral: number
      negative: number
    }
  }
  agent_debate?: {
    momentum_agent: string
    contrarian_agent: string
    safety_veto_agent: string
  }
  forecast_analysis?: {
    forecast: any[]
    trend_pct: number
    bullish_trend: boolean
    model: string
    days_forecasted: number
  }
  raw_fundamentals?: any // For extra fields like EBITDA
}

interface HealthStatus {
  status: string
  version: string
  gemini_connected: boolean
  database_connected: boolean
}

const API_BASE = '/api/v1'

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
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')

  // Check health on mount and poll every 30 seconds
  useEffect(() => {
    // apply theme body wide
    document.body.className = theme === 'light' ? 'light-theme' : '';
    
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
  }, [theme])

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

  // Analyze single stock (Comprehensive)
  const analyzeStock = async (symbol: string) => {
    if (!symbol.trim()) return
    setLoading(true)
    setError(null)
    setAnalysisResult(null)
    setShowDropdown(false)
    
    try {
      // Use the main orchestration endpoint
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

  const formatNumber = (num: number) => {
      if (num === undefined || num === null) return 'N/A';
      return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(num);
  }

  const getSignalColor = (signal: string) => {
    const s = signal?.toUpperCase() || '';
    if (s.includes('BUY')) return 'var(--success)'
    if (s.includes('SELL')) return 'var(--danger)'
    return 'var(--warning)'
  }

  return (
    <div className={`app ${theme === 'light' ? 'light-theme' : ''}`}>
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
            <button 
              className="nav-btn"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              title="Toggle Theme"
              style={{ padding: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
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
          <div className="dashboard animate-fade-in">
            <div className="dashboard-header">
              <div>
                <h1>Daily Stock Picks</h1>
                <p className="subtitle">AI-powered recommendations from Nifty 50</p>
                <small style={{color: '#94a3b8'}}>* Pre-market analysis (cached)</small>
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
                <div className="picks-card glass-card buy stagger-1 animate-fade-in">
                  <div className="picks-header">
                    <span className="picks-icon">🚀</span>
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
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Sell Recommendations */}
                <div className="picks-card glass-card sell stagger-2 animate-fade-in">
                  <div className="picks-header">
                    <span className="picks-icon">💎</span>
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
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div className="search-section animate-fade-in">
            <div className="search-header">
              <h1>Stock Analysis (Real-time)</h1>
              <p className="subtitle">Select or search for any NSE stock to get live analysis</p>
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
              <div className="analysis-results animate-fade-in stagger-1">
                {/* Stock Header */}
                <div className="stock-card glass-card">
                  <div className="stock-info">
                    <h2>{analysisResult.name || analysisResult.symbol}</h2>
                    <span className="badge">{analysisResult.symbol}</span>
                    <span className="sector">{analysisResult.sector || 'Unknown Sector'}</span>
                  </div>
                  <div className="stock-price">
                    <span className="price">{formatPrice(analysisResult.current_price)}</span>
                  </div>
                </div>

                {/* Recommendation */}
                <div className="recommendation-card glass-card stagger-2 animate-fade-in">
                  <div 
                    className="recommendation-badge"
                    style={{ background: getSignalColor(analysisResult.recommendation) + '22', 
                             color: getSignalColor(analysisResult.recommendation),
                             border: `2px solid ${getSignalColor(analysisResult.recommendation)}` }}
                  >
                    {analysisResult.recommendation}
                  </div>
                 
                  <div className="scores-grid">
                      <div className="score-item">
                          <span>Technical</span>
                          <b>{Math.round(analysisResult.confidence_breakdown.technical_score)}</b>
                      </div>
                      <div className="score-item">
                          <span>Financial</span>
                          <b>{Math.round(analysisResult.confidence_breakdown.financial_score)}</b>
                      </div>
                      <div className="score-item">
                          <span>Sentiment</span>
                          <b>{Math.round(analysisResult.confidence_breakdown.sentiment_score)}</b>
                      </div>
                  </div>
                </div>
                
                {/* Sentiment Gauge (FinBERT) */}
                {analysisResult.sentiment_analysis && (
                  <div className="section-card glass-card stagger-3 animate-fade-in sentiment-section">
                    <h3>📰 News Confidence (FinBERT)</h3>
                    <div className="sentiment-bar-container">
                      <div className="sentiment-bar-labels">
                        <span>Negative: {Math.round((analysisResult.sentiment_analysis.ml_breakdown?.negative || 0) * 100)}%</span>
                        <span>Neutral: {Math.round((analysisResult.sentiment_analysis.ml_breakdown?.neutral || 0) * 100)}%</span>
                        <span>Positive: {Math.round((analysisResult.sentiment_analysis.ml_breakdown?.positive || 0) * 100)}%</span>
                      </div>
                      <div className="sentiment-segmented-bar">
                        <div className="segment down" style={{width: `${(analysisResult.sentiment_analysis.ml_breakdown?.negative || 0) * 100}%`}}></div>
                        <div className="segment neutral" style={{width: `${(analysisResult.sentiment_analysis.ml_breakdown?.neutral || 1) * 100}%`}}></div>
                        <div className="segment up" style={{width: `${(analysisResult.sentiment_analysis.ml_breakdown?.positive || 0) * 100}%`}}></div>
                      </div>
                      <div className="sentiment-summary">
                        <strong>Overall: {analysisResult.sentiment_analysis.overall_sentiment}</strong> (Normalized Score: {analysisResult.sentiment_analysis.normalized_score > 0 ? '+' : ''}{analysisResult.sentiment_analysis.normalized_score.toFixed(2)})
                      </div>
                    </div>
                  </div>
                )}

                {/* Agent Debate Board */}
                {analysisResult.agent_debate && (
                  <div className="section-card glass-card stagger-3 animate-fade-in">
                    <h3>🤖 Multi-Agent Debate</h3>
                    <div className="agent-debate-board">
                      <div className="agent-monologue momentum-agent">
                        <h4>🚀 Value/Momentum Agent</h4>
                        <p>{analysisResult.agent_debate.momentum_agent}</p>
                      </div>
                      <div className="agent-monologue contrarian-agent">
                        <h4>⚖️ Contrarian (Divergence) Agent</h4>
                        <p>{analysisResult.agent_debate.contrarian_agent}</p>
                      </div>
                      <div className="agent-monologue safety-agent">
                        <h4>🛡️ Safety Veto Agent</h4>
                        <p>{analysisResult.agent_debate.safety_veto_agent}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Fundamentals Grid */}
                {analysisResult.fundamentals && Object.keys(analysisResult.fundamentals).length > 0 && (
                  <div className="section-card glass-card stagger-3 animate-fade-in">
                      <h3>📊 Deep Fundamentals & Holdings</h3>
                      <div className="indicators-grid four-col">
                           <div className="indicator">
                               <span className="label">P/E Ratio</span>
                               <span className="value">{formatNumber(analysisResult.fundamentals.ratios?.pe_ratio || 0)}</span>
                           </div>
                           <div className="indicator">
                               <span className="label">EPS Growth</span>
                               <span className="value">{formatNumber(analysisResult.fundamentals.ratios?.earnings_growth || 0)}%</span>
                           </div>
                           <div className="indicator">
                               <span className="label">Promoter Hold %</span>
                               <span className="value">{formatNumber(analysisResult.fundamentals.holdings?.promoters || analysisResult.raw_fundamentals?.promoter_holding_pct || analysisResult.raw_fundamentals?.held_percent_insiders)}%</span>
                           </div>
                           <div className="indicator">
                               <span className="label">Inst. Hold %</span>
                               <span className="value">{formatNumber(analysisResult.fundamentals.holdings?.institutions || (analysisResult.raw_fundamentals?.fii_holding_pct || 0) + (analysisResult.raw_fundamentals?.dii_holding_pct || 0) || analysisResult.raw_fundamentals?.held_percent_institutions)}%</span>
                           </div>
                           <div className="indicator" style={{ background: 'rgba(56, 189, 248, 0.1)' }}>
                               <span className="label" style={{ color: '#38bdf8' }}>FII Hold %</span>
                               <span className="value" style={{ color: '#38bdf8' }}>{formatNumber(analysisResult.raw_fundamentals?.fii_holding_pct || 0)}%</span>
                           </div>
                           <div className="indicator" style={{ background: 'rgba(56, 189, 248, 0.1)' }}>
                               <span className="label" style={{ color: '#38bdf8' }}>DII Hold %</span>
                               <span className="value" style={{ color: '#38bdf8' }}>{formatNumber(analysisResult.raw_fundamentals?.dii_holding_pct || 0)}%</span>
                           </div>
                      </div>
                  </div>
                )}

                {/* Technical Indicators */}
                <div className="section-card glass-card stagger-3 animate-fade-in">
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
                  </div>
                </div>

                {/* Historical Price Chart */}
                <PriceChart symbol={analysisResult.symbol} currentPrice={analysisResult.current_price} />

                {/* AI Forecast */}
                {analysisResult.forecast_analysis && (
                  <div className="section-card glass-card stagger-4 animate-fade-in">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h3>🤖 AI Price Forecast ({analysisResult.forecast_analysis.days_forecasted} Days)</h3>
                      <div className={`trend-badge ${analysisResult.forecast_analysis.bullish_trend ? 'bullish' : 'bearish'}`}
                           style={{
                             padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 'bold',
                             backgroundColor: analysisResult.forecast_analysis.bullish_trend ? '#2e7d32' : '#c62828',
                             color: 'white'
                           }}>
                        {analysisResult.forecast_analysis.bullish_trend ? 'Bullish Trend' : 'Bearish Trend'}
                      </div>
                    </div>
                    <p style={{ fontSize: '0.9rem', color: '#bbb', marginBottom: '1rem' }}>
                      Predicted Move: {analysisResult.forecast_analysis.trend_pct > 0 ? '+' : ''}{analysisResult.forecast_analysis.trend_pct}% • Model: {analysisResult.forecast_analysis.model}
                    </p>
                    <ForecastChart 
                      forecastData={analysisResult.forecast_analysis.forecast} 
                      currentPrice={analysisResult.current_price} 
                    />
                  </div>
                )}

                {/* Disclaimer */}
                <div className="disclaimer">
                  <p>⚠️ <strong>Real-time Analysis vs Dashboard:</strong> Search results are generated in real-time. Dashboard picks are generated before market open and may differ due to intraday price movements.</p>
                  SEBI Disclaimer: This is an AI-generated research tool for educational purposes only. It does not constitute financial advice.
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
