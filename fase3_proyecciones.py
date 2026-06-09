"""
FASE 3 — Modelo de Proyección Electoral
========================================
Metodología:
  Por cada departamento y el extranjero, calcula cuántos votos adicionales
  recibiría cada candidato si los actas pendientes siguieran la misma
  tendencia porcentual que las ya contabilizadas.

  Fórmula por unidad geográfica:
    votos_por_acta       = totalVotosValidos / contabilizadas
    votos_pendientes_est = actas_pendientes * votos_por_acta
    votos_proy_candidato = votos_actuales + (votos_pendientes_est * pct_candidato / 100)
"""
import json
import os
from datetime import datetime, timezone


# ─── helpers ────────────────────────────────────────────────────────────────

def find_key(data: dict, contains: str, votos: bool = False) -> str | None:
    """Localiza la clave de un candidato en el dict del departamento."""
    excluir = {'actascontabilizadas', 'participacionciudadana', 'fechaactualizacion',
               'totalactas', 'contabilizadas', 'departamento_key'}
    for k in data:
        k_low = k.lower()
        if contains in k_low and k_low not in excluir:
            if votos and '_votos' in k_low:
                return k
            if not votos and '_votos' not in k_low:
                return k
    return None


REGION_DEPTS = {
    "PUNO": "sur", "CUSCO": "sur", "AREQUIPA": "sur", "MOQUEGUA": "sur",
    "TACNA": "sur", "APURIMAC": "sur", "AYACUCHO": "sur", "MADRE DE DIOS": "sur",
    "HUANCAVELICA": "sierra central", "JUNIN": "sierra central", "PASCO": "sierra central",
    "ANCASH": "sierra norte", "CAJAMARCA": "norte", "LA LIBERTAD": "norte",
    "PIURA": "norte", "LAMBAYEQUE": "norte", "TUMBES": "norte",
    "AMAZONAS": "oriente", "LORETO": "oriente", "SAN MARTIN": "oriente",
    "UCAYALI": "oriente", "HUANUCO": "oriente", "ICA": "costa sur",
}


