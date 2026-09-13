"""Transforma cada aviso num mapa: decide o que desenhar, o enquadramento, os
marcadores de inicio e fim, a frase que diz se o aviso toca o trajeto de
voces, e o link para abrir o mesmo trecho no Google Maps.

Nomes de lugar ficam SEMPRE no original (pedido do usuario em 13/09/2026):
Salinas Valley, Windward Coast, Mauna Kea Summit. E assim que aparecem nas
placas, no GPS e no Google Maps que vao estar na mao durante a viagem.
"""
import hashlib
import json
import re
from datetime import date
from urllib.parse import quote

import _geo

VERSAO = "8"   # 8: nomes das abas e mudanca para /honeymoon/      # mudar isto forca redesenhar todos os mapas numa rodada

SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
          "sexta-feira", "sábado", "domingo"]
NOME_REG = {"ca": "Golden Coast", "oahu": "Oʻahu", "bi": "Hawaiʻi"}
MOTIVOS = [("wildfire", "Incêndio"), ("fire", "Incêndio"), ("slide", "Deslizamento"),
           ("slip", "Deslizamento"), ("flood", "Alagamento"), ("snow", "Neve"),
           ("ice", "Gelo"), ("collision", "Acidente"), ("accident", "Acidente"),
           ("emergency", "Obra emergencial"), ("construction", "Obra"),
           ("paving", "Obra de asfalto"), ("bridge work", "Obra na ponte")]
INICIO_VIAGEM = date(2026, 12, 21)

# Cidades ao longo das estradas do roteiro, so para DAR NOME a um ponto (nao
# sao desenhadas). O geocodificador reverso, num trecho rural da 101, devolve
# o condado inteiro ("Santa Barbara County"), que nao localiza ninguem.
REFERENCIAS = [
    (34.0195, -118.4912, "Santa Monica"), (34.0259, -118.7798, "Malibu"),
    (34.1706, -118.8376, "Thousand Oaks"), (34.2164, -119.0376, "Camarillo"),
    (34.1975, -119.1771, "Oxnard"), (34.2805, -119.2945, "Ventura"),
    (34.3989, -119.5185, "Carpinteria"), (34.4208, -119.6982, "Santa Barbara"),
    (34.4358, -119.8276, "Goleta"), (34.4717, -120.2276, "Gaviota"),
    (34.6136, -120.1929, "Buellton"), (34.9530, -120.4357, "Santa Maria"),
    (35.2828, -120.6596, "San Luis Obispo"), (35.4894, -120.6707, "Atascadero"),
    (35.6266, -120.6910, "Paso Robles"), (36.2127, -121.1261, "King City"),
    (36.3208, -121.2438, "Greenfield"), (36.4247, -121.3263, "Soledad"),
    (36.5066, -121.4444, "Gonzales"), (36.6777, -121.6555, "Salinas"),
    (36.6002, -121.8947, "Monterey"), (36.2704, -121.8081, "Big Sur"),
    (21.3069, -157.8583, "Honolulu"), (21.4022, -157.7980, "Kāneʻohe"),
    (21.6469, -157.9253, "Lāʻie"), (21.5028, -158.0236, "Wahiawā"),
    (19.4428, -155.2350, "Volcano"), (20.0791, -155.4675, "Honokaʻa"),
    (20.0230, -155.6718, "Waimea"), (19.0650, -155.5870, "Nāʻālehu"),
    (19.4969, -155.9217, "Captain Cook"), (19.6400, -155.9969, "Kailua-Kona"),
    (19.9178, -155.7844, "Waikoloa"),
]


def _br(dia):
    return dia[8:10] + "/" + dia[5:7]


def _dias(rotas):
    ds = sorted({_br(r["dia"]) for r in rotas})
    return ds[0] if len(ds) == 1 else ", ".join(ds[:-1]) + " e " + ds[-1]


def _semana(dia):
    return SEMANA[date.fromisoformat(dia).weekday()]


def link_gmaps(pontos):
    """Rota no Google Maps pelo formato de caminho, que o app do celular abre
    com todas as paradas (o formato ?api=1 corta em 3 paradas no celular)."""
    return "https://www.google.com/maps/dir/" + "/".join(
        f"{p[0]:.5f},{p[1]:.5f}" for p in pontos[:10])


