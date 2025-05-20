import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Position {
  id: number;
  ticker: string;
  entry_price: number;
  exit_price: number | null;
  current_price: number | null;
  daily_change: number | null;
  status: string;
  performance: number | null;
}

interface Trade {
  id: number;
  ticker: string;
  entry_price: number;
  exit_price: number;
  performance: number;
  date_closed: string;
}

interface PositionsTableProps {
  type: 'long' | 'short' | 'closed';
  positions?: Position[];
}

const PositionsTable: React.FC<PositionsTableProps> = ({ type }) => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);

  useEffect(() => {
    const fetchData = () => {
      // Fetch positions
      axios.get('http://127.0.0.1:5001/positions')
        .then(response => setPositions(response.data))
        .catch(error => console.error('Error fetching positions:', error));

      // Fetch trade history for closed positions
      if (type === 'closed') {
        axios.get('http://127.0.0.1:5001/trades')
          .then(response => setTrades(response.data))
          .catch(error => console.error('Error fetching trades:', error));
      }
    };

    fetchData();
    // Refresh every 30 seconds instead of every minute to get more frequent updates
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [type]);

  const calculateRealTimePerformance = (position: Position) => {
    if (!position.current_price) return position.performance;
    
    if (position.status === 'long') {
      return ((position.current_price - position.entry_price) / position.entry_price) * 100;
    } else {
      return ((position.entry_price - position.current_price) / position.entry_price) * 100;
    }
  };

  const formatPerformance = (perf: number | null) => {
    if (perf === null) return '';
    return `${perf > 0 ? '+' : ''}${perf.toFixed(2)}%`;
  };

  const formatPrice = (price: number | null) => {
    if (price === null) return '';
    return `$${price.toFixed(2)}`;
  };

  const getTrendArrow = (change: number | null) => {
    if (change === null) return '';
    if (change > 0) return '▲';
    if (change < 0) return '▼';
    return '─';
  };

  const getTrendStyle = (change: number | null) => {
    if (change === null) return {};
    return {
      color: change > 0 ? '#2ecc71' : change < 0 ? '#e74c3c' : '#95a5a6'
    };
  };

  const displayData = type === 'closed' ? trades : positions.filter(p => p.status === type);

  return (
    <div className="position-table">
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Performance</th>
              <th>Entry Price</th>
              {type !== 'closed' && (
                <>
                  <th>Current Price</th>
                  <th>Daily Trend</th>
                </>
              )}
              {type === 'closed' ? <th>Exit Price</th> : null}
              {type === 'closed' && <th>Date Closed</th>}
            </tr>
          </thead>
          <tbody>
            {displayData.map((item) => (
              <tr key={item.id}>
                <td className="ticker-column">${item.ticker}</td>
                <td className={
                  (type === 'closed' ? (item.performance ?? 0) : (calculateRealTimePerformance(item as Position) ?? 0)) > 0 
                    ? 'positive' 
                    : 'negative'
                }>
                  {formatPerformance(
                    type === 'closed' 
                      ? item.performance 
                      : calculateRealTimePerformance(item as Position)
                  )}
                </td>
                <td>{formatPrice(item.entry_price)}</td>
                {type !== 'closed' && (
                  <>
                    <td>{formatPrice((item as Position).current_price)}</td>
                    <td style={getTrendStyle((item as Position).daily_change)}>
                      {getTrendArrow((item as Position).daily_change)}
                      {(item as Position).daily_change !== null ? 
                        ` ${Math.abs((item as Position).daily_change!).toFixed(2)}%` 
                        : ''}
                    </td>
                  </>
                )}
                {type === 'closed' ? (
                  <td>{formatPrice((item as Trade).exit_price)}</td>
                ) : null}
                {type === 'closed' && (
                  <td>{(item as Trade).date_closed}</td>
                )}
              </tr>
            ))}
            {displayData.length === 0 && (
              <tr>
                <td colSpan={type === 'closed' ? 5 : 6} className="empty-message">
                  No positions found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PositionsTable;