def generar_narrativa(proy_depts: list, proy_nac: dict, proy_ext: dict) -> str:
    """Genera análisis narrativo detallado del resultado electoral proyectado."""
    ganador_key = proy_nac["ganador_key"]
    nombre_gan  = proy_nac["ganador_proyectado"]
    nombre_per  = "FUERZA POPULAR" if ganador_key == "JPP" else "JUNTOS POR EL PERÚ"
    diff_total  = proy_nac["diferencia_proyectada"]
    sign        = 1 if ganador_key == "JPP" else -1

    def fmt(n): return f"{abs(round(n)):,}".replace(",", " ")
    def tit(s): return s.title()

    lima   = next((d for d in proy_depts if d["nombre"] == "LIMA"),   None)
    callao = next((d for d in proy_depts if d["nombre"] == "CALLAO"), None)
    dif_lima   = (lima["diferencia_proyectada"]   * sign) if lima   else 0
    dif_callao = (callao["diferencia_proyectada"] * sign) if callao else 0
    dif_lc     = dif_lima + dif_callao

    depts_gan = sorted(
        [d for d in proy_depts
         if d["diferencia_proyectada"] * sign > 0
         and d["nombre"] not in ("LIMA", "CALLAO")],
        key=lambda x: x["diferencia_proyectada"] * sign, reverse=True
    )
    depts_per = sorted(
        [d for d in proy_depts if d["diferencia_proyectada"] * sign < 0],
        key=lambda x: x["diferencia_proyectada"] * sign
    )

    parrafos = []

    # ── Párrafo 1: resultado + desafío Lima/Callao ────────────────────────
    p1 = (f"Con una diferencia estimada de {fmt(diff_total)} votos, "
          f"{nombre_gan} se perfila como ganador de la segunda vuelta presidencial.")

    if lima and callao and dif_lc < 0:
        p1 += (f" El principal desafío para esta candidatura fue compensar la amplia ventaja "
               f"obtenida por {nombre_per} en Lima Metropolitana y el Callao, territorios que "
               f"concentran cerca del 40 % del electorado nacional. En conjunto, ambas "
               f"jurisdicciones otorgaron a {nombre_per} una ventaja de {fmt(abs(dif_lc))} votos "
               f"sobre {nombre_gan}.")
    elif lima and callao and dif_lc > 0:
        p1 += (f" Lima Metropolitana y el Callao —que concentran cerca del 40 % del "
               f"electorado nacional— también se inclinaron por {nombre_gan} con una ventaja "
               f"combinada de {fmt(dif_lc)} votos, consolidando la victoria.")
    parrafos.append(p1)

    # ── Párrafo 2: departamentos que revirtieron el déficit ───────────────
    if depts_gan:
        top3  = depts_gan[:3]
        noms  = [tit(d["nombre"]) for d in top3]
        difs  = [d["diferencia_proyectada"] * sign for d in top3]
        acum3 = sum(difs)

        # Detectar región predominante de los top 3
        regiones = [REGION_DEPTS.get(d["nombre"], "interior") for d in top3]
        if regiones.count("sur") >= 2:
            zona = "del sur del país"
        elif regiones.count("norte") >= 2:
            zona = "del norte del país"
        elif regiones.count("oriente") >= 2:
            zona = "de la amazonía"
        else:
            zona = "del interior del país"

        if dif_lc < 0:
            p2 = (f"La reversión de esta brecha fue posible gracias al contundente respaldo "
                  f"obtenido en departamentos {zona}. {noms[0]} aportó una ventaja de "
                  f"{fmt(difs[0])} votos para {nombre_gan}")
            if len(top3) >= 2:
                p2 += f", seguido por {noms[1]} con {fmt(difs[1])} votos"
            if len(top3) >= 3:
                p2 += f" y {noms[2]} con {fmt(difs[2])} votos"
            p2 += (f". En conjunto, estos tres departamentos acumularon una ventaja de "
                   f"{fmt(acum3)} votos, "
                   f"{'superando' if acum3 > abs(dif_lc) else 'reduciendo significativamente'} "
                   f"el déficit generado en la capital y consolidándose como territorios clave "
                   f"en la definición del resultado electoral.")
        else:
            p2 = (f"Los mayores aportantes a la victoria {zona} fueron {noms[0]} "
                  f"(+{fmt(difs[0])} votos), {noms[1]} (+{fmt(difs[1])}) "
                  f"y {noms[2]} (+{fmt(difs[2])}).")
        parrafos.append(p2)

    # ── Párrafo 3: bastiones del oponente ────────────────────────────────
    if depts_per:
        top_per = depts_per[:2]
        items = []
        for d in top_per:
            lbl  = "Lima Metropolitana" if d["nombre"] == "LIMA" else tit(d["nombre"])
            items.append(f"{lbl} (+{fmt(abs(d['diferencia_proyectada']))} votos)")
        p3 = (f"Por su parte, {' y '.join(items)} se consolidaron como los principales bastiones "
              f"electorales de {nombre_per}, evidenciando una marcada diferenciación territorial "
              f"del voto entre la capital y gran parte del interior del país.")
        parrafos.append(p3)

    # ── Párrafo 4: voto del extranjero ───────────────────────────────────
    if proy_ext and proy_ext.get("actas_contabilizadas_pct", 0) > 0:
        ext_dif = proy_ext["diferencia_proyectada"]
        ext_pct = proy_ext["actas_contabilizadas_pct"]
        ext_nom = "Juntos por el Perú" if ext_dif >= 0 else "Fuerza Popular"
        fav_key = "JPP" if ext_dif >= 0 else "FP"
        accion  = "sumándose" if fav_key == ganador_key else "restando"
        if abs(ext_dif) > 100:
            parrafos.append(
                f"El voto del extranjero —con {ext_pct:.1f} % de actas contabilizadas— "
                f"proyecta una ventaja de {fmt(abs(ext_dif))} votos para {ext_nom}, "
                f"{accion} al resultado final."
            )

    return "\n\n".join(parrafos)


