<!--
  StatusBadge.svelte - Status indicator badge
-->
<script lang="ts">
    export let status: string;

    const statusConfig: Record<string, { label: string; icon: string }> = {
        pending: { label: "Pending", icon: "⏳" },
        queued: { label: "Queued", icon: "📋" },
        running: { label: "Running", icon: "⚡" },
        completed: { label: "Completed", icon: "✓" },
        failed: { label: "Failed", icon: "✕" },
        cancelled: { label: "Cancelled", icon: "⊘" },
    };

    $: config = statusConfig[status] || { label: status, icon: "?" };
</script>

<span class="status-badge status-{status}">
    <span class="status-icon" class:animate-pulse={status === "running"}>
        {config.icon}
    </span>
    {config.label}
</span>

<style>
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.3rem 0.65rem;
        border-radius: 100px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }

    .status-icon {
        font-size: 0.7rem;
    }

    .status-pending,
    .status-queued {
        background: rgba(107, 114, 128, 0.15);
        color: #9ca3af;
    }

    .status-running {
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
    }

    .status-completed {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
    }

    .status-failed,
    .status-cancelled {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
    }
</style>