def _hash(spec):
    return hashlib.md5((VERSAO + json.dumps(spec, sort_keys=True, ensure_ascii=False))
                       .encode("utf-8")).hexdigest()[:10]


# ----------------------------------------------------------------- rotas

def prepara_rotas(rotas, geo):
    """Calcula (ou tira do cache) a linha de cada rota declarada no monitor."""
    out = {}
    for rid, r in rotas.items():
        try:
            g = _geo.rota(r["paradas"], geo, barco=r.get("barco", False))
            out[rid] = dict(r, id=rid, linha=g["linha"], km=g["km"], h=g["h"])
        except Exception as e:  # noqa: BLE001 - rota sem mapa nao derruba o aviso
            print(f"aviso: rota {rid} indisponivel ({e})")
    return out


def _legs(rotas, regiao):
    return [r for r in rotas.values() if r["regiao"] == regiao and r.get("trajeto")]


def spec_trajeto(r):
    p = r["paradas"]
    volta = _geo.km(p[0][:2], p[-1][:2]) < 0.6
    marcos = []
    if volta:
        marcos.append({"pos": list(p[0][:2]), "tipo": "inicio", "tag": "SAÍDA E VOLTA",
                       "nome": p[0][2]})
    else:
        marcos.append({"pos": list(p[0][:2]), "tipo": "inicio", "tag": "SAÍDA", "nome": p[0][2]})
        marcos.append({"pos": list(p[-1][:2]), "tipo": "fim", "tag": "CHEGADA", "nome": p[-1][2]})
    vistos = {p[0][2], p[-1][2]}
    for q in list(p[1:-1]) + list(r.get("passagens", [])):
        if q[2] and q[2] not in vistos:
            marcos.append({"pos": list(q[:2]), "tipo": "parada", "nome": q[2]})
            vistos.add(q[2])
    leg = [("barco" if r.get("barco") else "rota", "seu trajeto")]
    leg += [("inicio", "saída e volta")] if volta else [("inicio", "saída"), ("fim", "chegada")]
    leg.append(("parada", "parada"))
    km_txt = f"{r['km']} km" + (" de barco" if r.get("barco") else "")
    return {
        "kicker": f"Trajeto · {_br(r['dia'])} · {_semana(r['dia'])}",
        "titulo": r["titulo"],
        "subtitulo": f"{km_txt} · {r['resumo']}",
        "rotas": [{"linha": r["linha"], "barco": r.get("barco", False)}],
        "marcos": marcos, "legenda": leg,
    }


# ------------------------------------------------------------ interdicoes

def _motivo(texto):
    m = re.search(r"due to\s+(?:an?\s+)?([^-]+)", texto, re.I)
    baixo = (m.group(1) if m else texto).lower()
    for chave, pt in MOTIVOS:
        if chave in baixo:
            return pt
    return "Motivo: " + (m.group(1).strip() if m else "não informado")


def _condado(texto):
    m = re.search(r"\(([A-Za-z .]+?) Co\)", texto)
    if m:
        return m.group(1).strip() + " County"
    for c in _geo.DISTRITOS:
        if c in texto.lower():
            return c.title() + " County"
    return ""


def _termino(texto):
    m = re.search(r"on\s+(\d{1,2})/(\d{1,2})/(\d{2})\b", texto)
    if not m:
        return None
    return date(2000 + int(m.group(3)), int(m.group(1)), int(m.group(2)))


def _perto_do_trajeto(pontos_item, legs):
    """(km, rota, vertice) do vertice de trajeto mais perto de qualquer ponto do item."""
    melhor = (1e9, None, None)
    for r in legs:
        for p in pontos_item:
            dist, i = _geo.mais_perto(p, r["linha"])
            if dist < melhor[0]:
                melhor = (dist, r, r["linha"][i])
    return melhor


