<!--
  +page.svelte - Main dashboard page
-->
<script lang="ts">
    import { queue, history, activeTab } from "$lib/stores";
    import SystemStatusBar from "$lib/components/SystemStatusBar.svelte";
    import ConfigPanel from "$lib/components/ConfigPanel.svelte";
    import QueuePanel from "$lib/components/QueuePanel.svelte";
    import HistoryPanel from "$lib/components/HistoryPanel.svelte";
    import LogPanel from "$lib/components/LogPanel.svelte";
    import ResultsModal from "$lib/components/ResultsModal.svelte";
</script>

<svelte:head>
    <title>Geant4 Simulation Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link
        rel="preconnect"
        href="https://fonts.gstatic.com"
        crossorigin="anonymous"
    />
    <link
        href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
        rel="stylesheet"
    />
</svelte:head>

<div class="app">
    <SystemStatusBar />

    <header class="header">
        <div class="header-title">
            <h1 class="text-gradient">GEANT4 SIMULATION DASHBOARD</h1>
            <p class="subtitle">
                Electromagnetic Cascade Control Center • Team Workspace
            </p>
        </div>

        <nav class="tabs">
            <button
                class="tab"
                class:active={$activeTab === "queue"}
                on:click={() => activeTab.set("queue")}
            >
                Queue
            </button>
            <button
                class="tab"
                class:active={$activeTab === "history"}
                on:click={() => activeTab.set("history")}
            >
                History
            </button>
        </nav>
    </header>

    <main class="main">
        <aside class="sidebar">
            <ConfigPanel />
        </aside>

        <section class="content">
            {#if $activeTab === "queue"}
                <QueuePanel jobs={$queue} />
            {:else if $activeTab === "history"}
                <HistoryPanel jobs={$history} />
            {/if}
        </section>
    </main>

    <footer class="footer">
        <LogPanel />
    </footer>

    <ResultsModal />
</div>

<style>
    .app {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        background: var(--bg-primary);
    }

    .header {
        padding: 1.5rem 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--border-color);
    }

    .header-title h1 {
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: 0.02em;
        margin: 0;
    }

    .subtitle {
        font-size: 0.85rem;
        color: var(--text-muted);
        margin: 0.25rem 0 0 0;
    }

    .tabs {
        display: flex;
        gap: 0.5rem;
        background: var(--bg-card);
        padding: 0.25rem;
        border-radius: var(--radius-md);
    }

    .tab {
        padding: 0.5rem 1.25rem;
        background: transparent;
        border: none;
        color: var(--text-secondary);
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        border-radius: var(--radius-sm);
        transition: all 0.2s ease;
    }

    .tab:hover {
        color: var(--text-primary);
    }

    .tab.active {
        background: var(--accent-primary);
        color: white;
    }

    .main {
        flex: 1;
        display: flex;
        gap: 1.5rem;
        padding: 1.5rem 2rem;
        overflow: hidden;
    }

    .sidebar {
        width: 340px;
        flex-shrink: 0;
    }

    .content {
        flex: 1;
        min-width: 0;
    }

    .footer {
        padding: 0 2rem 1.5rem 2rem;
    }

    /* Responsive */
    @media (max-width: 1024px) {
        .main {
            flex-direction: column;
        }

        .sidebar {
            width: 100%;
        }
    }
</style>
