<!--
  QueuePanel.svelte - Central queue display and controls
-->
<script lang="ts">
    import { api, type JobListItem } from "$lib/api";
    import { queue, systemStatus, isQueueRunning, addLog } from "$lib/stores";
    import StatusBadge from "./StatusBadge.svelte";

    export let jobs: JobListItem[] = [];

    let isStarting = false;
    let isStopping = false;

    async function startQueue() {
        isStarting = true;
        try {
            await api.startQueue();
            addLog({
                timestamp: new Date().toISOString(),
                level: "info",
                message: "🚀 Queue started",
            });
        } catch (e: any) {
            addLog({
                timestamp: new Date().toISOString(),
                level: "error",
                message: `Failed to start: ${e.message}`,
            });
        } finally {
            isStarting = false;
        }
    }

    async function stopQueue() {
        isStopping = true;
        try {
            await api.stopQueue();
            addLog({
                timestamp: new Date().toISOString(),
                level: "warning",
                message: "⏹ Queue stopped",
            });
        } catch (e: any) {
            addLog({
                timestamp: new Date().toISOString(),
                level: "error",
                message: `Failed to stop: ${e.message}`,
            });
        } finally {
            isStopping = false;
        }
    }

    async function deleteJob(id: number) {
        try {
            await api.deleteJob(id);
            const updated = await api.getQueue();
            queue.set(updated);
        } catch (e: any) {
            console.error("Delete failed:", e);
        }
    }

    function formatDate(dateStr: string): string {
        return new Date(dateStr).toLocaleTimeString("pl-PL", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    }

    $: pendingJobs = jobs.filter(
        (j) => j.status === "pending" || j.status === "queued",
    );
    $: runningJob = jobs.find((j) => j.status === "running");
    $: completedJobs = jobs.filter(
        (j) => j.status === "completed" || j.status === "failed",
    );
</script>

<div class="queue-panel">
    <div class="panel-header">
        <div class="header-left">
            <h2>Active Queue</h2>
            <span class="job-count"
                >{jobs.length} job{jobs.length !== 1 ? "s" : ""}</span
            >
        </div>
        <div class="header-actions">
            {#if $isQueueRunning}
                <button
                    class="btn-danger"
                    on:click={stopQueue}
                    disabled={isStopping}
                >
                    {isStopping ? "⏳" : "⏹"} Stop
                </button>
            {:else}
                <button
                    class="btn-primary"
                    on:click={startQueue}
                    disabled={isStarting || pendingJobs.length === 0}
                >
                    {isStarting ? "⏳" : "▶"} Start Sequence
                </button>
            {/if}
        </div>
    </div>

    <div class="queue-content">
        {#if jobs.length === 0}
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>No jobs in queue</p>
                <p class="text-muted text-sm">
                    Add a simulation to get started
                </p>
            </div>
        {:else}
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Energy</th>
                        <th>Particles</th>
                        <th>Thickness</th>
                        <th>Cycles</th>
                        <th>Status</th>
                        <th>Progress</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {#each jobs as job (job.id)}
                        <tr class:running={job.status === "running"}>
                            <td class="font-mono">#{job.id}</td>
                            <td>{job.energy}</td>
                            <td class="font-mono"
                                >{job.particles.toLocaleString()}</td
                            >
                            <td>{job.thickness}</td>
                            <td class="font-mono"
                                >{job.current_cycle}/{job.cycles}</td
                            >
                            <td>
                                <StatusBadge status={job.status} />
                            </td>
                            <td>
                                <div class="progress-cell">
                                    <div class="progress-bar">
                                        <div
                                            class="progress-bar-fill"
                                            style="width: {job.progress}%"
                                        ></div>
                                    </div>
                                    <span class="progress-text"
                                        >{job.progress}%</span
                                    >
                                </div>
                            </td>
                            <td>
                                {#if job.status === "pending"}
                                    <button
                                        class="btn-icon btn-danger"
                                        on:click={() => deleteJob(job.id)}
                                        title="Remove from queue"
                                    >
                                        ✕
                                    </button>
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
    .queue-panel {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        display: flex;
        flex-direction: column;
        min-height: 400px;
    }

    .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.25rem 1.5rem;
        border-bottom: 1px solid var(--border-color);
    }

    .header-left {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .header-left h2 {
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

    .header-actions {
        display: flex;
        gap: 0.75rem;
    }

    .queue-content {
        flex: 1;
        overflow: auto;
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

    .empty-state p {
        margin: 0;
    }

    table {
        width: 100%;
    }

    tr.running {
        background: rgba(59, 130, 246, 0.05);
    }

    tr.running td {
        border-bottom-color: rgba(59, 130, 246, 0.2);
    }

    .progress-cell {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        min-width: 120px;
    }

    .progress-cell .progress-bar {
        flex: 1;
    }

    .progress-text {
        font-size: 0.8rem;
        font-family: var(--font-mono);
        color: var(--text-secondary);
        width: 40px;
        text-align: right;
    }
</style>