def mapa_interdicao(rodovia, item, rotas, geo, lcs):  # noqa: C901
    loc = _geo.localiza_interdicao(rodovia, item["texto"], geo, lcs)
    if not loc:
        return None
    legs = _legs(rotas, "ca")
    texto = item["texto"]
    termina = _termino(texto)
    antes = termina is not None and termina < INICIO_VIAGEM
    motivo = _motivo(texto)
    condado = _condado(texto)
    verbo = "fechada" if item["fechado"] else "com restrição"

    if "ponto" in loc:
        pts = [loc["ponto"]]
        trecho = []
        nome = loc["nomes"][0]
        titulo = f"{rodovia} {verbo} em {nome}"
        marcos = [{"pos": loc["ponto"], "tipo": "ponto", "tag": "LOCAL", "nome": nome}]
        leg_item = [("ponto", "local da restrição")]
    else:
        pts = [loc["inicio"], loc["fim"]]
        reto = _geo.km(loc["inicio"], loc["fim"])
        try:
            g = _geo.rota([(loc["inicio"][0], loc["inicio"][1], "a"),
                           (loc["fim"][0], loc["fim"][1], "b")], geo)
            trecho = g["linha"] if g["km"] <= max(2.5 * reto, reto + 3) else [loc["inicio"], loc["fim"]]
        except Exception:  # noqa: BLE001
            trecho = [loc["inicio"], loc["fim"]]
        n0, n1 = loc["nomes"][0], loc["nomes"][-1]
        titulo = f"{rodovia} {verbo} de {n0} até {n1}"
        marcos = [{"pos": loc["inicio"], "tipo": "inicio", "tag": "INÍCIO", "nome": n0},
                  {"pos": loc["fim"], "tipo": "fim", "tag": "FIM", "nome": n1}]
        leg_item = [("trecho", "trecho " + verbo), ("inicio", "início"), ("fim", "fim")]

    dist, rota_prox, vert = _perto_do_trajeto(trecho or pts, legs)
    toca = dist < 0.4
    proximos = [r for r in legs if _perto_do_trajeto(trecho or pts, [r])[0] <= dist + 3]
    if antes:
        efeito = f"Termina em {termina.strftime('%d/%m/%Y')}, antes da viagem."
    elif rota_prox is None:
        efeito = ""
    elif toca:
        efeito = f"Está no seu trajeto de {_dias(proximos)} ({rota_prox['titulo']})."
    else:
        efeito = (f"Seu trajeto passa a {dist:.0f} km em linha reta, perto de "
                  f"{_nome_perto(vert, rotas, geo, raio=15) or 'um trecho sem cidade'} "
                  f"({_dias(proximos)}), e não entra no trecho.")

    enquadra = list(trecho or pts)
    if vert and not toca:
        enquadra.append(vert)
        marcos.append({"pos": vert, "tipo": "parada",
                       "nome": _nome_perto(vert, rotas, geo, raio=15) or "seu trajeto"})
    # sempre uma parada conhecida do roteiro por perto, para o leitor se achar
    if rota_prox:
        ref = min((q for r in legs for q in list(r["paradas"]) + list(r.get("passagens", [])) if q[2]),
                  key=lambda q: _geo.km(q[:2], (trecho or pts)[0]))
        if _geo.km(ref[:2], (trecho or pts)[0]) < 60 and all(m["nome"] != ref[2] for m in marcos):
            marcos.append({"pos": list(ref[:2]), "tipo": "parada", "nome": ref[2]})
            enquadra.append(list(ref[:2]))
    spec = {
        "kicker": " · ".join(x for x in ("Aviso", rodovia, condado) if x),
        "titulo": titulo,
        "subtitulo": f"{motivo}. {efeito}".strip(),
        "rotas": [{"linha": r["linha"]} for r in legs],
        "trechos": [trecho] if trecho else [],
        "marcos": marcos, "enquadra": enquadra,
        "legenda": [("rota", "seu trajeto")] + leg_item,
    }
    return {
        "tipo": "interdicao", "regiao": "ca", "spec": spec, "titulo": titulo,
        "efeito": efeito, "motivo": motivo, "toca": toca and not antes,
        "link": link_gmaps(trecho[:1] + trecho[-1:] if trecho else pts),
        "texto_original": texto, "item_pontos": pts, "trecho": trecho,
        "marcos_item": [m for m in marcos if m["tipo"] != "parada"],
    }


# --------------------------------------------------------------- avisos NWS

