import { useState } from 'react';
import api from '../services/api';

export default function Register({ onRegisterSuccess }: { onRegisterSuccess: () => void }) {
    const [email, setEmail] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post('/api/v1/users/register', { 
                email, 
                username, 
                password 
            });
            alert('Account created! Please log in.');
            onRegisterSuccess();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Registration failed.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-md bg-surface border border-slate-800 rounded-3xl p-8 shadow-2xl">
            <h2 className="text-2xl font-bold text-emerald-400 mb-6">Create Account</h2>
            <form onSubmit={handleRegister} className="space-y-4">
                <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase mb-1 ml-1">Username</label>
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-emerald-500 transition-colors text-slate-200"
                        placeholder="soumyadeb_99"
                        required
                    />
                </div>

                <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase mb-1 ml-1">Email</label>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-emerald-500 transition-colors text-slate-200"
                        placeholder="name@example.com"
                        required
                    />
                </div>

                <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase mb-1 ml-1">Password</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-emerald-500 transition-colors text-slate-200"
                        placeholder="••••••••"
                        required
                    />
                </div>

                <button
                    disabled={loading}
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold py-4 rounded-2xl transition-all active:scale-95 disabled:opacity-50 mt-2"
                >
                    {loading ? 'Processing...' : 'Create Account'}
                </button>
            </form>
        </div>
    );
}