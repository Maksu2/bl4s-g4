<!--
  HistoryPanel.svelte - Completed simulations history
-->
<script lang="ts">
    import { api, type JobListItem, type Job } from "$lib/api";
    import { history, selectedJob, showResultsModal } from "$lib/stores";
    import StatusBadge from "./StatusBadge.svelte";

    export let jobs: JobListItem[] = [];

    async function viewResults(jobId: number) {
        try {
            const job = await api.getJob(jobId);
            selectedJob.set(job);
            showResultsModal.set(true);
        } catch (e) {
            console.error("Failed to load job:", e);
        }
    }

    function formatDate(dateStr: string): string {
        return new Date(dateStr).toLocaleString("pl-PL", {
            day: "2-digit",
            month: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }
</script>

<div class="history-panel">
    <div class="panel-header">
        <h2>Simulation History</h2>
        <span class="job-count">{jobs.length} runs</span>
    </div>

    <div class="history-content">
        {#if jobs.length === 0}
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <p>No completed simulations yet</p>
            </div>
        {:else}
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Date</th>
                        <th>Parameters</th>
                        <th>Cycles</th>
                        <th>Status</th>
                        <th>Results</th>
                    </tr>
                </thead>
                <tbody>
                    {#each jobs as job (job.id)}
                        <tr>
                            <td class="font-mono">#{job.id}</td>
                            <td class="text-muted"
                                >{formatDate(job.created_at)}</td
                            >
                            <td>
                                <span class="param">{job.energy}</span>
                                <span class="param-sep">•</span>
                                <span class="param"
                                    >{job.particles.toLocaleString()} particles</span
                                >
                                <span class="param-sep">•</span>
                                <span class="param">{job.thickness}</span>
                            </td>
                            <td class="font-mono">{job.cycles}</td>
                            <td>
                                <StatusBadge status={job.status} />
                            </td>
                            <td>
                                {#if job.status === "completed"}
                                    <button
                                        class="btn-secondary btn-sm"
                                        on:click={() => viewResults(job.id)}
                                    >
                                        View Results
                                    </button>
                                {:else}
                                    <span class="text-muted">—</span>
                                {/if}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        {/if}
    </div>
</div>

<style>
    .history-panel {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        display: flex;
        flex-direction: column;
    }

    .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.25rem 1.5rem;
        border-bottom: 1px solid var(--border-color);
    }

    .panel-header h2 {
        font-size: 1.1rem;
        margin: 0;
    }

    .job-count {
        background: var(--bg-input);
        padding: 0.25rem 0.75rem;
        border-radius: 100px;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    .history-content {
        overflow: auto;
        max-height: 500px;
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        text-align: center;
    }

    .empty-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }

    .param {
        color: var(--text-primary);
    }

    .param-sep {
        color: var(--text-muted);
        margin: 0 0.35rem;
    }

    .btn-sm {
        padding: 0.4rem 0.8rem;
        font-size: 0.8rem;
    }
</style>
