<!--
  LogPanel.svelte - Event log display
-->
<script lang="ts">
    import { logs, type LogEntry } from "$lib/stores";

    function formatTime(timestamp: string): string {
        return new Date(timestamp).toLocaleTimeString("pl-PL", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    }

    function getLevelClass(level: string): string {
        switch (level) {
            case "error":
                return "log-error";
            case "warning":
                return "log-warning";
            case "success":
                return "log-success";
            default:
                return "log-info";
        }
    }
</script>

<div class="log-panel">
    <div class="log-header">
        <span class="log-title">Event Log</span>
        <span class="log-count">{$logs.length} entries</span>
    </div>
    <div class="log-content">
        {#if $logs.length === 0}
            <div class="log-empty">&gt;&gt; Awaiting command sequence...</div>
        {:else}
            {#each $logs as entry (entry.timestamp + entry.message)}
                <div class="log-entry {getLevelClass(entry.level)}">
                    <span class="log-time">{formatTime(entry.timestamp)}</span>
                    <span class="log-message">{entry.message}</span>
                </div>
            {/each}
        {/if}
    </div>
</div>

<style>
    .log-panel {
        background: var(--bg-input);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        overflow: hidden;
    }

    .log-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid var(--border-color);
        background: var(--bg-card);
    }

    .log-title {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
    }

    .log-count {
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    .log-content {
        height: 160px;
        overflow-y: auto;
        padding: 0.75rem 1rem;
        font-family: var(--font-mono);
        font-size: 0.8rem;
    }

    .log-empty {
        color: var(--text-muted);
        font-style: italic;
    }

    .log-entry {
        display: flex;
        gap: 0.75rem;
        padding: 0.35rem 0;
        line-height: 1.4;
    }

    .log-time {
        color: var(--text-muted);
        flex-shrink: 0;
    }

    .log-message {
        word-break: break-word;
    }

    .log-info .log-message {
        color: var(--text-secondary);
    }

    .log-success .log-message {
        color: var(--status-success);
    }

    .log-warning .log-message {
        color: var(--status-warning);
    }

    .log-error .log-message {
        color: var(--status-error);
    }
</style>
