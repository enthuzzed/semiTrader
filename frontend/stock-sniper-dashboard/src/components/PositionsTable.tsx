import React from 'react';

interface PositionsTableProps {
  type: 'long' | 'short' | 'closed';
  positions?: Array<{
    ticker: string;
    entry_price: number;
    exit_price: number | null;
    status: string;
    performance: number | null;
  }>;
}

const PositionsTable: React.FC<PositionsTableProps> = ({ type, positions = [] }) => {
  const filteredPositions = positions.filter((position) => position.status === type);

  return (
    <div className="position-table">
      <table>
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Performance</th>
            <th>Entry Price</th>
            <th>Exit Price</th>
          </tr>
        </thead>
        <tbody>
          {filteredPositions.map((position, index) => (
            <tr key={index}>
              <td>${position.ticker}</td>
              <td>{position.performance !== null ? `${position.performance > 0 ? '+' : ''}${position.performance}%` : ''}</td>
              <td>{position.entry_price}</td>
              <td>{position.exit_price || ''}</td>
            </tr>
          ))}
          <tr>
            <td>...</td>
            <td>...</td>
            <td>...</td>
            <td>...</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

export default PositionsTable;
