import React from 'react';

interface PicksTableProps {
  type: 'ai' | 'manual';
  picks?: Array<{
    ticker: string;
    source: string;
    date: string;
    mention_count?: number;
    twitter_users?: string[];
    position_type?: 'long' | 'short';
    current_price?: number | null;
    daily_change?: number | null;
  }>;
}

const PicksTable: React.FC<PicksTableProps> = ({ type, picks = [] }) => {
  const filteredPicks = picks
    .filter((pick) => pick.source === (type === 'ai' ? 'AI' : 'Manual'))
    .sort((a, b) => (b.mention_count || 0) - (a.mention_count || 0));

  const formatPrice = (price: number | null | undefined) => {
    if (price === null || price === undefined) return '';
    return `$${price.toFixed(2)}`;
  };

  const getTrendArrow = (change: number | null | undefined) => {
    if (change === null || change === undefined) return '';
    if (change > 0) return '▲';
    if (change < 0) return '▼';
    return '─';
  };

  const getTrendStyle = (change: number | null | undefined) => {
    if (change === null || change === undefined) return {};
    return {
      color: change > 0 ? '#2ecc71' : change < 0 ? '#e74c3c' : '#95a5a6'
    };
  };

  return (
    <div className="stock-list-container">
      <div className="stock-list" role="list">
        {type === 'ai' ? (
          filteredPicks.map((pick, index) => (
            <div key={index} className="stock-item" role="listitem">
              <div className="stock-info">
                <span className="stock-symbol">${pick.ticker}</span>
                {pick.mention_count && (
                  <span className="mention-count">
                    ({pick.mention_count} mentions)
                  </span>
                )}
              </div>
              <div className="stock-price-info">
                <span className="current-price">{formatPrice(pick.current_price)}</span>
                <span className="daily-trend" style={getTrendStyle(pick.daily_change)}>
                  {getTrendArrow(pick.daily_change)}
                  {pick.daily_change !== null && pick.daily_change !== undefined ? 
                    ` ${Math.abs(pick.daily_change).toFixed(2)}%` 
                    : ''}
                </span>
              </div>
            </div>
          ))
        ) : (
          filteredPicks.map((pick, index) => (
            <div key={index} className="stock-item" role="listitem">
              <div className="stock-info">
                <span className="stock-symbol">${pick.ticker}</span>
                {pick.position_type && (
                  <span className={`position-type ${pick.position_type}`}>
                    ({pick.position_type})
                  </span>
                )}
              </div>
              <div className="stock-price-info">
                <span className="current-price">{formatPrice(pick.current_price)}</span>
                <span className="daily-trend" style={getTrendStyle(pick.daily_change)}>
                  {getTrendArrow(pick.daily_change)}
                  {pick.daily_change !== null && pick.daily_change !== undefined ? 
                    ` ${Math.abs(pick.daily_change).toFixed(2)}%` 
                    : ''}
                </span>
              </div>
            </div>
          ))
        )}
        {filteredPicks.length === 0 && (
          <div className="stock-item empty-message">No picks found</div>
        )}
      </div>
    </div>
  );
};

export default PicksTable;
