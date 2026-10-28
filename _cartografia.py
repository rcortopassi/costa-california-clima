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


# O que cada aviso do NWS quer dizer para quem esta na estrada. Nenhum deles e
# interdicao: interdicao de verdade vem da Caltrans e tem mapa proprio.
SENTIDO_AVISO = {
    "Coastal Flood Advisory": ("Alerta de maré alta na costa",
                               "água do mar pode cobrir trechos baixos perto da praia na maré cheia"),
    "Coastal Flood Warning": ("Alerta de inundação costeira",
                              "trechos baixos perto do mar podem alagar e fechar"),
    "Coastal Flood Watch": ("Vigilância de inundação costeira", "risco de maré invadir trechos baixos"),
    "Beach Hazards Statement": ("Alerta de perigo nas praias", "ondas e correntes fortes; não entrar no mar"),
    "High Surf Advisory": ("Alerta de ressaca", "ondas grandes; ficar longe das pedras e da beira"),
    "High Surf Warning": ("Aviso de ressaca forte", "ondas perigosas; mirantes à beira-mar podem fechar"),
    "Rip Current Statement": ("Alerta de correnteza", "não entrar no mar"),
    "Wind Advisory": ("Alerta de vento", "rajadas fortes; cuidado com o carro alto nas pontes e serras"),
    "High Wind Warning": ("Aviso de vento forte", "rajadas perigosas; queda de galhos e árvores"),
    "Dense Fog Advisory": ("Alerta de neblina densa", "visibilidade baixa; dirigir devagar"),
    "Flood Watch": ("Vigilância de enchente", "chuva forte pode alagar estradas"),
    "Flood Advisory": ("Alerta de alagamento", "água acumulada em trechos baixos"),
    "Flood Warning": ("Aviso de enchente", "estradas podem fechar por alagamento"),
    "Flash Flood Warning": ("Aviso de enxurrada", "não atravessar trechos alagados"),
    "Winter Storm Warning": ("Aviso de tempestade de inverno", "neve ou gelo nas partes altas"),
    "Winter Weather Advisory": ("Alerta de neve e gelo", "pista escorregadia nas partes altas"),
    "Wind Chill Advisory": ("Alerta de frio intenso", "sensação térmica muito baixa"),
    "Freeze Warning": ("Aviso de congelamento", "gelo na pista de manhã cedo"),
    "Frost Advisory": ("Alerta de geada", "gelo fino na pista de manhã cedo"),
    "Heat Advisory": ("Alerta de calor", "levar água"),
    "Red Flag Warning": ("Alerta de risco de incêndio", "vento seco; nada de fogo"),
    "Small Craft Advisory": ("Alerta para barcos pequenos", "mar agitado para passeios de barco"),
    "Gale Warning": ("Aviso de vendaval no mar", "passeios de barco podem ser cancelados"),
    "Volcano Advisory": ("Alerta vulcânico", "atividade no vulcão"),
}


def _sentido(evento):
    pt, efeito = SENTIDO_AVISO.get(evento, (evento, ""))
    return pt, efeito


def _tamanho(anel):
    return ((max(p[0] for p in anel) - min(p[0] for p in anel))
            * (max(p[1] for p in anel) - min(p[1] for p in anel)))


_OVERPASS_FORA = []


def _overpass(q):
    """Uma tentativa curta por servidor. Se todos falharem, desiste pelo resto da
    rodada: com o Overpass fora do ar, tentar de novo a cada pedaco de area
    levava minutos (27/10/2026)."""
    if _OVERPASS_FORA:
        return None
    import subprocess
    for host in ("overpass-api.de/api", "overpass.private.coffee/api", "overpass.kumi.systems/api"):
        try:
            r = subprocess.run(["curl", "-sS", "--max-time", "12", "-A", _geo.UA,
                                f"https://{host}/interpreter?data=" + quote(q)],
                               capture_output=True, text=True, timeout=15)
            return json.loads(r.stdout).get("elements", [])
        except Exception:  # noqa: BLE001 - servidor ocupado responde HTML ou nada
            continue
    _OVERPASS_FORA.append(True)
    return None