def _nome_perto(p, rotas, geo, raio=20):
    """Nome original do lugar: primeiro uma parada ou passagem do proprio
    roteiro a ate `raio` km (e o nome que voces ja conhecem), senao a cidade
    que o OpenStreetMap da para aquele ponto."""
    # o mais perto entre paradas do roteiro e cidades de referencia, juntos:
    # dar preferencia as paradas rotulava Gaviota como "Buellton", a 17 km
    candidatos = [q for r in rotas.values()
                  for q in list(r["paradas"]) + list(r.get("passagens", [])) if q[2]]
    candidatos += REFERENCIAS
    ref = min(candidatos, key=lambda q: _geo.km(p, q[:2]))
    if _geo.km(p, ref[:2]) < raio:
        return ref[2]
    nome = _reverso(p, geo)
    if not nome or nome.endswith("County"):
        return ref[2] if _geo.km(p, ref[:2]) < 50 else nome
    return nome


def _reverso(p, geo):
    """Nome do lugar mais proximo, como o OpenStreetMap o chama (em ingles).
    Zoom 14: no 12 ele devolvia o condado ("Santa Barbara County") nas duas
    pontas de um trecho de 30 km."""
    k = f"{p[0]:.2f},{p[1]:.2f}"
    rev = geo.setdefault("reverso14", {})
    geo.pop("reverso", None)
    if k not in rev:
        try:
            d = _geo._get("https://nominatim.openstreetmap.org/reverse?format=json&zoom=14"
                          f"&lat={p[0]:.4f}&lon={p[1]:.4f}")
            a = d.get("address", {})
            rev[k] = (a.get("town") or a.get("city") or a.get("village") or a.get("hamlet")
                      or a.get("suburb") or a.get("locality") or a.get("county") or "")
            import time
            time.sleep(1.1)
        except Exception:  # noqa: BLE001
            rev[k] = ""
    return rev[k]


def mapa_aviso(alerta, rotas, geo):
    aneis = _geo.area_do_aviso(alerta.get("zonas") or [], geo)
    if not aneis:
        return None
    reg = alerta["regioes"][0]
    legs = sorted(_legs(rotas, reg), key=lambda r: r["dia"])
    cruzam = []
    entrada = saida = None
    for r in legs:
        corrida, maior = [], []
        dentro_km = 0.0
        ant = None
        for p in r["linha"]:
            if any(_geo.dentro(p, a) for a in aneis):
                if corrida:
                    dentro_km += _geo.km(corrida[-1], p)
                corrida.append(p)
                if len(corrida) > len(maior):
                    maior = list(corrida)
            else:
                corrida = []
        if maior:
            cruzam.append(r)
            if entrada is None:
                entrada, saida, km_dentro = maior[0], maior[-1], dentro_km
    todos = [p for a in aneis for p in a]
    lats, lons = [p[0] for p in todos], [p[1] for p in todos]
    caixa = [[min(lats), min(lons)], [max(lats), max(lons)]]
    marcos, enquadra = [], list(caixa)
    zonas = alerta["onde"]
    if cruzam:
        n_ent = _nome_perto(entrada, rotas, geo) or "entrada"
        n_sai = _nome_perto(saida, rotas, geo) or "saída"
        marcos = [{"pos": entrada, "tipo": "inicio", "tag": "ENTRA NA ÁREA", "nome": n_ent},
                  {"pos": saida, "tipo": "fim", "tag": "SAI DA ÁREA", "nome": n_sai}]
        enquadra += [entrada, saida]
        km_txt = f"{max(1, round(km_dentro))} km"
        if n_ent == n_sai or _geo.km(entrada, saida) < 8:
            efeito = f"Seu trajeto passa {km_txt} dentro da área, perto de {n_ent}, em {_dias(cruzam)}."
        else:
            efeito = (f"Seu trajeto passa {km_txt} dentro da área, de {n_ent} até {n_sai}, "
                      f"em {_dias(cruzam)}.")
        leg = [("rota", "seu trajeto"), ("area", "área do aviso"),
               ("inicio", "entra"), ("fim", "sai")]
        link = link_gmaps([entrada, saida])
    else:
        centro = [(caixa[0][0] + caixa[1][0]) / 2, (caixa[0][1] + caixa[1][1]) / 2]
        dist, rprox, vert = _perto_do_trajeto([centro], legs)
        if vert:
            marcos = [{"pos": vert, "tipo": "parada", "nome": _nome_perto(vert, rotas, geo) or "seu trajeto"}]
            enquadra.append(vert)
            perto = [r for r in legs if _geo.mais_perto(centro, r["linha"])[0] <= dist + 3]
            efeito = (f"A área fica a {dist:.0f} km do seu trajeto ({_dias(perto)}) "
                      f"e não o cruza.")
        else:
            efeito = ""
        leg = [("rota", "seu trajeto"), ("area", "área do aviso")]
        link = link_gmaps([centro])
    fim = alerta.get("fim", "")[:16].replace("T", " ")
    spec = {
        "kicker": f"Aviso do NWS · {NOME_REG.get(reg, reg)}",
        "titulo": f"{alerta['evento']} em {zonas.split(';')[0].strip()}",
        "subtitulo": efeito + (f" Vale até {fim[8:10]}/{fim[5:7]} às {fim[11:16]}, hora local." if fim else ""),
        "rotas": [{"linha": r["linha"]} for r in legs],
        "areas": aneis, "marcos": marcos, "enquadra": enquadra, "legenda": leg,
    }
    return {"tipo": "aviso", "regiao": reg, "spec": spec, "titulo": spec["titulo"],
            "efeito": efeito, "toca": bool(cruzam), "link": link, "aneis": aneis,
            # no mapa-resumo a area ja aparece; entrada e saida so poluiriam
            "marcos_item": []}


