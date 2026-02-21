import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface PriceChartProps {
  symbol: string;
  currentPrice: number;
}

const API_BASE = '/api/v1';

const PriceChart: React.FC<PriceChartProps> = ({ symbol, currentPrice }) => {
  const [data, setData] = useState<any[]>([]);
  const [period, setPeriod] = useState<string>('1y');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistoricalData = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/historical/${symbol}?period=${period}`);
        if (!res.ok) throw new Error('Failed to fetch historical data');
        const json = await res.json();
        
        // Add current price as the last data point if '1d' or similar isn't perfect
        const chartData = json.data;
        if (chartData.length > 0) {
            const lastDate = chartData[chartData.length - 1].date;
            const today = new Date().toISOString().split('T')[0];
            if (lastDate !== today) {
                chartData.push({
                    date: today,
                    price: currentPrice
                });
            }
        }
        setData(chartData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error fetching data');
      } finally {
        setLoading(false);
      }
    };

    fetchHistoricalData();
  }, [symbol, period, currentPrice]);

  const periods = [
    { label: '1W', value: '1w' },
    { label: '1M', value: '1m' },
    { label: '6M', value: '6m' },
    { label: '1Y', value: '1y' },
    { label: '5Y', value: '5y' },
    { label: 'ALL', value: 'max' }
  ];

  // Calculate price change and percentage for the selected period
  const startPrice = data.length > 0 ? data[0].price : 0;
  const endPrice = data.length > 0 ? data[data.length - 1].price : 0;
  const changeStr = endPrice - startPrice;
  const changePct = startPrice > 0 ? (changeStr / startPrice) * 100 : 0;
  const isPositive = changeStr >= 0;

  return (
    <div className="price-chart-container section-card glass-card animate-fade-in stagger-2">
      <div className="chart-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
           <h3 style={{ margin: 0, padding: 0, border: 'none' }}>Historical Performance</h3>
           {!loading && data.length > 0 && (
               <div style={{ marginTop: '8px' }}>
                   <span style={{ fontSize: '24px', fontWeight: 'bold' }}>₹{endPrice.toFixed(2)}</span>
                   <span style={{ 
                       marginLeft: '12px', 
                       fontWeight: '600',
                       color: isPositive ? 'var(--success)' : 'var(--danger)' 
                    }}>
                       {isPositive ? '+' : ''}{changeStr.toFixed(2)} ({isPositive ? '+' : ''}{changePct.toFixed(2)}%)
                   </span>
                   <span style={{ marginLeft: '8px', color: 'var(--text-muted)', fontSize: '12px' }}>Past {period.toUpperCase()}</span>
               </div>
           )}
        </div>
        <div className="period-selector" style={{ display: 'flex', gap: '8px', background: 'rgba(255,255,255,0.05)', padding: '4px', borderRadius: '8px' }}>
          {periods.map(p => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`period-btn ${period === p.value ? 'active' : ''}`}
              style={{
                padding: '4px 12px',
                border: 'none',
                background: period === p.value ? 'var(--accent)' : 'transparent',
                color: period === p.value ? '#fff' : 'var(--text-secondary)',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: period === p.value ? 'bold' : 'normal',
                transition: 'all 0.2s'
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div className="loader"></div></div>}
      {error && <div className="error-banner">{error}</div>}

      {!loading && !error && data.length > 0 && (
        <div style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer>
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={isPositive ? 'var(--success)' : 'var(--danger)'} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={isPositive ? 'var(--success)' : 'var(--danger)'} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis 
                  dataKey="date" 
                  tickFormatter={(tick) => {
                      const date = new Date(tick);
                      return period === '1w' || period === '1m' ? `${date.getDate()}/${date.getMonth()+1}` : `${date.getFullYear()}`;
                  }}
                  minTickGap={30}
                  tick={{ fill: 'var(--text-muted)' }}
                  axisLine={false}
                  tickLine={false}
              />
              <YAxis 
                  domain={['dataMin', 'dataMax']} 
                  hide={true} 
              />
              <Tooltip 
                contentStyle={{ 
                    backgroundColor: 'var(--bg-card)', 
                    borderColor: 'var(--border)',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                    color: 'var(--text-primary)'
                }}
                itemStyle={{ color: isPositive ? 'var(--success)' : 'var(--danger)', fontWeight: 'bold' }}
                labelStyle={{ color: 'var(--text-secondary)', marginBottom: '4px' }}
                formatter={(value: any) => [`₹${value}`, 'Price']}
              />
              <Area 
                type="monotone" 
                dataKey="price" 
                stroke={isPositive ? 'var(--success)' : 'var(--danger)'} 
                strokeWidth={3}
                fillOpacity={1} 
                fill="url(#colorPrice)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default PriceChart;
