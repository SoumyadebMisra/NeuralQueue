import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Activity, CheckCircle2, Clock, AlertTriangle, Wifi, WifiOff, Zap, Cpu, RotateCcw, Trash2, Settings, Key, MessageSquare, ChevronDown, ChevronUp, BarChart3 } from 'lucide-react';
import { taskService } from '../services/taskService';
import type { Task, TaskCreatePayload } from '../services/taskService';
import { userService } from '../services/userService';
import { useWebSocket } from '../hooks/useWebSocket';

const PRIORITY_STYLES: Record<string, string> = {
    critical: 'bg-red-500/15 text-red-400 border-red-500/30',
    high: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    medium: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    low: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
};

const STATUS_STYLES: Record<string, { bg: string; icon: React.ReactNode }> = {
    queued: { bg: 'bg-slate-500/10 text-slate-400', icon: <Clock className="w-4 h-4" /> },
    scoring: { bg: 'bg-blue-500/10 text-blue-400', icon: <Zap className="w-4 h-4 animate-pulse" /> },
    processing: { bg: 'bg-amber-500/10 text-amber-400', icon: <Activity className="w-4 h-4 animate-spin" /> },
    completed: { bg: 'bg-emerald-500/10 text-emerald-400', icon: <CheckCircle2 className="w-4 h-4" /> },
    failed: { bg: 'bg-red-500/10 text-red-400', icon: <AlertTriangle className="w-4 h-4" /> },
};

