<!--
  ConfigPanel.svelte - Simulation configuration form
-->
<script lang="ts">
    import { api, type JobCreate } from '$lib/api';
    import { queue } from '$lib/stores';

    // Form state
    let particles = 1000;
    let energy = '1 GeV';
    let thickness = '1 cm';
    let cycles = 1;
    let generateSvg = true;
    let isSubmitting = false;
    let error = '';

    async function addToQueue() {
        isSubmitting = true;
        error = '';

        try {
            const job: JobCreate = {
                particles,
                energy,
                thickness,
                cycles,
                generate_svg: generateSvg
            };

            const newJob = await api.createJob(job);
            
            // Refresh queue
            const updatedQueue = await api.getQueue();
            queue.set(updatedQueue);

        } catch (e: any) {
            error = e.message || 'Failed to add job';
        } finally {
            isSubmitting = false;
        }
    }
</script>

<div class="config-panel">
    <div class="panel-header">
        <div class="header-icon">⚛</div>
        <div>
            <h2>Configure Simulation</h2>
            <p class="text-muted text-sm">Set parameters for Geant4 run</p>
        </div>
    </div>

    <form on:submit|preventDefault={addToQueue}>
        <div class="form-group">
            <label for="particles">Particle Count</label>
            <input 
                type="number" 
                id="particles"
                bind:value={particles}
                min="1"
                placeholder="1000"
            />
        </div>

        <div class="form-group">
            <label for="energy">Beam Energy</label>
            <input 
                type="text" 
                id="energy"
                bind:value={energy}
                placeholder="1 GeV"
            />
            <span class="input-hint">e.g., 1 GeV, 500 MeV</span>
        </div>

        <div class="form-group">
            <label for="thickness">Target Thickness</label>
            <input 
                type="text" 
                id="thickness"
                bind:value={thickness}
                placeholder="1 cm"
            />
            <span class="input-hint">e.g., 1 cm, 50 mm</span>
        </div>

        <div class="form-group">
            <label for="cycles">Simulation Cycles</label>
            <input 
                type="number" 
                id="cycles"
                bind:value={cycles}
                min="1"
                max="1000"
                placeholder="1"
            />
        </div>

        <div class="form-group">
            <label class="checkbox-wrapper">
                <input 
                    type="checkbox" 
                    bind:checked={generateSvg}
                />
                <span>Generate Visualization (SVG)</span>
            </label>
        </div>

        {#if error}
            <div class="error-message">{error}</div>
        {/if}

        <button 
            type="submit" 
            class="btn-primary w-full"
            disabled={isSubmitting}
        >
            {#if isSubmitting}
                <span class="animate-spin">⟳</span>
                Adding...
            {:else}
                <span>+</span>
                Add to Queue
            {/if}
        </button>
    </form>
</div>

<style>
    .config-panel {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        height: fit-content;
    }

    .panel-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--border-color);
    }

    .header-icon {
        font-size: 1.5rem;
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(59, 130, 246, 0.1);
        border-radius: var(--radius-md);
    }

    .panel-header h2 {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0;
    }

    form {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
    }

    .form-group {
        display: flex;
        flex-direction: column;
    }

    .input-hint {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-top: 0.35rem;
    }

    .error-message {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: var(--status-error);
        padding: 0.75rem;
        border-radius: var(--radius-sm);
        font-size: 0.875rem;
    }
</style>
