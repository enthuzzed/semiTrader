import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface StockPick {
  id: number;
  ticker: string;
  source: 'Manual' | 'AI';
  date: string;
  mention_count?: number;
}

interface Position {
  id: number;
  ticker: string;
  entry_price: number;
  exit_price?: number;
  status: 'long' | 'short' | 'closed';
  performance?: number;
  current_price?: number;
}

interface NewPosition {
  ticker: string;
  entry_price: number;
  status: 'long' | 'short';
}

const AdminDashboard: React.FC = () => {
  const [picks, setPicks] = useState<StockPick[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [newPick, setNewPick] = useState({ ticker: '', source: 'Manual' as const, position_type: 'long' as 'long' | 'short' });
  const [newPosition, setNewPosition] = useState<NewPosition>({ ticker: '', entry_price: 0, status: 'long' });
  const [message, setMessage] = useState('');
  const [closingPosition, setClosingPosition] = useState<{ id: number; exitPrice: string } | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [picksRes, positionsRes] = await Promise.all([
        axios.get('http://127.0.0.1:5001/picks'),
        axios.get('http://127.0.0.1:5001/positions')
      ]);
      setPicks(picksRes.data);
      setPositions(positionsRes.data);
    } catch (error) {
      setMessage('Error fetching data');
    }
  };

  const handlePickSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('http://127.0.0.1:5001/picks', newPick);
      setMessage('Stock pick added successfully!');
      setNewPick({ ticker: '', source: 'Manual', position_type: 'long' });
      fetchData();
    } catch (error) {
      setMessage('Error adding stock pick');
    }
  };

  const handlePositionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('http://127.0.0.1:5001/positions', newPosition);
      setMessage('Position added successfully!');
      setNewPosition({ ticker: '', entry_price: 0, status: 'long' });
      fetchData();
    } catch (error) {
      setMessage('Error adding position');
    }
  };

  const handlePositionClose = async (position: Position) => {
    if (!closingPosition?.exitPrice) return;

    try {
      await axios.put(`http://127.0.0.1:5001/positions/${position.id}`, {
        exit_price: parseFloat(closingPosition.exitPrice)
      });
      setMessage('Position closed and moved to trade history!');
      setClosingPosition(null);
      fetchData();
    } catch (error) {
      setMessage('Error closing position');
    }
  };

  const handlePositionDelete = async (position: Position) => {
    if (!window.confirm(`Are you sure you want to delete ${position.ticker} position?`)) return;

    try {
      await axios.delete(`http://127.0.0.1:5001/positions/${position.id}`);
      setMessage('Position deleted successfully!');
      fetchData();
    } catch (error) {
      setMessage('Error deleting position');
    }
  };

  const handlePickDelete = async (pickId: number) => {
    if (!window.confirm('Are you sure you want to delete this pick?')) return;

    try {
      await axios.delete(`http://127.0.0.1:5001/picks/${pickId}`);
      setMessage('Pick deleted successfully!');
      fetchData();
    } catch (error) {
      setMessage('Error deleting pick');
    }
  };

  return (
    <div className="container">
      <h1>Admin Dashboard</h1>
      
      {message && (
        <div className="alert" style={{ margin: '20px 0', padding: '10px', background: '#e0e0e0' }}>
          {message}
        </div>
      )}

      <div className="admin-section" style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
        <div className="card" style={{ flex: 1 }}>
          <h2>Add Manual Stock Pick</h2>
          <form onSubmit={handlePickSubmit}>
            <div className="form-group">
              <label>Ticker:</label>
              <input
                type="text"
                value={newPick.ticker}
                onChange={(e) => setNewPick({ ...newPick, ticker: e.target.value.toUpperCase() })}
                required
              />
            </div>
            <div className="form-group">
              <label>Position Type:</label>
              <select
                value={newPick.position_type}
                onChange={(e) => setNewPick({ ...newPick, position_type: e.target.value as 'long' | 'short' })}
                required
              >
                <option value="long">Long</option>
                <option value="short">Short</option>
              </select>
            </div>
            <button type="submit">Add Stock Pick</button>
          </form>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <h2>Add New Position</h2>
          <form onSubmit={handlePositionSubmit}>
            <div className="form-group">
              <label>Ticker:</label>
              <input
                type="text"
                value={newPosition.ticker}
                onChange={(e) => setNewPosition({ ...newPosition, ticker: e.target.value.toUpperCase() })}
                required
              />
            </div>
            <div className="form-group">
              <label>Entry Price:</label>
              <input
                type="number"
                step="0.01"
                value={newPosition.entry_price}
                onChange={(e) => setNewPosition({ ...newPosition, entry_price: parseFloat(e.target.value) })}
                required
              />
            </div>
            <div className="form-group">
              <label>Position Type:</label>
              <select
                value={newPosition.status}
                onChange={(e) => setNewPosition({ ...newPosition, status: e.target.value as 'long' | 'short' })}
              >
                <option value="long">Long</option>
                <option value="short">Short</option>
              </select>
            </div>
            <button type="submit">Add Position</button>
          </form>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '20px' }}>
        <div className="card" style={{ flex: 1 }}>
          <h2>Current Stock Picks</h2>
          <table style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Source</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {picks.map((pick) => (
                <tr key={pick.id}>
                  <td>${pick.ticker}</td>
                  <td>{pick.source}</td>
                  <td>{pick.date}</td>
                  <td>
                    {pick.source === 'Manual' && (
                      <button onClick={() => handlePickDelete(pick.id)}>Delete</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <h2>Current Positions</h2>
          <table style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Type</th>
                <th>Entry Price</th>
                <th>Current Price</th>
                <th>Performance</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => (
                <tr key={position.id}>
                  <td>${position.ticker}</td>
                  <td>{position.status}</td>
                  <td>${position.entry_price.toFixed(2)}</td>
                  <td>${position.current_price?.toFixed(2) || '-'}</td>
                  <td className={position.performance && position.performance > 0 ? 'positive' : 'negative'}>
                    {position.performance ? `${position.performance.toFixed(2)}%` : '-'}
                  </td>
                  <td>
                    {closingPosition?.id === position.id ? (
                      <div style={{ display: 'flex', gap: '5px' }}>
                        <input
                          type="number"
                          step="0.01"
                          value={closingPosition.exitPrice}
                          onChange={(e) => setClosingPosition({ ...closingPosition, exitPrice: e.target.value })}
                          placeholder="Exit price"
                          style={{ width: '80px' }}
                        />
                        <button onClick={() => handlePositionClose(position)}>Confirm</button>
                        <button onClick={() => setClosingPosition(null)}>Cancel</button>
                      </div>
                    ) : (
                      <>
                        <button 
                          onClick={() => setClosingPosition({ id: position.id, exitPrice: '' })} 
                          style={{ marginRight: '5px' }}
                        >
                          Close
                        </button>
                        <button onClick={() => handlePositionDelete(position)}>Delete</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;