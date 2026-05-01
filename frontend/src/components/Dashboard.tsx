import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Activity, CheckCircle2, Clock, AlertTriangle, Wifi, WifiOff, Zap, Cpu, RotateCcw, Trash2, Settings, Key, MessageSquare, ChevronDown, ChevronUp, BarChart3 } from 'lucide-react';
import { taskService } from '../services/taskService';
import type { Task, TaskCreatePayload, Job, AttachmentCreatePayload, Model } from '../services/taskService';
import { userService } from '../services/userService';
import { useWebSocket } from '../hooks/useWebSocket';
import { Layers, Link, File, Send, X } from 'lucide-react';

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

const WS_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/^http/, 'ws') + '/ws/events';

export default function Dashboard() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [jobs, setJobs] = useState<Job[]>([]);
    const [name, setName] = useState('');
    const [models, setModels] = useState<Model[]>([]);
    const [model, setModel] = useState('');
    const [inputText, setInputText] = useState('');
    const [priority, setPriority] = useState('low');
    const [attachments, setAttachments] = useState<AttachmentCreatePayload[]>([]);
    const [linkInput, setLinkInput] = useState('');

    // Bulk Mode States
    const [isBulkMode, setIsBulkMode] = useState(false);
    const [jobName, setJobName] = useState('');
    const [bulkTasks, setBulkTasks] = useState<TaskCreatePayload[]>([]);

    const [submitting, setSubmitting] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [openaiKey, setOpenaiKey] = useState('');
    const [anthropicKey, setAnthropicKey] = useState('');
    const [geminiKey, setGeminiKey] = useState('');
    const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);

    const { lastEvent, connected } = useWebSocket(WS_URL);

    const fetchTasks = async () => {
        try {
            const { data } = await taskService.getTasks();
            setTasks(data);
        } catch (err) {
            console.error(err);
        }
    };

    const fetchJobs = async () => {
        try {
            const { data } = await taskService.getJobs();
            setJobs(data);
        } catch (err) {
            console.error(err);
        }
    };

    const fetchModels = async () => {
        try {
            const { data } = await taskService.getModels();
            setModels(data);
            if (data.length > 0 && !model) {
                setModel(data[0].id);
            }
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
        fetchModels();
        fetchTasks();
        fetchJobs();
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
        } else {
            fetchTasks();
            fetchJobs();
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
        if (!confirm('Are you sure you want to delete this task?')) return;
        try {
            await taskService.deleteTask(taskId);
            setTasks(prev => prev.filter(t => t.id !== taskId));
        } catch (err) {
            console.error(err);
        }
    };

    const deleteJob = async (jobId: string) => {
        if (!confirm('Are you sure you want to delete this entire job campaign? All associated tasks will be lost.')) return;
        try {
            await taskService.deleteJob(jobId);
            setJobs(prev => prev.filter(j => j.id !== jobId));
            // Also refresh tasks as some might have been part of this job
            fetchTasks();
        } catch (err) {
            console.error(err);
        }
    };

    const handleRetryTask = async (taskId: string) => {
        try {
            await taskService.retryTask(taskId);
            fetchTasks();
        } catch (err) {
            console.error(err);
        }
    };

    const addAttachment = () => {
        if (!linkInput) return;
        setAttachments(prev => [...prev, { type: 'link', file_name: linkInput, file_url: linkInput }]);
        setLinkInput('');
    };

    const removeAttachment = (index: number) => {
        setAttachments(prev => prev.filter((_, i) => i !== index));
    };

    const removeBulkTask = (index: number) => {
        setBulkTasks(prev => prev.filter((_, i) => i !== index));
    };

    const addTaskToBulk = () => {
        if (!name || !model || !inputText) return;
        if (bulkTasks.length >= 20) return;

        const newTask: TaskCreatePayload = {
            name,
            model,
            input_text: inputText,
            priority,
            attachments: [...attachments],
        };

        setBulkTasks(prev => [...prev, newTask]);
        setName('');
        setInputText('');
        setAttachments([]);
    };

    const submitTask = async (e: React.FormEvent) => {
        e.preventDefault();
        if (submitting || !name || !model || !inputText) return;
        setSubmitting(true);

        try {
            const payload: TaskCreatePayload = {
                name,
                model,
                input_text: inputText,
                priority,
                attachments,
            };
            await taskService.createTask(payload);
            setName('');
            setInputText('');
            setPriority('low');
            setAttachments([]);
        } catch (err) {
            console.error(err);
        } finally {
            setSubmitting(false);
        }
    };

    const submitJob = async (e: React.FormEvent) => {
        e.preventDefault();
        if (submitting || !jobName || bulkTasks.length === 0) return;
        setSubmitting(true);

        try {
            await taskService.createJob({
                name: jobName,
                tasks: bulkTasks,
            });
            setJobName('');
            setName('');
            setInputText('');
            setAttachments([]);
            setBulkTasks([]);
            setIsBulkMode(false);
            fetchJobs();
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
    const selectedModel = models.find(m => m.id === model);
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
                <div className="md:col-span-1 space-y-4">
                    <div className="bg-surface border border-slate-800 p-6 rounded-3xl space-y-4 shadow-xl sticky top-6">
                        <div className="flex justify-between items-center bg-slate-900/50 p-1 rounded-xl border border-slate-800 mb-2">
                            <button
                                onClick={() => setIsBulkMode(false)}
                                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-bold transition-all ${!isBulkMode ? 'bg-slate-800 text-sky-400 shadow-inner' : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                <Zap className="w-3.5 h-3.5" /> Single
                            </button>
                            <button
                                onClick={() => setIsBulkMode(true)}
                                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-bold transition-all ${isBulkMode ? 'bg-slate-800 text-emerald-400 shadow-inner' : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                <Layers className="w-3.5 h-3.5" /> Job
                            </button>
                        </div>

                        <div className="flex justify-between items-center">
                            <h3 className="font-semibold text-slate-300">{isBulkMode ? 'Job Configuration' : 'Intelligent Dispatch'}</h3>
                            {!isBulkMode && (
                                <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-sky-500/10 border border-sky-500/20">
                                    <BarChart3 className="w-3.5 h-3.5 text-sky-400" />
                                    <span className="text-[10px] text-sky-400 font-bold uppercase">Scale: {predictedScale}x</span>
                                </div>
                            )}
                        </div>

                        {isBulkMode && (
                            <div className="space-y-4 p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1 text-emerald-500/80">Job Name</label>
                                    <input
                                        value={jobName}
                                        onChange={(e) => setJobName(e.target.value)}
                                        className="w-full bg-background border border-emerald-500/20 rounded-xl px-4 py-2.5 text-sm focus:ring-1 focus:ring-emerald-500 focus:outline-none"
                                        placeholder="e.g. Market Research Phase 1"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1 text-emerald-500/80">Job-Wide Intelligence Layer</label>
                                    <select
                                        value={model}
                                        onChange={(e) => setModel(e.target.value)}
                                        className="w-full bg-background border border-emerald-500/20 rounded-xl px-4 py-2.5 text-sm focus:ring-1 focus:ring-emerald-500 focus:outline-none appearance-none cursor-pointer"
                                    >
                                        {models.map(m => (
                                            <option key={m.id} value={m.id}>{m.name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        )}

                        <div className="space-y-4 pt-2">
                            <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold px-1">{isBulkMode ? 'Add Task to Job' : 'Task Details'}</div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Objective</label>
                                <input
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-1 focus:ring-accent focus:outline-none"
                                    placeholder="Task title..."
                                />
                            </div>

                            {!isBulkMode && (
                                <div className="space-y-1.5">
                                    <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Intelligence Layer</label>
                                    <select
                                        value={model}
                                        onChange={(e) => setModel(e.target.value)}
                                        className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-1 focus:ring-accent focus:outline-none appearance-none cursor-pointer"
                                    >
                                        {models.map(m => (
                                            <option key={m.id} value={m.id}>{m.name}</option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            <div className="space-y-1.5">
                                <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Prompt</label>
                                <textarea
                                    value={inputText}
                                    onChange={(e) => setInputText(e.target.value)}
                                    className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-1 focus:ring-accent focus:outline-none min-h-[100px] resize-none"
                                    placeholder="What should the AI do?"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Proactive Context</label>
                                <div className="flex gap-2">
                                    <div className="relative flex-1">
                                        <Link className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                                        <input
                                            value={linkInput}
                                            onChange={(e) => setLinkInput(e.target.value)}
                                            className="w-full bg-background border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-[11px] focus:ring-1 focus:ring-accent outline-none"
                                            placeholder="URL to read..."
                                            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addAttachment())}
                                        />
                                    </div>
                                    <button
                                        type="button"
                                        onClick={addAttachment}
                                        className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl border border-slate-700 transition-all"
                                    >
                                        <Plus className="w-4 h-4" />
                                    </button>
                                </div>
                                <AnimatePresence>
                                    {attachments.length > 0 && (
                                        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="flex flex-wrap gap-1.5 pt-1">
                                            {attachments.map((att, i) => (
                                                <div key={i} className="flex items-center gap-1.5 bg-sky-500/10 border border-sky-500/20 px-2 py-1 rounded-lg">
                                                    <span className="text-[9px] text-sky-300 max-w-[80px] truncate">{att.file_name}</span>
                                                    <button onClick={() => removeAttachment(i)} className="text-sky-500 hover:text-sky-300"><X className="w-2.5 h-2.5" /></button>
                                                </div>
                                            ))}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] text-slate-500 uppercase tracking-wider ml-1">Priority</label>
                                <select
                                    value={priority}
                                    onChange={(e) => setPriority(e.target.value)}
                                    className="w-full bg-background border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-1 focus:ring-accent focus:outline-none appearance-none cursor-pointer"
                                >
                                    <option value="low">Low Priority (Eco)</option>
                                    <option value="medium">Medium Priority</option>
                                    <option value="high">High Priority</option>
                                    <option value="critical">Critical (Turbo)</option>
                                </select>
                            </div>

                            {!isBulkMode ? (
                                <button
                                    onClick={submitTask}
                                    disabled={submitting}
                                    className="w-full bg-accent text-slate-900 font-bold py-4 rounded-xl flex items-center justify-center gap-2 hover:bg-sky-400 transition-all active:scale-95 disabled:opacity-50 shadow-lg shadow-sky-500/10 mt-2"
                                >
                                    <Send className="w-4 h-4" />
                                    {submitting ? 'Dispatching...' : 'Execute Task'}
                                </button>
                            ) : (
                                <div className="space-y-4 pt-2">
                                    <button
                                        type="button"
                                        onClick={addTaskToBulk}
                                        disabled={bulkTasks.length >= 20 || !name || !inputText}
                                        className="w-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold py-4 rounded-xl flex items-center justify-center gap-2 hover:bg-emerald-500/20 transition-all active:scale-95 disabled:opacity-50"
                                    >
                                        <Plus className="w-4 h-4" />
                                        Stage Task ({bulkTasks.length}/20)
                                    </button>

                                    {bulkTasks.length > 0 && (
                                        <div className="space-y-3">
                                            <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold px-1 flex justify-between">
                                                <span>Draft Tasks</span>
                                                <span className="text-emerald-500">{bulkTasks.length} staged</span>
                                            </div>
                                            <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1 custom-scrollbar">
                                                {bulkTasks.map((t, i) => (
                                                    <div key={i} className="bg-slate-900/50 border border-slate-800 rounded-xl p-3 flex justify-between items-center group">
                                                        <div className="min-w-0">
                                                            <div className="text-xs font-semibold text-slate-300 truncate">{t.name}</div>
                                                            <div className="text-[9px] text-slate-500 truncate mt-1">{t.input_text}</div>
                                                        </div>
                                                        <button
                                                            onClick={() => removeBulkTask(i)}
                                                            className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                                                        >
                                                            <X className="w-3.5 h-3.5" />
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>

                                            <button
                                                onClick={submitJob}
                                                disabled={submitting || !jobName}
                                                className="w-full bg-emerald-500 text-slate-900 font-bold py-4 rounded-xl flex items-center justify-center gap-2 hover:bg-emerald-400 transition-all active:scale-95 shadow-lg shadow-emerald-500/10"
                                            >
                                                <Layers className="w-4 h-4" />
                                                {submitting ? 'Launching...' : `Launch Job Campaign`}
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="md:col-span-2 space-y-8">
                    {jobs.length > 0 && (
                        <div className="space-y-4">
                            <h3 className="font-semibold text-slate-300 flex items-center gap-2">
                                <Layers className="w-4 h-4 text-emerald-500" /> Active Jobs
                            </h3>
                            <div className="grid sm:grid-cols-2 gap-3">
                                {jobs.map(job => {
                                    const completed = job.tasks.filter(t => t.status === 'completed').length;
                                    const progress = (completed / job.tasks.length) * 100;
                                    return (
                                        <div key={job.id} className="bg-surface border border-slate-800 rounded-2xl p-4 space-y-3">
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-sm font-bold text-slate-200 truncate">{job.name}</div>
                                                    <div className="text-[10px] text-slate-500 font-mono italic mt-0.5">{completed}/{job.tasks.length} tasks completed</div>
                                                </div>
                                                <button
                                                    onClick={() => deleteJob(job.id)}
                                                    className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all ml-2"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                            <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                                                <motion.div
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${progress}%` }}
                                                    className="h-full bg-emerald-500"
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    <div className="space-y-4">
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
                                                            {task.attachments && task.attachments.length > 0 && (
                                                                <span className="text-[10px] text-sky-400 font-mono flex items-center gap-1 bg-sky-500/5 px-1.5 py-0.5 rounded-md border border-sky-500/10">
                                                                    <Link className="w-2.5 h-2.5" /> {task.attachments.length}
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
                                                        initial={{ opacity: 0, height: 0 }}
                                                        animate={{ opacity: 1, height: 'auto' }}
                                                        exit={{ opacity: 0, height: 0 }}
                                                        className="overflow-hidden bg-background/40 border-t border-slate-800/50"
                                                    >
                                                        <div className="p-4 space-y-4">
                                                            {task.attachments && task.attachments.length > 0 && (
                                                                <div className="space-y-2">
                                                                    <div className="text-[10px] text-slate-600 uppercase tracking-widest font-bold">Context Sources</div>
                                                                    <div className="flex flex-wrap gap-2">
                                                                        {task.attachments.map(att => (
                                                                            <a
                                                                                key={att.id}
                                                                                href={att.file_url}
                                                                                target="_blank"
                                                                                rel="noreferrer"
                                                                                className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl text-[11px] text-sky-400 hover:border-sky-500/30 transition-all"
                                                                            >
                                                                                {att.type === 'link' ? <Link className="w-3 h-3" /> : <File className="w-3 h-3" />}
                                                                                {att.file_name}
                                                                            </a>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            )}

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
        </div>
    );
}