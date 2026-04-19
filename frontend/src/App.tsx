import { useState, useEffect } from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    try {
      const token = localStorage.getItem('access_token');
      setIsAuthenticated(!!token);
    } catch (e) {
      setIsAuthenticated(false);
    }
  }, []);

  if (isAuthenticated === null) return <div>Loading NeuralQueue...</div>;

  return (
    <div className="min-h-screen bg-background">
      {isAuthenticated ? (
        <Dashboard />
      ) : (
        <div className="flex items-center justify-center min-h-screen">
          <Login onLoginSuccess={() => setIsAuthenticated(true)} />
        </div>
      )}
    </div>
  );
}