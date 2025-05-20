import React, { useEffect, useState } from 'react';
import axios from 'axios';
import PicksTable from '../components/PicksTable';
import PositionsTable from '../components/PositionsTable';
import SectorPerformance from '../components/SectorPerformance';

const Dashboard: React.FC = () => {
  const [picks, setPicks] = useState([]);
  const [positions, setPositions] = useState([]);

  useEffect(() => {
    axios.get('http://127.0.0.1:5001/picks')
      .then((response) => setPicks(response.data))
      .catch((error) => console.error('Error fetching picks:', error));

    axios.get('http://127.0.0.1:5001/positions')
      .then((response) => setPositions(response.data))
      .catch((error) => console.error('Error fetching positions:', error));
  }, []);

  return (
    <div className="container">
      <h1>Stock Sniper Dashboard</h1>
      
      <div className="top-section">
        <div className="card">
          <h2>Daily AI Stock Picks</h2>
          <PicksTable type="ai" picks={picks} />
        </div>
        <div className="card">
          <h2>Daily Manual Stock Picks</h2>
          <PicksTable type="manual" picks={picks} />
        </div>
        <div className="card">
          <h2>Market Sectors</h2>
          <SectorPerformance />
        </div>
      </div>

      <div className="bottom-section">
        <div className="card">
          <h2>Current Long Positions</h2>
          <PositionsTable type="long" positions={positions} />
        </div>
        <div className="card">
          <h2>Current Short Positions</h2>
          <PositionsTable type="short" positions={positions} />
        </div>
        <div className="card">
          <h2>Old Trades</h2>
          <PositionsTable type="closed" positions={positions} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
