/**
 * API client for Geant4 Simulation Dashboard
 */

// Dynamic configuration based on environment
// For single-host (production), we use relative paths which SvelteKit proxies
// For development, we might still want localhost
import { browser } from '$app/environment';

const API_BASE = '/api';

function getWebSocketUrl() {
    if (!browser) return '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/ws`;
}

export interface Job {
    id: number;
    name: string | null;
    particles: number;
    energy: string;
    thickness: string;
    cycles: number;
    generate_svg: boolean;
    status: string;
    progress: number;
    current_cycle: number;
    result_folder: string | null;
    csv_files: string[] | null;
    svg_files: string[] | null;
    total_hits: number;
    error_message: string | null;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    submitted_by: string | null;
}

export interface JobListItem {
    id: number;
    name: string | null;
    particles: number;
    energy: string;
    thickness: string;
    cycles: number;
    status: string;
    progress: number;
    current_cycle: number;
    created_at: string;
}

export interface SystemStatus {
    status: string;
    is_running: boolean;
    current_job_id: number | null;
    queue_length: number;
    total_jobs: number;
    storage_used_bytes: number;
    storage_limit_bytes: number;
}

export interface JobCreate {
    name?: string;
    particles: number;
    energy: string;
    thickness: string;
    cycles: number;
    generate_svg: boolean;
}

class ApiClient {
    private baseUrl: string;
    private wsUrl: string;

    constructor(baseUrl: string = API_BASE) {
        this.baseUrl = API_BASE;
        this.wsUrl = getWebSocketUrl();
    }

    private async fetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Authentication
    async authenticate(pin: string): Promise<{ success: boolean; message: string }> {
        return this.fetch('/auth', {
            method: 'POST',
            body: JSON.stringify({ pin }),
        });
    }

    // Jobs
    async createJob(job: JobCreate): Promise<Job> {
        return this.fetch('/jobs', {
            method: 'POST',
            body: JSON.stringify(job),
        });
    }

    async getJobs(status?: string): Promise<JobListItem[]> {
        const params = status ? `?status=${status}` : '';
        return this.fetch(`/jobs${params}`);
    }

    async getQueue(): Promise<JobListItem[]> {
        return this.fetch('/jobs/queue');
    }

    async getJob(id: number): Promise<Job> {
        return this.fetch(`/jobs/${id}`);
    }

    async deleteJob(id: number): Promise<void> {
        return this.fetch(`/jobs/${id}`, { method: 'DELETE' });
    }

    // Queue control
    async startQueue(): Promise<{ success: boolean; message: string }> {
        return this.fetch('/queue/start', { method: 'POST' });
    }

    async stopQueue(): Promise<{ success: boolean; message: string }> {
        return this.fetch('/queue/stop', { method: 'POST' });
    }

    // Status
    async getStatus(): Promise<SystemStatus> {
        return this.fetch('/status');
    }

    // History
    async getHistory(limit: number = 100): Promise<JobListItem[]> {
        return this.fetch(`/history?limit=${limit}`);
    }

    // Results
    async getCsvPreview(jobId: number, filename: string): Promise<{ header: string[]; rows: string[][] }> {
        return this.fetch(`/jobs/${jobId}/results/csv/${filename}/preview`);
    }

    async getSvgContent(jobId: number, filename: string): Promise<{ svg: string }> {
        return this.fetch(`/jobs/${jobId}/results/svg/${filename}/view`);
    }

    getCsvDownloadUrl(jobId: number, filename: string): string {
        return `${this.baseUrl}/jobs/${jobId}/results/csv/${filename}`;
    }

    getSvgDownloadUrl(jobId: number, filename: string): string {
        return `${this.baseUrl}/jobs/${jobId}/results/svg/${filename}`;
    }
}

export const api = new ApiClient();

// WebSocket connection
export function createWebSocket(
    onMessage: (data: any) => void,
    onOpen?: () => void,
    onClose?: () => void
): WebSocket {
    const ws = new WebSocket(getWebSocketUrl());

    ws.onopen = () => {
        console.log('WebSocket connected');
        onOpen?.();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            onMessage(data);
        } catch (e) {
            console.error('WebSocket parse error:', e);
        }
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        onClose?.();
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    return ws;
}
