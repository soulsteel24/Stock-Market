import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface NetIncomeChartProps {
  netIncomeHistory: Record<string, number> | undefined
}

export default function NetIncomeChart({ netIncomeHistory }: NetIncomeChartProps) {
  if (!netIncomeHistory || Object.keys(netIncomeHistory).length === 0) {
    return <div style={{ color: '#888', fontStyle: 'italic', padding: '1rem' }}>No Net Income history available.</div>
  }

  // Convert Dictionary to Array for Recharts, sort by year ascending
  const data = Object.entries(netIncomeHistory)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([year, value]) => ({
      year,
      value: value / 10000000 // Convert to Crores
    }))

  const formatYAxis = (tickItem: number) => {
    return `₹${tickItem}Cr`
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const val = payload[0].value
      return (
        <div style={{
            background: 'var(--surface-color, #1e293b)',
            border: '1px solid var(--border-color, #334155)',
            padding: '10px',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            color: 'var(--text-color, #f8fafc)'
        }}>
          <p style={{ margin: 0, fontWeight: 'bold' }}>Year: {label}</p>
          <p style={{ margin: 0, color: val >= 0 ? '#10b981' : '#ef4444' }}>
            Net Income: ₹{val.toFixed(2)} Cr
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div style={{ width: '100%', height: 250, marginTop: '1rem' }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis 
            dataKey="year" 
            stroke="#94a3b8" 
            tick={{ fill: '#94a3b8', fontSize: 12 }} 
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
          />
          <YAxis 
            stroke="#94a3b8" 
            tick={{ fill: '#94a3b8', fontSize: 12 }} 
            tickFormatter={formatYAxis} 
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            width={80}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} />
          <Bar 
            dataKey="value" 
            fill="#3b82f6" 
            radius={[4, 4, 0, 0]}
            maxBarSize={40}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
