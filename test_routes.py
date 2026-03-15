import sys
import os

# Add sim_addon to path to simulate running inside it
sys.path.append(os.path.abspath("sim_addon"))

try:
    from api.main import app
    
    print("\n🔍 Weryfikacja tras (Routes Verification):")
    found_correct = False
    found_incorrect = False
    
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"  - {route.path}")
            if route.path == "/api/auth":
                found_correct = True
            if "/api/api/" in route.path:
                found_incorrect = True

    print("-" * 30)
    if found_correct and not found_incorrect:
        print("✅ SUKCES: Trasa '/api/auth' istnieje. Brak podwójnych prefiksów.")
        sys.exit(0)
    elif found_incorrect:
        print("❌ BŁĄD: Znaleziono podwójny prefiks (np. '/api/api/auth').")
        sys.exit(1)
    else:
        print("❌ BŁĄD: Nie znaleziono trasy '/api/auth'.")
        sys.exit(1)

except Exception as e:
    print(f"❌ BŁĄD IMPORTU: {e}")
    sys.exit(1)
