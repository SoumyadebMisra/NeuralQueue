import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Activity, CheckCircle2, Clock } from 'lucide-react';
import { taskService } from '../services/taskService';
import type { Task } from '../services/taskService';

export default function Dashboard() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [input, setInput] = useState('');

    const fetchTasks = async () => {
        try {
            const { data } = await taskService.getTasks();
            setTasks(data);
        } catch (err) { console.error(err); }
    };

    const submitTask = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input) return;

        try {
            const taskData = JSON.parse(input);

            await taskService.createTask(taskData);

            setInput('');
            fetchTasks();
        } catch (err) {
            console.error("Payload Error:", err);
            alert("Check console for validation errors. Ensure 'name' and 'model' are present.");
        }
    };

    useEffect(() => { fetchTasks(); }, []);

    return (
        <div className="max-w-5xl mx-auto w-full space-y-8 p-4">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-slate-100">NeuralQueue</h1>
                    <p className="text-slate-500">Real-time Task Orchestration</p>
                </div>
                <div className="flex gap-4 text-xs font-mono uppercase tracking-widest text-accent bg-accent/5 px-4 py-2 rounded-full border border-accent/20">
                    <Activity className="w-4 h-4 animate-pulse" />
                    Worker Status: Active
                </div>
            </header>

            <div className="grid md:grid-cols-3 gap-8">
                <form onSubmit={submitTask} className="md:col-span-1 space-y-4">
                    <div className="bg-surface border border-slate-800 p-6 rounded-3xl space-y-4 shadow-xl">
                        <h3 className="font-semibold text-slate-300">Enqueue New Task</h3>
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            className="w-full h-32 bg-background border border-slate-800 rounded-2xl p-4 text-sm focus:ring-1 focus:ring-accent focus:outline-none transition-all"
                            placeholder="Enter JSON payload..."
                        />
                        <button className="w-full bg-accent text-slate-900 font-bold py-3 rounded-xl flex items-center justify-center gap-2 hover:bg-sky-400 transition-all active:scale-95">
                            <Plus className="w-5 h-5" /> Enqueue
                        </button>
                    </div>
                </form>

                <div className="md:col-span-2 space-y-4">
                    <h3 className="font-semibold text-slate-300 flex items-center gap-2">
                        <Clock className="w-4 h-4 text-slate-500" /> Recent Activity
                    </h3>
                    <div className="space-y-3">
                        <AnimatePresence>
                            {tasks.map((task) => (
                                <motion.div
                                    key={task.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    className="bg-surface/50 border border-slate-800/50 p-4 rounded-2xl flex items-center justify-between group hover:border-slate-700 transition-colors"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className={`p-2 rounded-lg ${task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'
                                            }`}>
                                            {task.status === 'completed' ? <CheckCircle2 className="w-5 h-5" /> : <Activity className="w-5 h-5 animate-spin-slow" />}
                                        </div>
                                        <div>
                                            <div className="text-sm font-medium text-slate-200">Task #{task.id.slice(0, 8)}</div>
                                            <div className="text-xs text-slate-500 font-mono">{task.status}</div>
                                        </div>
                                    </div>
                                    <div className="text-xs text-slate-600 font-mono group-hover:text-slate-400">
                                        {new Date(task.created_at).toLocaleTimeString()}
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </div>
    );
}