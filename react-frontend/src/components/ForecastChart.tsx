import React from 'react';
import {

  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart
} from 'recharts';

interface ForecastDataPoint {
  date: string;
  predicted_price?: number;
  lower_bound?: number;
  upper_bound?: number;
  historical_price?: number;
  sma_20?: number;
  sma_50?: number;
}

interface ForecastChartProps {
  forecastData: ForecastDataPoint[];
  currentPrice: number;
}

const ForecastChart: React.FC<ForecastChartProps> = ({ forecastData }) => {
  if (!forecastData || forecastData.length === 0) {
    return <div className="no-data-chart">No forecast data available</div>;
  }

  const formattedData = forecastData.map(d => ({
    ...d,
    date: new Date(d.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
  }));

  return (
    <div className="forecast-chart-container" style={{ width: '100%', height: 350 }}>
      {/* We can show trends here if passed as prop, but parent can do it too */}
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={formattedData}
          margin={{
            top: 20,
            right: 20,
            bottom: 20,
            left: 20,
          }}
        >
          <CartesianGrid stroke="#f5f5f5" strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey="date" scale="point" stroke="#ccc" />
          <YAxis domain={['auto', 'auto']} stroke="#ccc" />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1e1e1e', border: '1px solid #444', color: '#fff' }}
            itemStyle={{ color: '#fff' }}
          />
          <Legend />
          
          {/* Confidence Interval (Area) */}
          <Area 
            type="monotone" 
            dataKey="upper_bound" 
            stroke="none" 
            fill="#8884d8" 
            fillOpacity={0.1} 
            name="Upper Bound"
          />
          <Area 
             type="monotone" 
             dataKey="lower_bound" 
             stroke="none" 
             fill="#8884d8" 
             fillOpacity={0.1} 
             name="Lower Bound"
           />

          {/* Lines */}
          <Line 
            type="monotone" 
            dataKey="historical_price" 
            stroke="#ffc658" 
            strokeWidth={2}
            dot={false}
            name="Historical Price"
          />
          <Line 
            type="monotone" 
            dataKey="predicted_price" 
            stroke="#8884d8" 
            strokeWidth={3} 
            strokeDasharray="5 5"
            dot={{ r: 3 }}
            name="Forecast Price"
          />
          <Line 
            type="monotone" 
            dataKey="sma_20" 
            stroke="#82ca9d" 
            strokeWidth={1.5}
            dot={false}
            name="SMA 20"
          />
          <Line 
            type="monotone" 
            dataKey="sma_50" 
            stroke="#ff7300" 
            strokeWidth={1.5}
            dot={false}
            name="SMA 50"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ForecastChart;
