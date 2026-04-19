import api from './api';

export interface User {
    id: string;
    username: string;
    email: string;
    openai_api_key?: string;
    anthropic_api_key?: string;
    gemini_api_key?: string;
}

export interface UserUpdatePayload {
    openai_api_key?: string;
    anthropic_api_key?: string;
    gemini_api_key?: string;
}

export const userService = {
    getMe: () => api.get<User>('/api/v1/users/me'),
    updateMe: (payload: UserUpdatePayload) => api.patch<User>('/api/v1/users/me', payload),
};
