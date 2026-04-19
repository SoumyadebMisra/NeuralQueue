import api from './api';

export interface Task {
    id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    payload: any;
    created_at: string;
}

export const taskService = {
    getTasks: () => api.get<Task[]>('/api/v1/tasks/'),
    createTask: (payload: any) => api.post('/api/v1/tasks/', payload),
};