const MODELS = [
    { id: 'gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI', weight: 0.2 },
    { id: 'gemini/gemini-3.1-pro-preview', name: 'Gemini 3.1 Pro (Preview)', provider: 'Google', weight: 0.8 },
    { id: 'gemini/gemini-3.1-flash-lite-preview', name: 'Gemini 3.1 Flash Lite (Preview)', provider: 'Google', weight: 0.2 },
    { id: 'gemini/gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'Google', weight: 0.2 },
    { id: 'ollama/llama3', name: 'Llama 3 (Local)', provider: 'Local', weight: 1.2 },
    { id: 'ollama/mistral', name: 'Mistral (Local)', provider: 'Local', weight: 1.0 },
];

const WS_URL = (import.meta.env.VITE_WS_URL as string) || 'ws://localhost:8000/ws/events';

export default function Dashboard() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [name, setName] = useState('');
    const [model, setModel] = useState(MODELS[0].id);
    const [inputText, setInputText] = useState('');
    const [priority, setPriority] = useState('low');
    const [submitting, setSubmitting] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [openaiKey, setOpenaiKey] = useState('');
    const [anthropicKey, setAnthropicKey] = useState('');
    const [geminiKey, setGeminiKey] = useState('');
    const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
    const [localWorkerStatus, setLocalWorkerStatus] = useState('offline');


    const { lastEvent, connected } = useWebSocket(WS_URL);

    const fetchTasks = async () => {
        try {
            const { data } = await taskService.getTasks();
            setTasks(data);
        } catch (err) {
            console.error(err);
        }
    };

    const fetchUser = async () => {
        try {
            const { data } = await userService.getMe();
            setOpenaiKey(data.openai_api_key || '');
            setAnthropicKey(data.anthropic_api_key || '');
            setGeminiKey(data.gemini_api_key || '');
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => {
        fetchTasks();
        fetchUser();
    }, []);

    useEffect(() => {
        if (!lastEvent) return;

        if (lastEvent.type === 'task_chunk') {
            setTasks(prev => prev.map(t => 
                t.id === lastEvent.task_id 
                ? { ...t, output_text: (t.output_text || '') + lastEvent.chunk, status: 'processing' } 
                : t
            ));
        } else if (lastEvent.type === 'local_worker_status') {
            setLocalWorkerStatus(lastEvent.status);
        } else {
            fetchTasks();
        }
    }, [lastEvent]);

    const saveKeys = async () => {
        try {
            await userService.updateMe({ 
                openai_api_key: openaiKey, 
                anthropic_api_key: anthropicKey,
                gemini_api_key: geminiKey
            });
            setShowSettings(false);
        } catch (err) {
            console.error(err);
        }
    };

    const deleteTask = async (taskId: string) => {
        try {
            await taskService.deleteTask(taskId);
            setTasks(prev => prev.filter(t => t.id !== taskId));
        } catch (err) {
            console.error(err);
        }
    };

    const handleRetryTask = async (taskId: string) => {
        try {
            await taskService.retryTask(taskId);
            // The WS will trigger a refresh, but we fetch for immediate UI update
            fetchTasks();
        } catch (err) {
            console.error(err);
        }
    };

    const submitTask = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name || !model || !inputText) return;
        setSubmitting(true);

        try {
            const payload: TaskCreatePayload = {
                name,
                model,
                input_text: inputText,
                priority,
            };
            await taskService.createTask(payload);
            setName('');
            setInputText('');
            setPriority('low');
        } catch (err) {
            console.error(err);
        } finally {
            setSubmitting(false);
        }
    };

    const queuedCount = tasks.filter(t => t.status === 'queued').length;
    const processingCount = tasks.filter(t => t.status === 'processing').length;
    const completedCount = tasks.filter(t => t.status === 'completed').length;

    // Calculate predicted scale (local UI simulation)
    const selectedModel = MODELS.find(m => m.id === model);
    const predictedScale = Math.max(1, Math.min(16, Math.floor((selectedModel?.weight || 0.5) * 5 + inputText.length / 300)));

    return (
        <div className="max-w-6xl mx-auto w-full space-y-8 p-6">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-slate-100 tracking-tight">NeuralQueue</h1>
                    <p className="text-slate-500 text-sm italic">Intelligent AI Resource Orchestrator</p>
                </div>
                <div className="flex items-center gap-4">
                    <button 
                        onClick={() => setShowSettings(!showSettings)}
                        className={`p-2.5 rounded-xl border transition-all ${showSettings ? 'bg-slate-800 border-slate-700 text-sky-400' : 'bg-surface border-slate-800 text-slate-400 hover:text-slate-200'}`}
                    >
                        <Settings className="w-5 h-5" />
                    </button>
                    
                    <div className="flex flex-col items-end gap-1.5">
                        <div className={`flex items-center gap-2 text-[9px] font-mono uppercase tracking-[0.2em] px-3 py-1.5 rounded-lg border leading-none ${localWorkerStatus === 'online' ? 'text-emerald-400 bg-emerald-500/5 border-emerald-500/20' : localWorkerStatus === 'starting' ? 'text-amber-400 bg-amber-500/5 border-amber-500/20' : 'text-slate-500 bg-slate-500/5 border-slate-500/20'}`}>
                            <Cpu className={`w-2.5 h-2.5 ${localWorkerStatus === 'starting' ? 'animate-pulse' : ''}`} />
                            Local: {localWorkerStatus}
                        </div>
                        <div className={`flex items-center gap-2 text-[9px] font-mono uppercase tracking-[0.2em] px-3 py-1.5 rounded-lg border leading-none ${connected ? 'text-sky-400 bg-sky-500/5 border-sky-500/20' : 'text-red-400 bg-red-500/5 border-red-500/20'}`}>
                            {connected ? <Wifi className="w-2.5 h-2.5" /> : <WifiOff className="w-2.5 h-2.5" />}
                            Orchestrator: {connected ? 'Live' : 'Offline'}
                        </div>
                    </div>
                </div>
            </header>

            <AnimatePresence>
                {showSettings && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="bg-surface border border-slate-800 rounded-3xl p-6 mb-8 space-y-6 shadow-2xl">
                            <div className="flex items-center gap-2 text-slate-300 font-semibold mb-2">
                                <Key className="w-4 h-4 text-sky-400" /> API Settings
                            </div>
                            <div className="grid md:grid-cols-3 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">OpenAI Key</label>
                                    <input
                                        type="password"
                                        value={openaiKey}
                                        onChange={(e) => setOpenaiKey(e.target.value)}
                                        className="w-full bg-background border border-slate-800 rounded-xl px-4 py-2.5 text-sm focus:ring-1 focus:ring-sky-500 outline-none"
                                        placeholder="sk-..."
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Anthropic Key</label>
                                    <input
                                        type="password"
                                        value={anthropicKey}
                                        onChange={(e) => setAnthropicKey(e.target.value)}
                                        className="w-full bg-background border border-slate-800 rounded-xl px-4 py-2.5 text-sm focus:ring-1 focus:ring-sky-500 outline-none"
                                        placeholder="sk-ant-..."
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Gemini Key (Free Tier)</label>
                                    <input
                                        type="password"
                                        value={geminiKey}
                                        onChange={(e) => setGeminiKey(e.target.value)}
                                        className="w-full bg-background border border-slate-800 rounded-xl px-4 py-2.5 text-sm focus:ring-1 focus:ring-sky-500 outline-none"
                                        placeholder="AIza..."
                                    />
                                </div>
                            </div>
                            <div className="flex justify-end pt-2">
                                <button 
                                    onClick={saveKeys}
                                    className="px-6 py-2 bg-sky-500 hover:bg-sky-400 text-slate-900 font-bold rounded-xl transition-all active:scale-95 text-sm"
                                >
                                    Save Credentials
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="grid grid-cols-3 gap-4">
                <div className="bg-surface border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-colors">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">In Queue</div>
                    <div className="text-2xl font-bold text-slate-200">{queuedCount}</div>
                </div>
                <div className="bg-surface border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-colors border-l-4 border-l-amber-500/30">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Streaming</div>
                    <div className="text-2xl font-bold text-amber-400">{processingCount}</div>
                </div>
                <div className="bg-surface border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-colors border-l-4 border-l-emerald-500/30">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Completed</div>
                    <div className="text-2xl font-bold text-emerald-400">{completedCount}</div>
                </div>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
                <form onSubmit={submitTask} className="md:col-span-1 space-y-4">
                    <div className="bg-surface border border-slate-800 p-6 rounded-3xl space-y-4 shadow-xl sticky top-6">
                        <div className="flex justify-between items-center">
                            <h3 className="font-semibold text-slate-300">Intelligent Dispatch</h3>
                            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-sky-500/10 border border-sky-500/20">
                                <BarChart3 className="w-3.5 h-3.5 text-sky-400" />
                                <span className="text-[10px] text-sky-400 font-bold uppercase">Scale: {predictedScale}x</span>
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Objective</label>
                            <input
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-1 focus:ring-accent focus:outline-none"
                                placeholder="Task title"
                                required
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Intelligence Layer</label>
                            <select
                                value={model}
                                onChange={(e) => setModel(e.target.value)}
                                className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-1 focus:ring-accent focus:outline-none appearance-none cursor-pointer"
                                required
                            >
                                {MODELS.map(m => (
                                    <option key={m.id} value={m.id}>{m.name}</option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Input Data (Prompt)</label>
                            <textarea
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-1 focus:ring-accent focus:outline-none min-h-[120px] resize-none"
                                placeholder="Type your prompt here..."
                                required
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Priority</label>
                            <select
                                value={priority}
                                onChange={(e) => setPriority(e.target.value)}
                                className="w-full bg-background border border-slate-800 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-accent"
                            >
                                <option value="low">Low Priority (Eco)</option>
                                <option value="medium">Medium Priority</option>
                                <option value="high">High Priority</option>
                                <option value="critical">Critical (Turbo)</option>
                            </select>
                        </div>

                        <button
                            disabled={submitting}
                            className="w-full bg-accent text-slate-900 font-bold py-4 rounded-xl flex items-center justify-center gap-2 hover:bg-sky-400 transition-all active:scale-95 disabled:opacity-50 shadow-lg shadow-sky-500/10"
                        >
                            <Plus className="w-5 h-5" />
                            {submitting ? 'Calculating...' : 'Execute Task'}
                        </button>
                    </div>
                </form>

                <div className="md:col-span-2 space-y-4">
                    <h3 className="font-semibold text-slate-300 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-slate-500" /> Intelligent Queue
                        <span className="text-xs text-slate-600 ml-auto font-mono">{tasks.length} total</span>
                    </h3>
                    <div className="space-y-3">
                        <AnimatePresence>
                            {[...tasks].reverse().map((task) => {
                                const statusStyle = STATUS_STYLES[task.status] || STATUS_STYLES.queued;
                                const priorityStyle = PRIORITY_STYLES[task.priority] || PRIORITY_STYLES.low;
                                const isExpanded = expandedTaskId === task.id || task.status === 'processing';

                                return (
                                    <motion.div
                                        key={task.id}
                                        layout
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, x: -20 }}
                                        className={`bg-surface/60 border border-slate-800/50 rounded-2xl overflow-hidden group hover:border-slate-700/80 transition-all ${isExpanded ? 'border-slate-700 ring-1 ring-slate-800 bg-surface/90' : ''}`}
                                    >
                                        <div className="p-4 flex items-center justify-between cursor-pointer" onClick={() => setExpandedTaskId(isExpanded ? null : task.id)}>
                                            <div className="flex items-center gap-4 min-w-0">
                                                <div className={`p-2.5 rounded-xl shrink-0 ${statusStyle.bg}`}>
                                                    {statusStyle.icon}
                                                </div>
                                                <div className="min-w-0">
                                                    <div className="text-sm font-semibold text-slate-200 truncate">{task.name}</div>
                                                    <div className="flex items-center gap-2 mt-1.5">
                                                        <span className={`text-[9px] px-2 py-0.5 rounded-full border font-bold uppercase tracking-tighter ${priorityStyle}`}>
                                                            {task.priority}
                                                        </span>
                                                        <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1 bg-slate-800/50 px-1.5 py-0.5 rounded-md">
                                                            <Cpu className="w-3 h-3" />Scale: {task.gpu_budget}x
                                                        </span>
                                                        <span className="text-[10px] text-slate-600 font-mono truncate max-w-[120px]">{task.model.split('/').pop()}</span>
                                                        {task.retries > 0 && (
                                                            <span className="text-[10px] text-orange-400 font-mono flex items-center gap-0.5">
                                                                <RotateCcw className="w-3 h-3" />{task.retries}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3 shrink-0 ml-4">
                                                <div className="text-right">
                                                    <div className="text-[10px] text-slate-600 font-mono">
                                                        {new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                    </div>
                                                    {task.latency_ms && (
                                                        <div className="text-[10px] text-emerald-500/80 font-mono font-bold">
                                                            {(task.latency_ms / 1000).toFixed(1)}s
                                                        </div>
                                                    )}
                                                </div>
                                                <div className="flex flex-col gap-1 items-center">
                                                    {task.status === 'failed' && (
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); handleRetryTask(task.id); }}
                                                            className="p-1.5 rounded-lg text-orange-400 hover:bg-orange-500/10 transition-all"
                                                            title="Retry Task"
                                                        >
                                                            <RotateCcw className="w-3.5 h-3.5" />
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); deleteTask(task.id); }}
                                                        className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-all"
                                                    >
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </button>
                                                    {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
                                                </div>
                                            </div>
                                        </div>
                                        
                                        <AnimatePresence>
                                            {isExpanded && (
                                                <motion.div 
                                                    initial={{ height: 0 }}
                                                    animate={{ height: 'auto' }}
                                                    exit={{ height: 0 }}
                                                    className="overflow-hidden bg-background/40 border-t border-slate-800/50"
                                                >
                                                    <div className="p-4 space-y-4">
                                                        <div className="space-y-1.5">
                                                            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 uppercase tracking-wider">
                                                                <MessageSquare className="w-3 h-3 text-sky-500" /> Input Data
                                                            </div>
                                                            <p className="text-xs text-slate-400 bg-slate-900/50 p-3 rounded-xl border border-slate-800/50 italic whitespace-pre-wrap">
                                                                {task.input_text || task.name}
                                                            </p>
                                                        </div>
                                                        {(task.output_text || task.status === 'processing') && (
                                                            <div className="space-y-1.5">
                                                                <div className="flex items-center gap-1.5 text-[10px] text-emerald-500 uppercase tracking-wider">
                                                                    <Zap className="w-3.5 h-3.5" /> Task Output {task.status === 'processing' && '(Streaming...)'}
                                                                </div>
                                                                <div className="text-xs text-slate-300 bg-slate-950/50 p-4 rounded-xl border border-emerald-500/10 font-serif leading-relaxed min-h-[60px] whitespace-pre-wrap">
                                                                    {task.output_text}
                                                                    {task.status === 'processing' && <span className="inline-block w-1.5 h-4 bg-emerald-500 animate-pulse ml-1 align-middle" />}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </motion.div>
                                );
                            })}
                        </AnimatePresence>
                        {tasks.length === 0 && (
                            <div className="text-center text-slate-600 py-24 bg-surface/30 border border-dashed border-slate-800 rounded-3xl">
                                <Activity className="w-10 h-10 mx-auto mb-3 opacity-20" />
                                <p className="text-sm font-medium">System Ready. New tasks will appear here.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}