"""Geografia dos avisos: a estrada que voces vao percorrer, onde comeca e
termina cada interdicao, e a area de cada aviso do NWS.

Tudo sem chave de API e tudo com cache em state/geo.json, porque nada disso
muda de uma rodada para outra: a rota de 22/12 e a mesma hoje e em dezembro,
e a zona CAZ349 do NWS nao se mexe. So a interdicao nova pede consulta nova.

Fontes:
  OSRM (router.project-osrm.org)   rota pelas estradas do OpenStreetMap
  Caltrans LCS (cwwp2.dot.ca.gov)  inicio e fim de cada interdicao, com
                                   coordenada e postmile
  Nominatim (OpenStreetMap)        reserva: lugar citado no texto da Caltrans
  api.weather.gov/zones            poligono da zona de cada aviso
"""
import hashlib
import json
import math
import re
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

UA = "costa-california-clima/1.0 (rafaelmcortopassi@gmail.com)"

# Distrito da Caltrans de cada condado da rota. D5: Monterey, San Luis Obispo,
# Santa Barbara, Santa Cruz, San Benito. D7: Los Angeles e Ventura.
DISTRITOS = {"monterey": 5, "san luis obispo": 5, "santa barbara": 5,
             "santa cruz": 5, "san benito": 5, "los angeles": 7, "ventura": 7}


