import pandas as pd
import json

def procesar_etl_ligero():
    print("1. Cargando datos electorales de ONPE...")
    df_elecciones = pd.read_csv('resultados_onpe.csv')
    df_elecciones['ubigeo_departamento'] = df_elecciones['ubigeo_departamento'].astype(str).str.zfill(6)
    
    print("2. Pivotando datos...")
    df_elecciones['partido_columna'] = df_elecciones['nombreAgrupacionPolitica'].str.replace(' ', '_').str.replace('Ú', 'U').str.lower()
    
    # Datos generales de la región
    df_avance = df_elecciones[['ubigeo_departamento', 'departamento', 'actasContabilizadas', 'participacionCiudadana', 'fechaActualizacion', 'totalActas', 'contabilizadas']].drop_duplicates()
    
    # Pivot de Porcentajes
    df_pct = df_elecciones.pivot(
        index='ubigeo_departamento', columns='partido_columna', values='porcentajeVotosValidos'
    ).reset_index()
    
    # Pivot de Votos Absolutos (Nuevo)
    df_abs = df_elecciones.pivot(
        index='ubigeo_departamento', columns='partido_columna', values='totalVotosValidos'
    ).reset_index()
    
    # Renombramos las columnas de absolutos para no chocar con las de porcentajes
    nuevas_columnas = []
    for col in df_abs.columns:
        if col == 'ubigeo_departamento':
            nuevas_columnas.append(col)
        else:
            nuevas_columnas.append(f"{col}_votos")
    df_abs.columns = nuevas_columnas
    
    # Unimos todo
    df_final = df_avance.merge(df_pct, on='ubigeo_departamento', how='left').merge(df_abs, on='ubigeo_departamento', how='left')
    
    print("3. Exportando a JSON para el visor web...")
    datos_dict = df_final.set_index('ubigeo_departamento').to_dict(orient='index')
    
    with open('resultados_pivot.json', 'w', encoding='utf-8') as f:
        json.dump(datos_dict, f, ensure_ascii=False, indent=2)
        
    print("¡ETL completado! Archivo 'resultados_pivot.json' generado exitosamente.")

if __name__ == "__main__":
    procesar_etl_ligero()