def _nome_da_area(p, geo):
    """Nome da ilha que contem o ponto, pelo Overpass (OpenStreetMap). O
    reverso do Nominatim devolve a cidade (Avalon em vez de Santa Catalina
    Island) ou um pico. Fora de ilha volta vazio e vale o nome da zona."""
    k = f"{p[0]:.2f},{p[1]:.2f}"
    cache = geo.setdefault("ilha", {})
    geo.pop("nome_area", None)
    if k not in cache:
        try:
            q = (f"[out:json][timeout:20];is_in({p[0]:.4f},{p[1]:.4f})->.a;"
                 'area.a[place~"island|islet"];out tags;')
            els = _overpass(q)
            if els is None:
                return ""       # sem cache: tenta de novo na proxima rodada
            cache[k] = next((e["tags"].get("name", "") for e in els if e.get("tags")), "")
        except Exception:  # noqa: BLE001
            return ""       # sem cache: tenta de novo na proxima rodada
    return cache[k]


def _comprimento(linha):
    return sum(_geo.km(a, b) for a, b in zip(linha, linha[1:]))


def mapa_aviso(alerta, rotas, geo):
    aneis = _geo.area_do_aviso(alerta.get("zonas") or [], geo)
    if not aneis:
        return None
    reg = alerta["regioes"][0]
    legs = sorted(_legs(rotas, reg), key=lambda r: r["dia"])
    cruzam = []
    trechos = []          # pedacos do trajeto que ficam dentro da area, para pintar
    entrada = saida = None
    km_dentro = km_total = 0.0
    faixa = None
    for r in legs:
        corrida, maior, corridas = [], [], []
        dentro_km = 0.0
        for p in r["linha"]:
            if any(_geo.dentro(p, a) for a in aneis):
                if corrida:
                    dentro_km += _geo.km(corrida[-1], p)
                corrida.append(p)
                if len(corrida) > len(maior):
                    maior = list(corrida)
            else:
                if len(corrida) > 1:
                    corridas.append(corrida)
                corrida = []
        if len(corrida) > 1:
            corridas.append(corrida)
        if maior:
            cruzam.append(r)
            trechos += corridas or [maior]
            if entrada is None:
                entrada, saida, km_dentro = maior[0], maior[-1], dentro_km
                n_pedacos = len(corridas) or 1
                km_total = _comprimento(r["linha"])
                i0 = r["linha"].index(maior[0])
                i1 = r["linha"].index(maior[-1])
                par = r.get("paradas") or []
                faixa = {"de": par[0][-1] if par else "", "ate": par[-1][-1] if par else "",
                         "total": km_total, "dia": _br(r["dia"]),
                         "ini": _comprimento(r["linha"][:i0 + 1]),
                         "fim": _comprimento(r["linha"][:i1 + 1]), "km": dentro_km,
                         "pedacos": [(_comprimento(r["linha"][:r["linha"].index(c[0]) + 1]),
                                      _comprimento(r["linha"][:r["linha"].index(c[-1]) + 1]))
                                     for c in (corridas or [maior])]}
    todos = [p for a in aneis for p in a]
    lats, lons = [p[0] for p in todos], [p[1] for p in todos]
    caixa = [[min(lats), min(lons)], [max(lats), max(lons)]]
    marcos, enquadra = [], list(caixa)
    zonas = alerta["onde"]
    pt, sentido = _sentido(alerta.get("evento", ""))
    fim = alerta.get("fim", "")[:16].replace("T", " ")
    vale = f" Vale até {fim[8:10]}/{fim[5:7]} às {fim[11:16]}, hora local." if fim else ""
    rotas_spec = [{"linha": r["linha"]} for r in legs]
    if cruzam:
        n_ent = _nome_perto(entrada, rotas, geo) or "entrada"
        n_sai = _nome_perto(saida, rotas, geo) or "saída"
        curto = n_ent == n_sai or _geo.km(entrada, saida) < 8
        if curto:
            marcos = [{"pos": entrada, "tipo": "ponto", "tag": "TRECHO NO AVISO", "nome": n_ent}]
        else:
            marcos = [{"pos": entrada, "tipo": "inicio", "tag": "COMEÇA O TRECHO", "nome": n_ent},
                      {"pos": saida, "tipo": "fim", "tag": "TERMINA O TRECHO", "nome": n_sai}]
        # enquadra o trecho afetado com folga, e nao a area inteira do aviso: uma
        # area do tamanho da baia de San Francisco deixava 21 km de estrada do
        # tamanho de um risco (Coastal Flood Advisory, 27/10/2026)
        pts = [p for t in trechos for p in t]
        la0, la1 = min(p[0] for p in pts), max(p[0] for p in pts)
        lo0, lo1 = min(p[1] for p in pts), max(p[1] for p in pts)
        folga = max(0.12, (la1 - la0) * 0.6, (lo1 - lo0) * 0.6)
        enquadra = [[la0 - folga, lo0 - folga], [la1 + folga, lo1 + folga]]
        km_txt = f"{max(1, round(km_dentro))} km"
        parcial = km_total and km_dentro < 0.9 * km_total
        alcance = (f"{km_txt} de {round(km_total)} km do trajeto" if parcial else f"todo o trajeto ({km_txt})")
        lugar = f"perto de {n_ent}" if curto else f"de {n_ent} até {n_sai}"
        if n_pedacos > 1:
            lugar = f"em {n_pedacos} pedaços; o maior {lugar}"
        titulo = f"{pt}: {alcance}"
        onde = f"Trecho {lugar}, em {_dias(cruzam)}" if parcial else f"Vale para o trajeto inteiro de {_dias(cruzam)}"
        efeito = (f"Aviso do tempo, não interdição de estrada. {onde}"
                  + (f": {sentido}." if sentido else "."))
        leg = [("rota", "seu trajeto"), ("trecho", "trecho dentro do aviso"), ("area", "área do aviso"),
               ("parque", "parque ou reserva")]
        link = link_gmaps([entrada, saida])
    else:
        centro = [(caixa[0][0] + caixa[1][0]) / 2, (caixa[0][1] + caixa[1][1]) / 2]
        dist, rprox, vert = _perto_do_trajeto([centro], legs)
        area_nome = zonas.split(";")[0].strip()
        # o titulo diz o essencial e cabe; o nome da zona do NWS, que pode ser
        # comprido, vai no subtitulo e num rotulo em cima da propria area
        # (Catalina and Santa Barbara Islands, 28/10/2026)
        titulo = f"{pt}: fora do seu trajeto"
        # um rotulo por pedaco da area: uma zona como "Catalina and Santa
        # Barbara Islands" sao duas ilhas, e a pequena sumia sem nome
        # pedacos com o mesmo nome (uma ilha e as pedras em volta) levam um rotulo so;
        # pedaco sem nome conhecido leva o nome da zona, se estiver longe dos outros
        marcos, nomes = [], set()
        for anel in sorted(aneis, key=_tamanho, reverse=True)[:6]:
            meio = [sum(p[0] for p in anel) / len(anel), sum(p[1] for p in anel) / len(anel)]
            nome = _nome_da_area(meio, geo)
            if nome in nomes or (not nome and any(_geo.km(meio, m["pos"]) < 15 for m in marcos)):
                continue
            nomes.add(nome)
            marcos.append({"pos": meio, "tipo": "area", "tag": "ÁREA DO AVISO",
                           "nome": nome or area_nome})
        if vert:
            marcos.append({"pos": vert, "tipo": "parada",
                           "nome": _nome_perto(vert, rotas, geo) or "seu trajeto"})
            enquadra.append(vert)
            perto = [r for r in legs if _geo.mais_perto(centro, r["linha"])[0] <= dist + 3]
            efeito = (f"Área: {area_nome}, a {dist:.0f} km do trajeto ({_dias(perto)}), "
                      f"sem cruzá-lo.")
        else:
            efeito = f"Área: {area_nome}."
        leg = [("rota", "seu trajeto"), ("area", "área do aviso")]
        link = link_gmaps([centro])
    spec = {
        "kicker": f"Aviso do NWS · {alerta.get('evento', '')} · {NOME_REG.get(reg, reg)}",
        "titulo": titulo,
        "subtitulo": efeito + vale,
        "rotas": rotas_spec, "trechos": trechos, "faixa": faixa,
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
