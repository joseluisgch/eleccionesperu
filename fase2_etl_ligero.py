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
        
    print("¡ETL completado exitosamente usando nombres como llave primaria!")

if __name__ == "__main__":
    procesar_etl_ligero()