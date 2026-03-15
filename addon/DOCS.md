# Geant4 Simulation Dashboard

Team-based web dashboard for managing Geant4 electromagnetic cascade simulations with Cloudflare Tunnel access.

## Features

- **Web Dashboard**: SvelteKit-based UI for configuring and running simulations
- **Queue System**: Submit jobs and monitor progress in real-time via WebSocket
- **Visualization**: Automatic SVG generation of results
- **Remote Access**: Cloudflare Tunnel integration for secure external access
- **Persistence**: SQLite database for job history

## Requirements

1. **Pre-built GeantSim binary**: You must compile the `GeantSim` binary on aarch64 (Raspberry Pi 5) and place it in `addon/bin/GeantSim` before building the add-on.
2. **Cloudflare Account**: Required for external access via tunnel.

## Setup Instructions

### 1. Compile GeantSim on Raspberry Pi 5

On your RPi5, compile Geant4 and the simulation binary:

```bash
# Install Geant4 (if not already installed)
./install_geant4.sh

# Compile the simulation
./compile_sim.sh

# Copy the binary to add-on directory
mkdir -p addon/bin
cp build/GeantSim addon/bin/
```

### 2. Configure Cloudflare Tunnel

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Networks → Tunnels → Create a tunnel**
3. Select **Cloudflared** connector
4. Name your tunnel (e.g., `geant4-sim`)
5. Copy the tunnel token
6. Configure public hostnames:
   - `sim.maksu.online` → `http://localhost:4173`
   - `api.maksu.online` → `http://localhost:8000`

### 3. Install Add-on in Home Assistant

1. Copy the `addon/` directory to your HA OS installation:
   ```bash
   scp -r addon/ root@homeassistant.local:/addons/geant4-sim/
   ```

2. In Home Assistant:
   - Go to **Settings → Add-ons → Add-on Store**
   - Click **⋮** → **Check for updates**
   - Find "Geant4 Simulation Dashboard" and install

3. Configure the add-on:
   - Paste your Cloudflare Tunnel token
   - Update domains if needed
   - Start the add-on

### 4. Access the Dashboard

Once running, access your dashboard at:
- **https://sim.maksu.online**

## Troubleshooting

### Add-on won't start
Check the add-on logs in HA for errors. Common issues:
- Missing GeantSim binary
- Invalid tunnel token

### WebSocket not connecting
Ensure both domains are configured in Cloudflare tunnel with WebSocket support enabled.

### Simulation fails
Check that the pre-built binary is compatible with aarch64 and has execute permissions.

## Architecture

```
Home Assistant OS (RPi5)
└── Add-on Container
    ├── cloudflared (tunnel)
    ├── SvelteKit (port 4173)
    ├── FastAPI (port 8000)
    └── GeantSim (worker)
```

## Support

For issues and feature requests, see the project repository.
