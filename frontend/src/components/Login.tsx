import { useState } from 'react';
import api from '../services/api';

export default function Login({ onLoginSuccess }: { onLoginSuccess: () => void }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const response = await api.post('/api/v1/users/login', { email, password });
            localStorage.setItem('access_token', response.data.access_token);
            localStorage.setItem('refresh_token', response.data.refresh_token);
            onLoginSuccess();
        } catch (error) {
            alert('Authentication failed. Check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-md bg-surface border border-slate-800 rounded-3xl p-8 shadow-2xl">
            <h2 className="text-2xl font-bold text-accent mb-6">Welcome Back</h2>
            <form onSubmit={handleLogin} className="space-y-4">
                <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase mb-1 ml-1">Email</label>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-accent transition-colors"
                        placeholder="johndoe@gmail.com"
                        required
                    />
                </div>
                <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase mb-1 ml-1">Password</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-accent transition-colors"
                        placeholder="••••••••"
                        required
                    />
                </div>
                <button
                    disabled={loading}
                    className="w-full bg-accent hover:bg-sky-400 text-slate-950 font-bold py-4 rounded-2xl transition-all active:scale-95 disabled:opacity-50"
                >
                    {loading ? 'Authenticating...' : 'Sign In'}
                </button>
            </form>
        </div>
    );
}