def proyectar_unidad(votos_jpp, votos_fp, pct_jpp, pct_fp,
                     actas_cont, actas_total) -> dict:
    """Calcula la proyección de una unidad geográfica (dpto o extranjero)."""
    actas_pend = max(0, actas_total - actas_cont)
    votos_tot  = votos_jpp + votos_fp
    vpa        = votos_tot / actas_cont if actas_cont > 0 else 0   # votos por acta
    v_pend_est = actas_pend * vpa

    proy_jpp = votos_jpp + v_pend_est * pct_jpp / 100
    proy_fp  = votos_fp  + v_pend_est * pct_fp  / 100

    return {
        "votos_actuales_jpp":   round(votos_jpp),
        "votos_actuales_fp":    round(votos_fp),
        "pct_jpp":              round(pct_jpp, 3),
        "pct_fp":               round(pct_fp,  3),
        "actas_pendientes":     actas_pend,
        "votos_por_acta":       round(vpa, 1),
        "votos_pendientes_est": round(v_pend_est),
        "votos_proyectados_jpp": round(proy_jpp),
        "votos_proyectados_fp":  round(proy_fp),
        "diferencia_proyectada": round(proy_jpp - proy_fp),
        "lider_proyectado": "JPP" if proy_jpp >= proy_fp else "FP",
    }


# ─── main ───────────────────────────────────────────────────────────────────

