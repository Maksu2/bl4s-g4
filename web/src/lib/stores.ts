/**
 * Svelte stores for application state
 */

import { writable, derived, type Writable } from 'svelte/store';
import type { JobListItem, SystemStatus, Job } from './api';

// Authentication state
export const isAuthenticated: Writable<boolean> = writable(false);

// System status
export const systemStatus: Writable<SystemStatus | null> = writable(null);

// Current queue
export const queue: Writable<JobListItem[]> = writable([]);

// Job history
export const history: Writable<JobListItem[]> = writable([]);

// Currently selected job for details
export const selectedJob: Writable<Job | null> = writable(null);

// Log entries
export interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
    job_id?: number;
}

export const logs: Writable<LogEntry[]> = writable([]);

// Add a log entry
export function addLog(entry: LogEntry) {
    logs.update(current => {
        const updated = [entry, ...current];
        // Keep only last 100 entries
        return updated.slice(0, 100);
    });
}

// WebSocket connection state
export const wsConnected: Writable<boolean> = writable(false);

// Derived stores
export const isQueueRunning = derived(
    systemStatus,
    ($status) => $status?.is_running ?? false
);

export const queueLength = derived(
    queue,
    ($queue) => $queue.filter(j => j.status === 'pending' || j.status === 'queued').length
);

// UI state
export const activeTab: Writable<'queue' | 'history' | 'results'> = writable('queue');
export const showResultsModal: Writable<boolean> = writable(false);
