<!--
  ResultsModal.svelte - Modal for viewing simulation results
-->
<script lang="ts">
    import { api, type Job } from "$lib/api";
    import { selectedJob, showResultsModal } from "$lib/stores";

    let activeTab: "csv" | "svg" = "svg";
    let selectedFile: string | null = null;
    let csvData: { header: string[]; rows: string[][] } | null = null;
    let svgContent: string | null = null;
    let isLoading = false;

    $: job = $selectedJob;
    $: if (job && job.svg_files && job.svg_files.length > 0 && !selectedFile) {
        selectedFile = job.svg_files[0];
        loadSvg(job.id, selectedFile);
    }

    async function loadCsv(jobId: number, filename: string) {
        isLoading = true;
        selectedFile = filename;
        activeTab = "csv";
        svgContent = null;
        try {
            csvData = await api.getCsvPreview(jobId, filename);
        } catch (e) {
            console.error("Failed to load CSV:", e);
        } finally {
            isLoading = false;
        }
    }

    async function loadSvg(jobId: number, filename: string) {
        isLoading = true;
        selectedFile = filename;
        activeTab = "svg";
        csvData = null;
        try {
            const result = await api.getSvgContent(jobId, filename);
            svgContent = result.svg;
        } catch (e) {
            console.error("Failed to load SVG:", e);
        } finally {
            isLoading = false;
        }
    }

    function close() {
        showResultsModal.set(false);
        selectedJob.set(null);
        selectedFile = null;
        csvData = null;
        svgContent = null;
    }

    function downloadFile(type: "csv" | "svg", filename: string) {
        if (!job) return;
        const url =
            type === "csv"
                ? api.getCsvDownloadUrl(job.id, filename)
                : api.getSvgDownloadUrl(job.id, filename);
        window.open(url, "_blank");
    }
</script>

{#if $showResultsModal && job}
    <div class="modal-overlay" on:click={close}>
        <div class="modal" on:click|stopPropagation>
            <div class="modal-header">
                <div>
                    <h2>Results: Job #{job.id}</h2>
                    <p class="text-muted text-sm">
                        {job.energy} • {job.particles.toLocaleString()} particles
                        • {job.thickness}
                    </p>
                </div>
                <button class="btn-icon" on:click={close}>✕</button>
            </div>

            <div class="modal-body">
                <div class="sidebar">
                    <div class="file-section">
                        <h3>SVG Visualizations</h3>
                        {#if job.svg_files && job.svg_files.length > 0}
                            {#each job.svg_files as file}
                                <button
                                    class="file-item"
                                    class:active={selectedFile === file &&
                                        activeTab === "svg"}
                                    on:click={() => loadSvg(job.id, file)}
                                >
                                    <span class="file-icon">📊</span>
                                    <span class="file-name">{file}</span>
                                </button>
                            {/each}
                        {:else}
                            <p class="text-muted text-sm">No SVG files</p>
                        {/if}
                    </div>

                    <div class="file-section">
                        <h3>CSV Data</h3>
                        {#if job.csv_files && job.csv_files.length > 0}
                            {#each job.csv_files as file}
                                <button
                                    class="file-item"
                                    class:active={selectedFile === file &&
                                        activeTab === "csv"}
                                    on:click={() => loadCsv(job.id, file)}
                                >
                                    <span class="file-icon">📄</span>
                                    <span class="file-name">{file}</span>
                                </button>
                            {/each}
                        {:else}
                            <p class="text-muted text-sm">No CSV files</p>
                        {/if}
                    </div>

                    <div class="stats">
                        <div class="stat">
                            <span class="stat-value"
                                >{job.total_hits.toLocaleString()}</span
                            >
                            <span class="stat-label">Total Hits</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">{job.cycles}</span>
                            <span class="stat-label">Cycles</span>
                        </div>
                    </div>
                </div>

                <div class="content">
                    {#if isLoading}
                        <div class="loading">
                            <span class="animate-spin">⟳</span>
                            Loading...
                        </div>
                    {:else if activeTab === "svg" && svgContent}
                        <div class="svg-viewer">
                            {@html svgContent}
                        </div>
                        {#if selectedFile}
                            <div class="download-bar">
                                <button
                                    class="btn-secondary"
                                    on:click={() =>
                                        downloadFile("svg", selectedFile || "")}
                                >
                                    ⬇ Download SVG
                                </button>
                            </div>
                        {/if}
                    {:else if activeTab === "csv" && csvData}
                        <div class="csv-viewer">
                            <table>
                                <thead>
                                    <tr>
                                        {#each csvData.header as col}
                                            <th>{col}</th>
                                        {/each}
                                    </tr>
                                </thead>
                                <tbody>
                                    {#each csvData.rows as row}
                                        <tr>
                                            {#each row as cell}
                                                <td>{cell}</td>
                                            {/each}
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                        {#if selectedFile}
                            <div class="download-bar">
                                <button
                                    class="btn-secondary"
                                    on:click={() =>
                                        downloadFile("csv", selectedFile || "")}
                                >
                                    ⬇ Download CSV
                                </button>
                            </div>
                        {/if}
                    {:else}
                        <div class="empty-content">
                            <p class="text-muted">Select a file to view</p>
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(4px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        padding: 2rem;
    }

    .modal {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-xl);
        width: 100%;
        max-width: 1100px;
        max-height: 85vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.25rem 1.5rem;
        border-bottom: 1px solid var(--border-color);
    }

    .modal-header h2 {
        margin: 0;
        font-size: 1.2rem;
    }

    .modal-body {
        display: flex;
        flex: 1;
        overflow: hidden;
    }

    .sidebar {
        width: 260px;
        border-right: 1px solid var(--border-color);
        padding: 1rem;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .file-section h3 {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 0.5rem;
    }

    .file-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        width: 100%;
        padding: 0.5rem 0.75rem;
        background: transparent;
        border: 1px solid transparent;
        border-radius: var(--radius-sm);
        color: var(--text-secondary);
        cursor: pointer;
        text-align: left;
        font-size: 0.85rem;
    }

    .file-item:hover {
        background: var(--bg-card);
    }

    .file-item.active {
        background: rgba(59, 130, 246, 0.1);
        border-color: rgba(59, 130, 246, 0.3);
        color: var(--accent-primary);
    }

    .file-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .stats {
        margin-top: auto;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.75rem;
    }

    .stat {
        background: var(--bg-card);
        padding: 0.75rem;
        border-radius: var(--radius-md);
        text-align: center;
    }

    .stat-value {
        display: block;
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-accent);
        font-family: var(--font-mono);
    }

    .stat-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .content {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    .loading,
    .empty-content {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        font-size: 1rem;
        color: var(--text-muted);
    }

    .svg-viewer {
        flex: 1;
        overflow: auto;
        padding: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #fff;
    }

    .svg-viewer :global(svg) {
        max-width: 100%;
        max-height: 100%;
    }

    .csv-viewer {
        flex: 1;
        overflow: auto;
    }

    .csv-viewer table {
        font-size: 0.85rem;
        font-family: var(--font-mono);
    }

    .download-bar {
        padding: 0.75rem 1rem;
        border-top: 1px solid var(--border-color);
        background: var(--bg-card);
    }
</style>
