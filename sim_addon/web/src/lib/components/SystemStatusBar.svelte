<!--
  SystemStatusBar.svelte - Global system status indicator
-->
<script lang="ts">
    import { systemStatus, wsConnected } from "$lib/stores";

    $: status = $systemStatus;
    $: statusText = status?.is_running
        ? "SIMULATION IN PROGRESS"
        : status?.queue_length
          ? "READY"
          : "IDLE";
    $: statusClass = status?.is_running
        ? "running"
        : status?.queue_length
          ? "ready"
          : "idle";

    function formatStorage(bytes: number): string {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        if (bytes < 1024 * 1024 * 1024)
            return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
</script>

<div class="status-bar">
    <div class="status-main">
        <div class="status-indicator {statusClass}">
            <span class="status-dot" class:animate-pulse={status?.is_running}
            ></span>
            {statusText}
        </div>

        {#if status?.is_running && status?.current_job_id}
            <span class="current-job">Job #{status.current_job_id}</span>
        {/if}
    </div>

    <div class="status-info">
        <div class="info-item" class:connected={$wsConnected}>
            <span class="info-dot"></span>
            {$wsConnected ? "Live" : "Offline"}
        </div>

        {#if status}
            <div class="info-item">
                <span class="info-icon">📊</span>
                {status.total_jobs} runs
            </div>
            <div class="info-item">
                <span class="info-icon">💾</span>
                {formatStorage(status.storage_used_bytes)} / 2 GB
            </div>
        {/if}
    </div>
</div>

<style>
    .status-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 1rem;
        background: var(--bg-card);
        border-bottom: 1px solid var(--border-color);
    }

    .status-main {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .status-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0.85rem;
        border-radius: 100px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }

    .status-indicator.idle {
        background: rgba(107, 114, 128, 0.15);
        color: #9ca3af;
    }

    .status-indicator.idle .status-dot {
        background: #9ca3af;
    }

    .status-indicator.ready {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
    }

    .status-indicator.ready .status-dot {
        background: #4ade80;
    }

    .status-indicator.running {
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
    }

    .status-indicator.running .status-dot {
        background: #60a5fa;
    }

    .current-job {
        font-size: 0.8rem;
        color: var(--text-secondary);
        font-family: var(--font-mono);
    }

    .status-info {
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }

    .info-item {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.8rem;
        color: var(--text-muted);
    }

    .info-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--status-error);
    }

    .info-item.connected .info-dot {
        background: var(--status-success);
    }

    .info-icon {
        font-size: 0.9rem;
    }
</style>
