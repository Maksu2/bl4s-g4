<!--
  LoginScreen.svelte - PIN authentication screen
-->
<script lang="ts">
    import { api } from "$lib/api";
    import { isAuthenticated } from "$lib/stores";

    let pin = "";
    let error = "";
    let isLoading = false;

    async function login() {
        if (!pin.trim()) {
            error = "Please enter the team PIN";
            return;
        }

        isLoading = true;
        error = "";

        try {
            await api.authenticate(pin);
            isAuthenticated.set(true);
            localStorage.setItem("geant4_auth", "true");
        } catch (e: any) {
            error = "Invalid PIN";
            pin = "";
        } finally {
            isLoading = false;
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter") {
            login();
        }
    }
</script>

<div class="login-screen">
    <div class="login-card">
        <div class="logo">
            <div class="logo-icon">⚛</div>
            <h1>Geant4 Dashboard</h1>
            <p class="subtitle">Electromagnetic Cascade Simulation</p>
        </div>

        <div class="form">
            <label for="pin">Team Access PIN</label>
            <input
                type="password"
                id="pin"
                bind:value={pin}
                placeholder="Enter PIN"
                on:keydown={handleKeydown}
                autofocus
            />

            {#if error}
                <div class="error">{error}</div>
            {/if}

            <button
                class="btn-primary w-full"
                on:click={login}
                disabled={isLoading}
            >
                {#if isLoading}
                    <span class="animate-spin">⟳</span>
                    Authenticating...
                {:else}
                    Access Dashboard
                {/if}
            </button>
        </div>

        <p class="footer-text">Shared team workspace for Geant4 simulations</p>
    </div>
</div>

<style>
    .login-screen {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--bg-primary);
        padding: 2rem;
    }

    .login-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-xl);
        padding: 3rem;
        width: 100%;
        max-width: 400px;
        text-align: center;
    }

    .logo {
        margin-bottom: 2.5rem;
    }

    .logo-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: inline-block;
        background: linear-gradient(135deg, #3b82f6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .logo h1 {
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        background: linear-gradient(135deg, #f1f5f9, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .subtitle {
        font-size: 0.9rem;
        color: var(--text-muted);
        margin: 0;
    }

    .form {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        text-align: left;
    }

    .form input {
        text-align: center;
        font-size: 1.1rem;
        letter-spacing: 0.2em;
        padding: 1rem;
    }

    .error {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: var(--status-error);
        padding: 0.75rem;
        border-radius: var(--radius-sm);
        font-size: 0.875rem;
        text-align: center;
    }

    .footer-text {
        margin-top: 2rem;
        font-size: 0.8rem;
        color: var(--text-muted);
    }
</style>