def _get(url, accept=None, timeout=60):
    cab = {"User-Agent": UA}
    if accept:
        cab["Accept"] = accept
    ultimo = None
    for t in range(3):
        try:
            with urlopen(Request(url, headers=cab), timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            ultimo = e
            if "SSL" in str(e) or "handshake" in str(e).lower():
                break
            time.sleep(3 * (t + 1))
    # reserva: o Python do Mac (LibreSSL antigo) falha o TLS com alguns
    # servidores que o curl atende. No Actions o urllib resolve antes de chegar aqui.
    import shutil
    import subprocess
    if shutil.which("curl"):
        args = ["curl", "-sS", "--max-time", str(timeout), "-A", UA]
        if accept:
            args += ["-H", f"Accept: {accept}"]
        r = subprocess.run(args + [url], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
        ultimo = f"{ultimo} / curl: {r.stderr.strip()[:120]}"
    raise RuntimeError(f"{url[:90]}: {ultimo}")


def km(a, b):
    """Distancia em km entre dois (lat, lon)."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(min(1.0, h)))


def rumo(de, para):
    """Direcao cardinal em portugues, de um ponto para outro."""
    y = math.sin(math.radians(para[1] - de[1])) * math.cos(math.radians(para[0]))
    x = (math.cos(math.radians(de[0])) * math.sin(math.radians(para[0]))
         - math.sin(math.radians(de[0])) * math.cos(math.radians(para[0]))
         * math.cos(math.radians(para[1] - de[1])))
    g = (math.degrees(math.atan2(y, x)) + 360) % 360
    return ["norte", "nordeste", "leste", "sudeste", "sul", "sudoeste",
            "oeste", "noroeste"][int((g + 22.5) // 45) % 8]


def _enxuga_linha(pts, passo_km=0.15):
    """Um vertice a cada ~150 m. A rota de 22/12 vem com 9.600 pontos do OSRM;
    no mapa isso nao muda nada e no cache pesaria centenas de KB por rodada."""
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for p in pts[1:-1]:
        if km(out[-1], p) >= passo_km:
            out.append(p)
    out.append(pts[-1])
    return out


# ------------------------------------------------------------------ rotas

USADAS = set()


def rota(paradas, cache, barco=False):
    """Linha da rota passando pelas paradas NA ORDEM. paradas: [(lat, lon, nome)].
    Barco nao tem estrada: vira uma linha reta tracejada entre as paradas."""
    chave = ("barco:" if barco else "carro:") + ";".join(
        f"{p[0]:.4f},{p[1]:.4f}" for p in paradas)
    rotas = cache.setdefault("rotas", {})
    USADAS.add(chave)
    if chave in rotas:
        return rotas[chave]
    if barco:
        linha = [[p[0], p[1]] for p in paradas]
        rotas[chave] = {"linha": linha, "km": round(sum(
            km(linha[i], linha[i + 1]) for i in range(len(linha) - 1))), "h": None}
        return rotas[chave]
    coords = ";".join(f"{p[1]},{p[0]}" for p in paradas)
    d = _get("https://router.project-osrm.org/route/v1/driving/"
             f"{coords}?overview=full&geometries=geojson")
    if d.get("code") != "Ok":
        raise RuntimeError(f"OSRM recusou a rota: {d.get('code')}")
    r = d["routes"][0]
    linha = _enxuga_linha([[c[1], c[0]] for c in r["geometry"]["coordinates"]])
    rotas[chave] = {"linha": [[round(a, 5), round(b, 5)] for a, b in linha],
                    "km": round(r["distance"] / 1000), "h": round(r["duration"] / 3600, 1)}
    time.sleep(1.1)       # politica do servidor publico: no maximo 1 por segundo
    return rotas[chave]


def mais_perto(ponto, linha):
    """(distancia km, indice do vertice) do vertice da linha mais proximo."""
    melhor = (1e9, 0)
    for i, p in enumerate(linha):
        d = km(ponto, p)
        if d < melhor[0]:
            melhor = (d, i)
    return melhor


# ---------------------------------------------------------- interdicoes

def _lcs(distrito, cache_rodada):
    if distrito not in cache_rodada:
        u = f"https://cwwp2.dot.ca.gov/data/d{distrito}/lcs/lcsStatusD{distrito:02d}.json"
        try:
            cache_rodada[distrito] = _get(u, timeout=90).get("data", [])
        except Exception as e:  # noqa: BLE001
            print(f"aviso: LCS do distrito {distrito} falhou ({e})")
            cache_rodada[distrito] = []
    return cache_rodada[distrito]


def _num(x):
    try:
        return float(re.sub(r"[^0-9.]", "", str(x)))
    except ValueError:
        return None


def marcos_do_texto(texto):
    """Os lugares que a Caltrans poe entre barras: '/at Los Burros/'."""
    return [m.strip() for m in re.findall(r"/\s*(?:at|in|near)\s+([^/]+?)\s*/", texto, re.I)]


def localiza_interdicao(rodovia, texto, cache, lcs_rodada):
    """Inicio e fim de um item do boletim da Caltrans.

    1. Casa o texto com o feed de interdicoes (LCS), que traz coordenada: pela
       postmile citada ('11.1 mi north of the ... Co Line'), pelo tipo (fechada
       ou meia pista) e pela data de termino ('thru ... on 11/30/26').
    2. Se nao casar, geocodifica os lugares entre barras pelo Nominatim.
    Devolve {"inicio": [lat, lon], "fim": [lat, lon], "nomes": [ini, fim]} ou None.
    """
    marca = hashlib.md5((rodovia + "|" + " ".join(texto.split())).encode()).hexdigest()[:12]
    guardado = cache.setdefault("interdicoes", {})
    if marca in guardado:
        return guardado[marca]

    baixo = texto.lower()
    num_rota = re.sub(r"\D", "", rodovia)
    nomes = marcos_do_texto(texto)
    condados = [c for c in DISTRITOS if c in baixo]
    distritos = sorted({DISTRITOS[c] for c in condados}) or [5, 7]
    pms = [float(x) for x in re.findall(
        r"(\d+(?:\.\d+)?)\s*mi\s+(?:north|south|east|west)\s+of\s+the\s+[a-z /.]+?co\.? line", baixo)]
    termino = re.search(r"on\s+(\d{1,2})/(\d{1,2})/(\d{2})\b", baixo)
    termino = f"20{termino.group(3)}-{int(termino.group(1)):02d}-{int(termino.group(2)):02d}" if termino else None
    fechada = "is closed" in baixo
    meia = "1-way" in baixo or "one-way" in baixo

    achado, nota = None, -1
    for dist in distritos:
        for it in _lcs(dist, lcs_rodada):
            l = it.get("lcs", {})
            b, e, c = l.get("location", {}).get("begin", {}), l.get("location", {}).get("end", {}), l.get("closure", {})
            if re.sub(r"\D", "", str(b.get("beginRoute", ""))) != num_rota:
                continue
            s = 0
            pb, pe = _num(b.get("beginPostmile")), _num(e.get("endPostmile"))
            if pms and pb is not None and abs(pb - pms[0]) <= 0.3:
                s += 3
            if len(pms) > 1 and pe is not None and abs(pe - pms[1]) <= 0.3:
                s += 3
            fim_lcs = (c.get("closureTimestamp") or {}).get("closureEndDate", "")
            if termino and fim_lcs.startswith(termino):
                s += 2
            tipo = str(c.get("typeOfClosure", "")).lower()
            if fechada and tipo == "full" and "ramp" not in str(c.get("facility", "")).lower():
                s += 1
            if meia and "one-way" in tipo:
                s += 1
            lugar = (str(b.get("beginNearbyPlace", "")) + " " + str(b.get("beginLocationName", ""))).lower()
            if any(n.lower().split()[0] in lugar for n in nomes if n):
                s += 1
            if s > nota:
                nota, achado = s, (b, e)
    # exige mais que coincidencia de tipo: postmile ou data de termino
    if achado and nota >= 3:
        b, e = achado
        ini = [float(b["beginLatitude"]), float(b["beginLongitude"])]
        fim = [float(e["endLatitude"]), float(e["endLongitude"])]
        if km(ini, fim) < 1.0:
            res = {"ponto": [(ini[0] + fim[0]) / 2, (ini[1] + fim[1]) / 2],
                   "fonte": "Caltrans LCS",
                   "nomes": [nomes[0] if nomes else str(b.get("beginNearbyPlace", "")).strip()]}
            guardado[marca] = res
            return res
        res = {"inicio": ini, "fim": fim, "fonte": "Caltrans LCS",
               "nomes": [nomes[0] if nomes else str(b.get("beginNearbyPlace", "")).strip(),
                         nomes[-1] if len(nomes) > 1 else (nomes[0] if nomes else
                                                           str(e.get("endNearbyPlace", "")).strip())]}
        guardado[marca] = res
        return res

    # reserva: os lugares entre barras, no condado citado
    pontos = []
    for n in nomes[:2]:
        q = f"{n}, {condados[0].title() + ' County, ' if condados else ''}California"
        try:
            d = _get("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + quote(q))
            time.sleep(1.1)
            if d:
                pontos.append([float(d[0]["lat"]), float(d[0]["lon"])])
        except Exception as e:  # noqa: BLE001
            print(f"aviso: Nominatim falhou para '{q}' ({e})")
    if not pontos:
        guardado[marca] = None
        return None
    if len(pontos) == 1:
        res = {"ponto": pontos[0], "fonte": "OpenStreetMap", "nomes": [nomes[0]]}
    else:
        res = {"inicio": pontos[0], "fim": pontos[1], "fonte": "OpenStreetMap",
               "nomes": nomes[:2]}
    guardado[marca] = res
    return res


# ---------------------------------------------------------------- zonas NWS

def area_do_aviso(zonas, cache):
    """Poligonos das zonas de um aviso, como lista de aneis [[lat, lon], ...]."""
    guardado = cache.setdefault("zonas", {})
    aneis = []
    for url in zonas:
        zid = url.rstrip("/").split("/")[-1]
        if zid not in guardado:
            try:
                g = _get(url, accept="application/geo+json").get("geometry") or {}
                polys = g.get("coordinates", [])
                if g.get("type") == "Polygon":
                    polys = [polys]
                guardado[zid] = [[[round(pt[1], 4), round(pt[0], 4)] for pt in anel[0]]
                                 for anel in polys if anel]
                time.sleep(0.5)
            except Exception as e:  # noqa: BLE001
                print(f"aviso: zona {zid} sem geometria ({e})")
                guardado[zid] = []
        aneis.extend(guardado[zid])
    return aneis


def dentro(ponto, anel):
    """Ponto dentro de poligono (lat, lon), por paridade de cruzamentos."""
    y, x = ponto
    c = False
    j = len(anel) - 1
    for i in range(len(anel)):
        yi, xi = anel[i]
        yj, xj = anel[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            c = not c
        j = i
    return c
