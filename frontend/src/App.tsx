import { useState, useEffect } from 'react';
import Login from './components/Login';
import Register from './components/Register';
import Dashboard from './components/Dashboard';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [isRegistering, setIsRegistering] = useState<boolean>(false);

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
        <div className="flex flex-col items-center justify-center min-h-screen space-y-6">
          {isRegistering ? (
            <>
              <Register onRegisterSuccess={() => setIsRegistering(false)} />
              <button 
                onClick={() => setIsRegistering(false)}
                className="text-slate-400 hover:text-sky-400 text-sm transition-colors"
              >
                Already have an account? <span className="font-bold">Sign In</span>
              </button>
            </>
          ) : (
            <>
              <Login onLoginSuccess={() => setIsAuthenticated(true)} />
              <button 
                onClick={() => setIsRegistering(true)}
                className="text-slate-400 hover:text-emerald-400 text-sm transition-colors"
              >
                Don't have an account? <span className="font-bold">Sign Up</span>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}