import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import Picks from './components/Picks';
import Positions from './components/Positions';
import Trades from './components/Trades';

function App() {
  return (
    <Router>
      <div className="App" style={{ fontFamily: 'Architects Daughter, cursive' }}>
        <nav>
          <ul>
            <li><Link to="/picks">Stock Picks</Link></li>
            <li><Link to="/positions">Positions</Link></li>
            <li><Link to="/trades">Trade History</Link></li>
          </ul>
        </nav>
        <Routes>
          <Route path="/picks" element={<Picks />} />
          <Route path="/positions" element={<Positions />} />
          <Route path="/trades" element={<Trades />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
