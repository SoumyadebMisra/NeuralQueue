import api from './api';

export interface Task {
    id: string;
    name: string;
    model: string;
    task_type: string;
    priority: 'critical' | 'high' | 'medium' | 'low';
    gpu_budget: number;
    status: 'queued' | 'scoring' | 'processing' | 'completed' | 'failed';
    retries: number;
    created_at: string;
    updated_at: string | null;
    started_at: string | null;
    completed_at: string | null;
    latency_ms: number | null;
    user_id: string;
    input_text: string | null;
    output_text: string | null;
}

export interface TaskCreatePayload {
    name: string;
    model: string;
    input_text?: string;
    task_type?: string;
    priority?: string;
}

export const taskService = {
    getTasks: () => api.get<Task[]>('/api/v1/tasks/'),
    createTask: (payload: TaskCreatePayload) => api.post<Task>('/api/v1/tasks/', payload),
    getTask: (id: string) => api.get<Task>(`/api/v1/tasks/${id}`),
    deleteTask: (id: string) => api.delete(`/api/v1/tasks/${id}`),
    retryTask: (id: string) => api.post<Task>(`/api/v1/tasks/${id}/retry`),
};