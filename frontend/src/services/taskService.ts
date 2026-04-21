import api from './api';

export interface Attachment {
    id: string;
    type: 'link' | 'file' | 'photo';
    file_name: string;
    file_url: string;
    extracted_text?: string;
    file_size?: number;
    content_type?: string;
}

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
    attachments?: Attachment[];
}

export interface AttachmentCreatePayload {
    type: 'link' | 'file' | 'photo';
    file_name: string;
    file_url: string;
}

export interface TaskCreatePayload {
    name: string;
    model: string;
    input_text?: string;
    task_type?: string;
    priority?: string;
    attachments?: AttachmentCreatePayload[];
}

export interface Job {
    id: string;
    name: string;
    status: string;
    capacity_limit: number;
    tasks: Task[];
    created_at: string;
    updated_at: string;
}

export interface JobCreatePayload {
    name: string;
    tasks: TaskCreatePayload[];
    capacity_limit?: number;
}

export const taskService = {
    getTasks: () => api.get<Task[]>('/api/v1/tasks/'),
    createTask: (payload: TaskCreatePayload) => api.post<Task>('/api/v1/tasks/', payload),
    getTask: (id: string) => api.get<Task>(`/api/v1/tasks/${id}`),
    deleteTask: (id: string) => api.delete(`/api/v1/tasks/${id}`),
    retryTask: (id: string) => api.post<Task>(`/api/v1/tasks/${id}/retry`),
    
    getJobs: () => api.get<Job[]>('/api/v1/tasks/jobs'),
    getJob: (id: string) => api.get<Job>(`/api/v1/tasks/jobs/${id}`),
    createJob: (payload: JobCreatePayload) => api.post<Job>('/api/v1/tasks/jobs', payload),
};