def calcular_proyecciones():
    # 1. Cargar datos
    if not os.path.exists("resultados_pivot.json"):
        print("[!] resultados_pivot.json no encontrado. Ejecuta fase2 primero.")
        return

    with open("resultados_pivot.json", "r", encoding="utf-8") as f:
        pivot = json.load(f)

    nacionales  = {}
    extranjero  = {}
    if os.path.exists("totales_nacionales.json"):
        with open("totales_nacionales.json", "r", encoding="utf-8") as f:
            nacionales = json.load(f)
    if os.path.exists("extranjero.json"):
        with open("extranjero.json", "r", encoding="utf-8") as f:
            extranjero = json.load(f)

    # 2. Proyección por departamento
    departamentos = {k: v for k, v in pivot.items() if not k.startswith("_")}

    proy_depts = []
    total_proy_jpp = 0.0
    total_proy_fp  = 0.0

    for nombre, datos in departamentos.items():
        kv_jpp = find_key(datos, "juntos", votos=True)
        kv_fp  = find_key(datos, "fuerza", votos=True)
        kp_jpp = find_key(datos, "juntos", votos=False)
        kp_fp  = find_key(datos, "fuerza", votos=False)

        votos_jpp = float(datos.get(kv_jpp) or 0) if kv_jpp else 0
        votos_fp  = float(datos.get(kv_fp)  or 0) if kv_fp  else 0
        pct_jpp   = float(datos.get(kp_jpp) or 0) if kp_jpp else 0
        pct_fp    = float(datos.get(kp_fp)  or 0) if kp_fp  else 0

        actas_cont  = int(datos.get("contabilizadas") or 0)
        actas_total = int(datos.get("totalActas")     or 0)

        if actas_total == 0:
            continue

        proy = proyectar_unidad(votos_jpp, votos_fp, pct_jpp, pct_fp,
                                actas_cont, actas_total)
        proy["nombre"] = nombre
        proy["actas_contabilizadas_pct"] = round(
            float(datos.get("actasContabilizadas") or 0), 3)

        total_proy_jpp += proy["votos_proyectados_jpp"]
        total_proy_fp  += proy["votos_proyectados_fp"]
        proy_depts.append(proy)

    # Ordenar: mayor aporte absoluto primero
    proy_depts.sort(key=lambda x: abs(x["diferencia_proyectada"]), reverse=True)

    # 3. Proyección del extranjero
    ext_totales      = extranjero.get("totales", {})
    ext_participantes = extranjero.get("participantes", [])

    ext_jpp = next((c for c in ext_participantes
                    if "juntos" in (c.get("nombreAgrupacionPolitica") or "").lower()), {})
    ext_fp  = next((c for c in ext_participantes
                    if "fuerza" in (c.get("nombreAgrupacionPolitica") or "").lower()), {})

    ext_votos_jpp = float(ext_jpp.get("totalVotosValidos")      or 0)
    ext_votos_fp  = float(ext_fp.get("totalVotosValidos")       or 0)
    ext_pct_jpp   = float(ext_jpp.get("porcentajeVotosValidos") or 0)
    ext_pct_fp    = float(ext_fp.get("porcentajeVotosValidos")  or 0)
    ext_actas_cont  = int(ext_totales.get("contabilizadas") or 0)
    ext_actas_total = int(ext_totales.get("totalActas")     or 0)

    proy_ext = proyectar_unidad(ext_votos_jpp, ext_votos_fp, ext_pct_jpp, ext_pct_fp,
                                ext_actas_cont, ext_actas_total)
    proy_ext["actas_contabilizadas_pct"] = round(
        float(ext_totales.get("actasContabilizadas") or 0), 3)

    total_proy_jpp += proy_ext["votos_proyectados_jpp"]
    total_proy_fp  += proy_ext["votos_proyectados_fp"]

    # 4. Resumen nacional proyectado
    total_proy = total_proy_jpp + total_proy_fp
    pct_proy_jpp = total_proy_jpp / total_proy * 100 if total_proy > 0 else 0
    pct_proy_fp  = total_proy_fp  / total_proy * 100 if total_proy > 0 else 0

    nac_totales = nacionales.get("totales", {})
    pct_actas_nac = float(nac_totales.get("actasContabilizadas") or 0)

    if pct_actas_nac >= 97:
        confianza, confianza_color = "Muy Alta", "#16a34a"
    elif pct_actas_nac >= 93:
        confianza, confianza_color = "Alta",     "#2563eb"
    elif pct_actas_nac >= 85:
        confianza, confianza_color = "Media",    "#d97706"
    else:
        confianza, confianza_color = "Baja",     "#dc2626"

    # Top 5 aportantes al ganador proyectado
    ganador = "JPP" if total_proy_jpp >= total_proy_fp else "FP"
    sign    = 1 if ganador == "JPP" else -1
    top_aportantes = sorted(
        [d for d in proy_depts if d["lider_proyectado"] == ganador],
        key=lambda x: x["diferencia_proyectada"] * sign, reverse=True
    )[:5]

    ahora_utc = datetime.now(timezone.utc)

    proy_nac_dict = {
        "votos_proyectados_jpp": round(total_proy_jpp),
        "votos_proyectados_fp":  round(total_proy_fp),
        "pct_proyectado_jpp":    round(pct_proy_jpp, 3),
        "pct_proyectado_fp":     round(pct_proy_fp,  3),
        "diferencia_proyectada": round(abs(total_proy_jpp - total_proy_fp)),
        "ganador_proyectado":    "JUNTOS POR EL PERÚ" if ganador == "JPP" else "FUERZA POPULAR",
        "ganador_key":           ganador,
    }

    narrativa = generar_narrativa(proy_depts, proy_nac_dict, proy_ext)

    resultado = {
        "timestamp": ahora_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pct_actas_procesadas": round(pct_actas_nac, 3),
        "confianza": confianza,
        "confianza_color": confianza_color,
        "proyeccion_nacional": proy_nac_dict,
        "narrativa": narrativa,
        "extranjero": proy_ext,
        "por_departamento": proy_depts,
        "top_aportantes_ganador": top_aportantes,
    }

    with open("proyecciones.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    gd = resultado["proyeccion_nacional"]
    print(f"\n{'='*55}")
    print(f"  PROYECCIÓN FINAL  |  Confianza: {confianza} ({pct_actas_nac:.1f}%)")
    print(f"  Ganador estimado : {gd['ganador_proyectado']}")
    print(f"  JPP proyectado   : {gd['pct_proyectado_jpp']:.3f}%  ({gd['votos_proyectados_jpp']:,} votos)")
    print(f"  FP  proyectado   : {gd['pct_proyectado_fp']:.3f}%  ({gd['votos_proyectados_fp']:,} votos)")
    print(f"  Diferencia est.  : {gd['diferencia_proyectada']:,} votos")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    calcular_proyecciones()