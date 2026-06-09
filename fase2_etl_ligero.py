import pandas as pd
import json
from datetime import datetime, timezone

def normalizar_nombre(nombre):
    """Estandariza los nombres de los departamentos para asegurar el merge."""
    if not isinstance(nombre, str): return ""
    n = nombre.upper().strip()
    # Mapeo de casos especiales si existieran diferencias entre ONPE y GeoJSON
    mapping = {
        "LIMA METROPOLITANA": "LIMA",
        "LIMA PROVINCIAS": "LIMA"
    }
    return mapping.get(n, n)

def procesar_etl_ligero():
    print("1. Cargando datos electorales de ONPE...")
    df_elecciones = pd.read_csv('resultados_onpe.csv')
    
    # Normalizamos el nombre del departamento para usarlo como llave principal
    df_elecciones['departamento_key'] = df_elecciones['departamento'].apply(normalizar_nombre)
    
    print("2. Pivotando datos...")
    df_elecciones['partido_columna'] = df_elecciones['nombreAgrupacionPolitica'].str.replace(' ', '_').str.replace('Ú', 'U').str.lower()
    
    # Datos generales usando la nueva llave
    df_avance = df_elecciones[['departamento_key', 'actasContabilizadas', 'participacionCiudadana', 'fechaActualizacion', 'totalActas', 'contabilizadas']].drop_duplicates()
    
    # Pivot de Porcentajes
    df_pct = df_elecciones.pivot(
        index='departamento_key', columns='partido_columna', values='porcentajeVotosValidos'
    ).reset_index()
    
    # Pivot de Votos Absolutos
    df_abs = df_elecciones.pivot(
        index='departamento_key', columns='partido_columna', values='totalVotosValidos'
    ).reset_index()
    
    # Renombramos columnas de absolutos
    df_abs.columns = [col if col == 'departamento_key' else f"{col}_votos" for col in df_abs.columns]
    
    # Unimos todo usando la llave de nombre
    df_final = df_avance.merge(df_pct, on='departamento_key', how='left').merge(df_abs, on='departamento_key', how='left')
    
    print("3. Exportando a JSON...")
    datos_dict = df_final.set_index('departamento_key').to_dict(orient='index')

    # Timestamp propio del pipeline
    ahora_utc = datetime.now(timezone.utc)
    meta = {
        "_meta": {
            "ultima_actualizacion_iso": ahora_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ultima_actualizacion_ts": int(ahora_utc.timestamp() * 1000)
        }
    }

    # Totales nacionales (incluye extranjero)
    nacional_bloque = {}
    try:
        import os
        if os.path.exists("totales_nacionales.json"):
            with open("totales_nacionales.json", "r", encoding="utf-8") as f:
                raw = json.load(f)

            totales = raw.get("totales", {})
            participantes = raw.get("participantes", [])

            # Votos por candidato a nivel nacional
            candidatos_nac = {}
            for c in participantes:
                clave = c.get("nombreAgrupacionPolitica", "").replace(" ", "_").lower()
                candidatos_nac[clave] = {
                    "porcentajeVotosValidos": c.get("porcentajeVotosValidos"),
                    "totalVotosValidos": c.get("totalVotosValidos"),
                    "nombreCandidato": c.get("nombreCandidato")
                }

            nacional_bloque = {
                "_nacional": {
                    "actasContabilizadas": totales.get("actasContabilizadas"),
                    "contabilizadas": totales.get("contabilizadas"),
                    "totalActas": totales.get("totalActas"),
                    "participacionCiudadana": totales.get("participacionCiudadana"),
                    "totalVotosValidos": totales.get("totalVotosValidos"),
                    "totalVotosEmitidos": totales.get("totalVotosEmitidos"),
                    "fechaActualizacion": totales.get("fechaActualizacion"),
                    "candidatos": candidatos_nac
                }
            }
            print("  Totales nacionales integrados en el JSON.")
    except Exception as e:
        print(f"  [!] No se pudo integrar totales_nacionales.json: {e}")

    salida = {**meta, **nacional_bloque, **datos_dict}

    with open('resultados_pivot.json', 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    # ── SERIE TEMPORAL ─────────────────────────────────────────────────────
    # Acumula un punto por ejecución para graficar la evolución del conteo
    try:
        nac = nacional_bloque.get("_nacional", {})
        candidatos_nac = nac.get("candidatos", {})

        clave_jpp = next((k for k in candidatos_nac if "juntos" in k), None)
        clave_fp  = next((k for k in candidatos_nac if "fuerza" in k), None)

        pct_actas  = float(nac.get("actasContabilizadas") or 0)
        votos_jpp  = int(candidatos_nac[clave_jpp]["totalVotosValidos"])  if clave_jpp else 0
        votos_fp   = int(candidatos_nac[clave_fp]["totalVotosValidos"])   if clave_fp  else 0
        pct_jpp    = float(candidatos_nac[clave_jpp]["porcentajeVotosValidos"]) if clave_jpp else 0
        pct_fp     = float(candidatos_nac[clave_fp]["porcentajeVotosValidos"])  if clave_fp  else 0

        if pct_actas > 0 and (votos_jpp + votos_fp) > 0:
            import os
            serie = []
            if os.path.exists("serie_temporal.json"):
                with open("serie_temporal.json", "r", encoding="utf-8") as f:
                    serie = json.load(f)

            nuevo_punto = {
                "ts":        ahora_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "pct_actas": round(pct_actas, 3),
                "votos_jpp": votos_jpp,
                "votos_fp":  votos_fp,
                "pct_jpp":   round(pct_jpp, 3),
                "pct_fp":    round(pct_fp,  3),
            }

            # Deduplicar por pct_actas: si ya existe ese porcentaje, actualizar
            indice = {p["pct_actas"]: i for i, p in enumerate(serie)}
            if pct_actas in indice:
                serie[indice[pct_actas]] = nuevo_punto
            else:
                serie.append(nuevo_punto)

            # Mantener ordenado por avance de actas
            serie.sort(key=lambda p: p["pct_actas"])

            with open("serie_temporal.json", "w", encoding="utf-8") as f:
                json.dump(serie, f, ensure_ascii=False, indent=2)
            print(f"  Serie temporal actualizada: {len(serie)} puntos (actas: {pct_actas}%)")
        else:
            print("  [!] Sin datos nacionales suficientes para serie temporal.")
    except Exception as e:
        print(f"  [!] Error actualizando serie temporal: {e}")

    print("¡ETL completado exitosamente usando nombres como llave primaria!")

if __name__ == "__main__":
    procesar_etl_ligero()