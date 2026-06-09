import requests
import pandas as pd
import json
import time
from datetime import datetime

# 1. Diccionario maestro de los 25 departamentos
departamentos_peru = {
    "010000": "AMAZONAS", "020000": "ANCASH", "030000": "APURIMAC",
    "040000": "AREQUIPA", "050000": "AYACUCHO", "060000": "CAJAMARCA",
    "240000": "CALLAO", "070000": "CUSCO", "080000": "HUANCAVELICA",
    "090000": "HUANUCO", "100000": "ICA", "110000": "JUNIN",
    "120000": "LA LIBERTAD", "130000": "LAMBAYEQUE", "140000": "LIMA",
    "150000": "LORETO", "160000": "MADRE DE DIOS", "170000": "MOQUEGUA",
    "180000": "PASCO", "190000": "PIURA", "200000": "PUNO",
    "210000": "SAN MARTIN", "220000": "TACNA", "230000": "TUMBES",
    "250000": "UCAYALI"
}

# 2. Cabeceras actualizadas desde tu cURL (Android/Chrome 149)
headers = {
    "accept": "*/*",
    "accept-language": "es-US,es-ES;q=0.9,es-419;q=0.8,es;q=0.7",
    "content-type": "application/json",
    "priority": "u=1, i",
    "referer": "https://resultadosegundavuelta.onpe.gob.pe/main/resumen",
    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36",
    # Las cookies _ga son de Google Analytics y expiran. No son necesarias para la API de la ONPE.
}

# Los dos endpoints de la ONPE
url_totales = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend/resumen-general/totales"
url_participantes = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend/resumen-general/participantes"

datos_electorales = []

print("Iniciando extracción combinada (Totales + Participantes) de la ONPE...")

# 3. Bucle de iteración
for ubigeo, nombre_dep in departamentos_peru.items():
    print(f"Extrayendo datos de: {nombre_dep} (Ubigeo: {ubigeo})...")
    
    params = {
        "idEleccion": 10,
        "tipoFiltro": "ubigeo_nivel_01",
        "idAmbitoGeografico": 1,
        "idUbigeoDepartamento": ubigeo
    }
    
    try:
        # A. Primero obtenemos el resumen general (Actas y Participación)
        resp_totales = requests.get(url_totales, headers=headers, params=params)
        actas_contabilizadas = 0
        participacion = 0
        
        if resp_totales.status_code == 200:
            json_totales = resp_totales.json()
            if json_totales.get("success") and "data" in json_totales:
                data_t = json_totales["data"]
                actas_contabilizadas = data_t.get("actasContabilizadas", 0)
                participacion = data_t.get("participacionCiudadana", 0)
                fecha_actualizacion = data_t.get("fechaActualizacion", 0)
                total_actas = data_t.get("totalActas", 0)
                contabilizadas_num = data_t.get("contabilizadas", 0)
        
        time.sleep(0.5) # Breve pausa entre peticiones

        # B. Luego obtenemos los resultados de los partidos
        resp_participantes = requests.get(url_participantes, headers=headers, params=params)
        
        if resp_participantes.status_code == 200:
            try:
                json_participantes = resp_participantes.json()
                
                if json_participantes.get("success") and "data" in json_participantes:
                    candidatos = json_participantes["data"]
                    
                    for candidato in candidatos:
                        registro = {
                            "ubigeo_departamento": ubigeo,
                            "departamento": nombre_dep,
                            # Añadimos la data de avance general
                            "actasContabilizadas": actas_contabilizadas,
                            "participacionCiudadana": participacion,
                            "fechaActualizacion": fecha_actualizacion,
                            "totalActas": total_actas,
                            "contabilizadas": contabilizadas_num,
                            # Data del candidato
                            "nombreAgrupacionPolitica": candidato.get("nombreAgrupacionPolitica"),
                            "codigoAgrupacionPolitica": candidato.get("codigoAgrupacionPolitica"),
                            "nombreCandidato": candidato.get("nombreCandidato"),
                            "dniCandidato": candidato.get("dniCandidato"),
                            "totalVotosValidos": candidato.get("totalVotosValidos"),
                            "porcentajeVotosValidos": candidato.get("porcentajeVotosValidos"),
                            "porcentajeVotosEmitidos": candidato.get("porcentajeVotosEmitidos")
                        }
                        datos_electorales.append(registro)
                else:
                    print(f"  [!] Datos vacíos de participantes para {nombre_dep}.")
                    
            except requests.exceptions.JSONDecodeError:
                print(f"  [X] Bloqueo detectado. El servidor no devolvió JSON.")
        else:
            print(f"  [X] Error HTTP {resp_participantes.status_code} para {nombre_dep}.")
            
    except Exception as e:
         print(f"  [X] Error al procesar {nombre_dep}: {str(e)}")
    
    time.sleep(1) # Pausa amigable para el servidor