# --------------------------------------------------------------- decisoes

def mapa_decisao(dec, rota):
    spec = spec_trajeto(dict(rota, dia=dec["dia"]))
    spec["kicker"] = f"Decisão · {_br(dec['dia'])} · {dec['quando']}"
    spec["titulo"] = dec["titulo"]
    spec["subtitulo"] = dec["motivo"]
    return {"tipo": "decisao", "regiao": rota["regiao"], "spec": spec, "titulo": dec["titulo"],
            "efeito": dec["motivo"], "toca": True,
            "link": link_gmaps([p[:2] for p in rota["paradas"]])}


# ---------------------------------------------------------------- resumo

def mapa_resumo(regiao, itens, rotas):
    legs = _legs(rotas, regiao)
    if not itens or not legs:
        return None
    trechos, areas, marcos, enquadra = [], [], [], []
    for it in itens:
        if it["tipo"] == "interdicao":
            if it["trecho"]:
                trechos.append(it["trecho"])
            enquadra += it["item_pontos"]
        else:
            areas += it["aneis"]
        marcos += it["marcos_item"]
    for r in legs:
        enquadra += [r["linha"][0], r["linha"][-1]]
    ends = {}
    for r in sorted(legs, key=lambda r: r["dia"]):
        for q in (r["paradas"][0], r["paradas"][-1]):
            ends.setdefault(q[2], q)
    marcos += [{"pos": list(q[:2]), "tipo": "parada", "nome": n} for n, q in ends.items()]
    n_int = sum(1 for i in itens if i["tipo"] == "interdicao")
    n_av = sum(1 for i in itens if i["tipo"] == "aviso")
    partes = []
    if n_int:
        partes.append(f"{n_int} interdição" if n_int == 1 else f"{n_int} interdições")
    if n_av:
        partes.append(f"{n_av} aviso do NWS" if n_av == 1 else f"{n_av} avisos do NWS")
    tocam = [i for i in itens if i["toca"]]
    leg = [("rota", "seu trajeto")]
    if trechos:
        leg.append(("trecho", "trecho fechado"))
    if areas:
        leg.append(("area", "área de aviso"))
    leg += [("inicio", "início"), ("fim", "fim")]
    return {"tipo": "resumo", "regiao": regiao, "titulo": f"Mapa de {NOME_REG[regiao]}",
            "toca": bool(tocam), "link": "",
            "efeito": (("1 deles está" if len(tocam) == 1 else f"{len(tocam)} deles estão")
                       + " no seu trajeto." if tocam else "Nenhum toca o seu trajeto."),
            "spec": {"kicker": f"Resumo · {NOME_REG[regiao]}",
                     "titulo": " e ".join(partes) + " perto do seu trajeto",
                     "subtitulo": (("1 deles toca" if len(tocam) == 1 else f"{len(tocam)} deles tocam")
                                   + " o trajeto de vocês." if tocam
                                   else "Nenhum deles toca o trajeto de vocês."),
                     "rotas": [{"linha": r["linha"]} for r in legs],
                     "trechos": trechos, "areas": areas, "marcos": marcos,
                     "enquadra": enquadra, "legenda": leg}}


def com_hash(m):
    if m:
        m["hash"] = _hash(m["spec"])
    return m
