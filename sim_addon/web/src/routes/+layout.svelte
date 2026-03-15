<!-- 
  +layout.svelte - Root layout with global styles and auth check
-->
<script lang="ts">
	import "../app.css";
	import { onMount } from "svelte";
	import {
		isAuthenticated,
		wsConnected,
		systemStatus,
		queue,
		history,
		addLog,
	} from "$lib/stores";
	import { api, createWebSocket } from "$lib/api";
	import LoginScreen from "$lib/components/LoginScreen.svelte";

	let ws: WebSocket | null = null;

	onMount(() => {
		// Check for saved auth
		if (localStorage.getItem("geant4_auth") === "true") {
			isAuthenticated.set(true);
		}

		return () => {
			if (ws) {
				ws.close();
			}
		};
	});

	// Setup WebSocket when authenticated
	$: if ($isAuthenticated && !ws) {
		setupWebSocket();
		loadInitialData();
	}

	function setupWebSocket() {
		ws = createWebSocket(
			(data) => {
				handleWsMessage(data);
			},
			() => {
				wsConnected.set(true);
				addLog({
					timestamp: new Date().toISOString(),
					level: "info",
					message: "🔗 Connected to server",
				});
			},
			() => {
				wsConnected.set(false);
				// Attempt reconnect after 3s
				setTimeout(() => {
					if ($isAuthenticated) {
						setupWebSocket();
					}
				}, 3000);
			},
		);
	}

	function handleWsMessage(data: any) {
		switch (data.type) {
			case "job_update":
				// Refresh queue
				refreshQueue();
				if (data.message) {
					addLog({
						timestamp: new Date().toISOString(),
						level:
							data.status === "failed"
								? "error"
								: data.status === "completed"
									? "success"
									: "info",
						message: data.message,
						job_id: data.job_id,
					});
				}
				break;
			case "system_status":
				refreshStatus();
				break;
			case "log":
				addLog(data);
				break;
		}
	}

	async function loadInitialData() {
		try {
			const [statusData, queueData, historyData] = await Promise.all([
				api.getStatus(),
				api.getQueue(),
				api.getHistory(),
			]);
			systemStatus.set(statusData);
			queue.set(queueData);
			history.set(historyData);
		} catch (e) {
			console.error("Failed to load initial data:", e);
		}
	}

	async function refreshQueue() {
		try {
			const [queueData, historyData] = await Promise.all([
				api.getQueue(),
				api.getHistory(),
			]);
			queue.set(queueData);
			history.set(historyData);
		} catch (e) {
			console.error("Refresh failed:", e);
		}
	}

	async function refreshStatus() {
		try {
			const statusData = await api.getStatus();
			systemStatus.set(statusData);
		} catch (e) {
			console.error("Status refresh failed:", e);
		}
	}
</script>

{#if $isAuthenticated}
	<slot />
{:else}
	<LoginScreen />
{/if}
