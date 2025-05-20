import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface SectorData {
  ticker: string;
  name: string;
  performance: number;
}

const SectorPerformance: React.FC = () => {
  const [sectors, setSectors] = useState<SectorData[]>([
    { ticker: 'XLK', name: 'Technology', performance: 0 },
    { ticker: 'XLF', name: 'Financials', performance: 0 },
    { ticker: 'XLE', name: 'Energy', performance: 0 },
    { ticker: 'XLV', name: 'Healthcare', performance: 0 },
    { ticker: 'XLI', name: 'Industrials', performance: 0 },
    { ticker: 'XLP', name: 'Consumer Staples', performance: 0 },
    { ticker: 'XLY', name: 'Consumer Discretionary', performance: 0 },
    { ticker: 'XLB', name: 'Materials', performance: 0 },
    { ticker: 'XLRE', name: 'Real Estate', performance: 0 },
    { ticker: 'XLU', name: 'Utilities', performance: 0 }
  ]);

  useEffect(() => {
    const fetchSectorData = () => {
      const tickers = sectors.map(s => s.ticker).join(',');
      axios.get(`http://127.0.0.1:5001/sectors?tickers=${tickers}`)
        .then(response => {
          setSectors(prev => prev.map(sector => ({
            ...sector,
            performance: response.data[sector.ticker]?.daily_change ?? 0
          })));
        })
        .catch(error => console.error('Error fetching sector data:', error));
    };

    fetchSectorData();
    const interval = setInterval(fetchSectorData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getTrendStyle = (performance: number) => ({
    color: performance > 0 ? 'var(--positive)' : performance < 0 ? 'var(--negative)' : 'var(--neutral)'
  });

  const getTrendArrow = (performance: number) => {
    if (performance > 0) return '▲';
    if (performance < 0) return '▼';
    return '─';
  };

  return (
    <div className="sectors-grid">
      {sectors.map((sector) => (
        <div key={sector.ticker} className="sector-item">
          <div className="sector-header">
            <span className="sector-ticker">${sector.ticker}</span>
            <span className="sector-name">{sector.name}</span>
          </div>
          <div className="sector-performance" style={getTrendStyle(sector.performance)}>
            {getTrendArrow(sector.performance)}
            {` ${Math.abs(sector.performance).toFixed(2)}%`}
          </div>
        </div>
      ))}
    </div>
  );
};

export default SectorPerformance;