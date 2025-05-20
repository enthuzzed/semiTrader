import React from 'react';

interface PicksTableProps {
  type: 'ai' | 'manual';
  picks?: Array<{
    ticker: string;
    source: string;
    date: string;
    mention_count?: number;
    twitter_users?: string[];
  }>;
}

const PicksTable: React.FC<PicksTableProps> = ({ type, picks = [] }) => {
  const filteredPicks = picks
    .filter((pick) => pick.source === (type === 'ai' ? 'AI' : 'Manual'))
    .sort((a, b) => (b.mention_count || 0) - (a.mention_count || 0));

  return (
    <div className="stock-list">
      {type === 'ai' ? (
        filteredPicks.map((pick, index) => (
          <div key={index} className="stock-item">
            <span className="stock-symbol">${pick.ticker}</span>
            {pick.mention_count && (
              <span className="mention-count">
                ({pick.mention_count} mentions)
              </span>
            )}
          </div>
        ))
      ) : (
        filteredPicks.map((pick, index) => (
          <div key={index} className="stock-item">
            <span className="stock-symbol">${pick.ticker}</span>
          </div>
        ))
      )}
      {filteredPicks.length === 0 && <div>...</div>}
    </div>
  );
};

export default PicksTable;
