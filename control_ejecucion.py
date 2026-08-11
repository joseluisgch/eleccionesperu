import json
import os
import urllib.request
import sys

def main():
    hubo_cambios = os.environ.get("HUBO_CAMBIOS", "false")
    if hubo_cambios != "true":
        print("Sin cambios en los datos en esta iteracion.")
        return

    pct = 0.0
    es_100 = False

    try:
        if os.path.exists("totales_nacionales.json"):
            with open("totales_nacionales.json", "r", encoding="utf-8") as f:
                d = json.load(f)
            totales = d.get("totales", {})
            pct = float(totales.get("actasContabilizadas", 0))
            cont = int(totales.get("contabilizadas", 0))
            total = int(totales.get("totalActas", 0))
            es_100 = (pct >= 100.0) or (total > 0 and cont >= total)
    except Exception as e:
        print(f"Aviso leyendo totales: {e}")

    print(f"Actas contabilizadas a nivel nacional: {pct}%")

    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not token or not repo:
        print("GITHUB_TOKEN o GITHUB_REPOSITORY no disponible.")
        return

    if es_100:
        print("100% de actas alcanzado. Desactivando workflow...")
        url = f"https://api.github.com/repos/{repo}/actions/workflows/actualizador.yml/disable"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            },
            method="PUT"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"Workflow desactivado exitosamente (HTTP {resp.status}).")
        except Exception as e:
            print(f"Aviso al desactivar: {e}")
    elif pct < 99.5:
        print("Disparando siguiente ejecucion via API...")
        url = f"https://api.github.com/repos/{repo}/actions/workflows/actualizador.yml/dispatches"
        req = urllib.request.Request(
            url,
            data=b'{"ref":"main"}',
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"Siguiente ejecucion programada (HTTP {resp.status}).")
        except Exception as e:
            print(f"Aviso al disparar: {e}")
    else:
        print(f"Conteo al {pct}%. Conteo avanzado: el cron de respaldo cada 15m continuara verificando.")

if __name__ == "__main__":
    main()