# 4. Consolidación
if datos_electorales:
    print("\nExtracción finalizada. Creando DataFrame...")
    df_resultados = pd.DataFrame(datos_electorales)
    
    # 5. Exportar siempre como 'resultados_onpe.csv' para que el ETL lo encuentre
    # Y opcionalmente un histórico con la fecha
    fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = "resultados_onpe.csv" 
    archivo_historico = f"historico/resultados_onpe_{fecha_hora}.csv"
    
    # Guardar la versión principal que consume el ETL espacial
    df_resultados.to_csv(archivo_salida, index=False, encoding='utf-8-sig')
    print(f"Datos guardados exitosamente en: {archivo_salida}")
    
    # Guardamos el histórico en un CSV separado por si falla la automatización
    import os
    os.makedirs("historico", exist_ok=True)
    df_resultados.to_csv(archivo_historico, index=False, encoding='utf-8-sig')

else:
    print("\nNo se pudieron extraer datos.")

# ── VOTOS DEL EXTRANJERO ──────────────────────────────────────────────────
print("\nObteniendo datos de votos del extranjero...")
try:
    params_ext = {
        "idEleccion": 10,
        "tipoFiltro": "ambito_geografico",
        "idAmbitoGeografico": 2
    }
    resp_t_ext = requests.get(url_totales,       headers=headers, params=params_ext)
    time.sleep(0.5)
    resp_p_ext = requests.get(url_participantes, headers=headers, params=params_ext)

    extranjero_data = {}

    if resp_t_ext.status_code == 200:
        j = resp_t_ext.json()
        if j.get("success") and "data" in j:
            extranjero_data["totales"] = j["data"]
            print(f"  Actas extranjero: {j['data'].get('actasContabilizadas')}%  "
                  f"({j['data'].get('contabilizadas')} / {j['data'].get('totalActas')})")
        else:
            print(f"  [!] Respuesta sin datos en totales extranjero.")
    else:
        print(f"  [!] HTTP {resp_t_ext.status_code} en totales extranjero.")

    if resp_p_ext.status_code == 200:
        j = resp_p_ext.json()
        if j.get("success") and "data" in j:
            extranjero_data["participantes"] = j["data"]
            for c in j["data"]:
                print(f"    {c.get('nombreAgrupacionPolitica')}: "
                      f"{c.get('totalVotosValidos')} votos "
                      f"({c.get('porcentajeVotosValidos')}%)")
    else:
        print(f"  [!] HTTP {resp_p_ext.status_code} en participantes extranjero.")

    with open("extranjero.json", "w", encoding="utf-8") as f:
        json.dump(extranjero_data, f, ensure_ascii=False, indent=2)
    print("  Datos del extranjero guardados en extranjero.json")

except Exception as e:
    print(f"  [!] Error obteniendo datos del extranjero: {e}")

# ── TOTALES NACIONALES (incluye votos del extranjero) ──────────────────────
print("\nObteniendo totales nacionales (tipoFiltro=eleccion)...")
try:
    params_nac = {"idEleccion": 10, "tipoFiltro": "eleccion"}

    resp_t_nac = requests.get(url_totales, headers=headers, params=params_nac)
    resp_p_nac = requests.get(url_participantes, headers=headers, params=params_nac)

    nacional = {}

    if resp_t_nac.status_code == 200:
        j = resp_t_nac.json()
        if j.get("success") and "data" in j:
            nacional["totales"] = j["data"]
            print(f"  Actas nacionales: {j['data'].get('actasContabilizadas')}%")

    time.sleep(0.5)

    if resp_p_nac.status_code == 200:
        j = resp_p_nac.json()
        if j.get("success") and "data" in j:
            nacional["participantes"] = j["data"]

    with open("totales_nacionales.json", "w", encoding="utf-8") as f:
        json.dump(nacional, f, ensure_ascii=False, indent=2)
    print("Totales nacionales guardados en totales_nacionales.json")

except Exception as e:
    print(f"  [!] Error obteniendo totales nacionales: {e}")