/**
 * Agentic Quant Research System - Frontend
 * Connects to FastAPI backend for stock analysis
 */

const API_BASE = 'http://127.0.0.1:8000';
let lastSymbol = '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkApiStatus();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    const input = document.getElementById('stockInput');
    
    // Enter key to search
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            analyzeStock();
        }
    });
    
    // Auto uppercase
    input.addEventListener('input', (e) => {
        e.target.value = e.target.value.toUpperCase();
    });
}

// Check API status
async function checkApiStatus() {
    const statusEl = document.getElementById('apiStatus');
    const statusDot = document.querySelector('.status-dot');
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/health`);
        const data = await response.json();
        
        if (data.status === 'healthy') {
            statusEl.textContent = 'Connected';
            statusDot.style.background = '#10b981';
        } else {
            statusEl.textContent = 'Limited';
            statusDot.style.background = '#f59e0b';
        }
    } catch (error) {
        statusEl.textContent = 'Offline';
        statusDot.style.background = '#ef4444';
    }
}

// Quick analyze button
function quickAnalyze(symbol) {
    document.getElementById('stockInput').value = symbol;
    analyzeStock();
}

// Retry analysis
function retryAnalysis() {
    if (lastSymbol) {
        document.getElementById('stockInput').value = lastSymbol;
        analyzeStock();
    }
}

// Main analyze function
async function analyzeStock() {
    const input = document.getElementById('stockInput');
    const symbol = input.value.trim().toUpperCase();
    
    if (!symbol) {
        input.focus();
        return;
    }
    
    lastSymbol = symbol;
    
    // Show loading state
    setLoading(true);
    hideError();
    hideResults();
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/analyze/${symbol}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }
        
        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        console.error('Analysis error:', error);
        showError('Analysis Failed', error.message);
    } finally {
        setLoading(false);
    }
}

// Set loading state
function setLoading(isLoading) {
    const btn = document.getElementById('analyzeBtn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');
    
    btn.disabled = isLoading;
    btnText.textContent = isLoading ? 'Analyzing...' : 'Analyze';
    btnLoader.style.display = isLoading ? 'block' : 'none';
}

// Display results
function displayResults(data) {
    // Stock Header
    document.getElementById('stockName').textContent = data.name || data.symbol;
    document.getElementById('stockSymbol').textContent = data.symbol;
    document.getElementById('stockSector').textContent = data.sector || 'Unknown';
    document.getElementById('currentPrice').textContent = formatPrice(data.current_price);
    
    // Price change
    const changeEl = document.getElementById('priceChange');
    const changeValue = data.technical_indicators?.change_pct || 0;
    document.getElementById('changeValue').textContent = formatPercent(changeValue);
    changeEl.className = `price-change ${changeValue >= 0 ? 'positive' : 'negative'}`;
    
    // Recommendation
    const recBadge = document.getElementById('recommendationBadge');
    const recType = data.recommendation.toLowerCase();
    document.getElementById('recommendationType').textContent = data.recommendation;
    recBadge.className = `recommendation-badge ${recType}`;
    
    // Confidence
    const confidence = data.confidence_score || 50;
    document.getElementById('confidenceBar').style.width = `${confidence}%`;
    document.getElementById('confidenceValue').textContent = `${confidence.toFixed(1)}%`;
    
    // Price Targets
    document.getElementById('entryPrice').textContent = formatPrice(data.entry_price);
    document.getElementById('targetPrice').textContent = formatPrice(data.target_price);
    document.getElementById('stopLoss').textContent = formatPrice(data.stop_loss);
    document.getElementById('riskReward').textContent = data.risk_reward_ratio || '1:2';
    
    // Technical Indicators
    const tech = data.technical_indicators || {};
    const rsi = tech.rsi || 50;
    document.getElementById('rsiValue').textContent = rsi.toFixed(1);
    document.getElementById('rsiBar').style.width = `${rsi}%`;
    
    const emaStatus = tech.price_above_ema ? 'Above' : 'Below';
    const emaEl = document.getElementById('emaStatus');
    emaEl.textContent = emaStatus;
    emaEl.className = `indicator-status ${tech.price_above_ema ? 'positive' : 'negative'}`;
    
    // MACD (simplified)
    const macdEl = document.getElementById('macdStatus');
    macdEl.textContent = data.recommendation === 'BUY' ? 'Bullish' : 'Bearish';
    macdEl.className = `indicator-status ${data.recommendation === 'BUY' ? 'positive' : 'negative'}`;
    
    // Technical Score
    document.getElementById('techScore').textContent = (data.confidence_breakdown?.technical_score || 50).toFixed(0);
    
    // Sentiment
    const sentiment = data.sentiment_analysis || {};
    const sentimentType = sentiment.overall_sentiment || 'NEUTRAL';
    document.getElementById('sentimentType').textContent = sentimentType;
    
    const sentBadge = document.getElementById('sentimentBadge');
    sentBadge.className = `sentiment-badge ${sentimentType.toLowerCase()}`;
    
    document.getElementById('positiveCount').textContent = sentiment.positive_count || 0;
    document.getElementById('neutralCount').textContent = sentiment.neutral_count || 0;
    document.getElementById('negativeCount').textContent = sentiment.negative_count || 0;
    
    // Confidence Breakdown
    const breakdown = data.confidence_breakdown || {};
    updateConfBar('confTechBar', 'confTechVal', breakdown.technical_score);
    updateConfBar('confFinBar', 'confFinVal', breakdown.financial_score);
    updateConfBar('confSentBar', 'confSentVal', breakdown.sentiment_score);
    updateConfBar('confHistBar', 'confHistVal', breakdown.historical_score);
    
    // News Headlines
    displayNews(sentiment.key_headlines || []);
    
    // Investment Thesis
    displayThesis(data.investment_thesis || []);
    
    // Warnings
    displayWarnings(data.warnings || [], data.safety_veto_applied);
    
    // Disclaimer
    if (data.disclaimer) {
        document.getElementById('disclaimer').textContent = data.disclaimer;
    }
    
    // Update timestamp
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
    
    // Show results
    document.getElementById('resultsSection').style.display = 'block';
    
    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// Update confidence bar
function updateConfBar(barId, valId, value) {
    const val = value || 50;
    document.getElementById(barId).style.width = `${val}%`;
    document.getElementById(valId).textContent = `${val.toFixed(0)}%`;
}

// Display news headlines
function displayNews(headlines) {
    const container = document.getElementById('newsContainer');
    container.innerHTML = '';
    
    if (headlines.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted);">No news available</p>';
        return;
    }
    
    headlines.slice(0, 5).forEach(headline => {
        // Parse headline (format: "Source TimeAgo Title")
        const parts = headline.split(' ');
        let source = parts[0] || 'News';
        let title = headline;
        
        // Try to extract source
        if (headline.includes(' ago ')) {
            const agoIndex = headline.indexOf(' ago ');
            source = headline.substring(0, agoIndex + 4);
            title = headline.substring(agoIndex + 5);
        }
        
        const item = document.createElement('div');
        item.className = 'news-item';
        item.innerHTML = `
            <div class="news-title">${escapeHtml(title)}</div>
            <div class="news-source">${escapeHtml(source)}</div>
        `;
        container.appendChild(item);
    });
}

// Display investment thesis
function displayThesis(points) {
    const container = document.getElementById('thesisContainer');
    container.innerHTML = '';
    
    if (points.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted);">AI thesis not available (add GEMINI_API_KEY)</p>';
        return;
    }
    
    points.forEach((point, index) => {
        const item = document.createElement('div');
        item.className = 'thesis-point';
        item.innerHTML = `
            <span class="thesis-number">${index + 1}</span>
            <span class="thesis-text">${escapeHtml(point)}</span>
        `;
        container.appendChild(item);
    });
}

// Display warnings
function displayWarnings(warnings, vetoApplied) {
    const card = document.getElementById('warningsCard');
    const container = document.getElementById('warningsContainer');
    
    if (warnings.length === 0 && !vetoApplied) {
        card.style.display = 'none';
        return;
    }
    
    container.innerHTML = '';
    
    if (vetoApplied) {
        const vetoWarning = document.createElement('div');
        vetoWarning.className = 'warning-item';
        vetoWarning.textContent = '🛑 Safety Veto Applied - Original recommendation was overridden due to risk factors';
        container.appendChild(vetoWarning);
    }
    
    warnings.forEach(warning => {
        const item = document.createElement('div');
        item.className = 'warning-item';
        item.textContent = warning.message || warning;
        container.appendChild(item);
    });
    
    card.style.display = 'block';
}

// Show error
function showError(title, message) {
    document.getElementById('errorTitle').textContent = title;
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorSection').style.display = 'block';
}

// Hide error
function hideError() {
    document.getElementById('errorSection').style.display = 'none';
}

// Hide results
function hideResults() {
    document.getElementById('resultsSection').style.display = 'none';
}

// Format price
function formatPrice(price) {
    if (!price) return '₹0';
    return `₹${Number(price).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

// Format percent
function formatPercent(value) {
    if (!value) return '0%';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${Number(value).toFixed(2)}%`;
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show history (placeholder)
function showHistory() {
    alert('History feature - View your past recommendations at /api/v1/recommendations');
}

// Show lessons (placeholder)  
function showLessons() {
    alert('Lessons feature - View learned lessons at /api/v1/lessons');
}
