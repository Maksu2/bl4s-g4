# Geant4 Simulation Dashboard

Panel zespołowy do symulacji elektromagnetycznych Geant4.

## Instalacja

1. Skopiuj folder `sim_addon` do `/addons/local/` na Home Assistant
2. Odśwież sklep add-onów
3. Zainstaluj "Geant4 Simulation Dashboard"
4. Wklej Cloudflare Tunnel Token w konfiguracji
5. Uruchom

## Konfiguracja (Krok po kroku)

### 1. W Cloudflare Dashboard (strona www)
Wejdź na [one.dash.cloudflare.com](https://one.dash.cloudflare.com/) → Networks → Tunnels.
1. Utwórz tunel i **skopiuj token**.
2. W zakładce **Public Hostname** dodaj dwie reguły dla domeny `sim.maksu.online`:

| Path | Type | URL / Address | Uwagi |
|------|------|---------------|-------|
| `/api*` | **HTTP** | `localhost:8000` | **Musi być pierwsza!** (bez `http://`) |
| `/*` | **HTTP** | `localhost:4173` | Domyślna dla reszty |

### 2. W Home Assistant (sim_addon)
1. Zainstaluj add-on z folderu `local`.
2. W zakładce **Configuration** wklej tylko token:
   - `tunnel_token`: `eyJhIjoi...` (twój długi token z punktu 1)
3. Uruchom add-on.

## Dostęp

Po uruchomieniu: **https://sim.maksu.online**
