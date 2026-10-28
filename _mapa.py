"""Desenha os mapas dos avisos: fundo Esri World Street Map, o trajeto de voces, o trecho ou a area de que o aviso fala, e os
marcadores de inicio e fim com o nome original do lugar.

Uma imagem de 1200 x 900 em JPEG, pensada para chegar legivel no Telegram do
celular: faixa do titulo em cima, mapa no meio, legenda embaixo.
"""
import io
import math
import os
import tempfile
import time
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

UA = "costa-california-clima/1.0 (rafaelmcortopassi@gmail.com)"
W, H = 1200, 900
TOPO, RODAPE = 150, 64
MAPA_H = H - TOPO - RODAPE
# Fundo: Esri World Street Map, sem chave. A CARTO passou a exigir chave e
# carimba "API KEY REQUIRED" em cada bloco (visto em 13/09/2026); o OSM padrao
# e poluido demais para servir de fundo a um aviso. O relevo dourado da Esri
# ainda conversa com a paleta californiana do painel.
FUNDO = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
         "World_Street_Map/MapServer/tile/{z}/{y}/{x}")
CREDITO = "Base: Esri World Street Map (Esri, HERE, Garmin, USGS) · rotas: OpenStreetMap"
TILE = 256
MAXZ, MINZ = 14, 4

PACIFICO = (11, 59, 84)
ROTA = (22, 108, 143)
TRECHO = (210, 75, 54)
INICIO = (47, 125, 74)
FIM = (200, 64, 47)
DOURADO = (242, 169, 59)
POPPY = (232, 115, 15)
PAPEL = (251, 246, 236)
TINTA = (28, 43, 49)
TINTA2 = (94, 109, 114)
PARQUE = (214, 230, 196)     # verde dos parques e reservas no fundo da Esri, ja com o veu
LINHA = (226, 214, 194)

_FONTES = {
    False: ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf"],
    True: ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
}
_cache_fonte = {}


def fonte(tam, negrito=False):
    k = (tam, negrito)
    if k not in _cache_fonte:
        for f in _FONTES[negrito]:
            if os.path.exists(f):
                _cache_fonte[k] = ImageFont.truetype(f, tam)
                break
        else:
            _cache_fonte[k] = ImageFont.load_default(size=tam)
    return _cache_fonte[k]


def nome_fonte():
    for f in _FONTES[False]:
        if os.path.exists(f):
            return os.path.basename(f)
    return "fonte embutida do Pillow"


# ------------------------------------------------------------- projecao

def _mundo(lat, lon, z):
    n = TILE * (2 ** z)
    s = min(max(math.sin(math.radians(lat)), -0.9999), 0.9999)
    return ((lon + 180.0) / 360.0 * n,
            (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n)


def _zoom_fracionado(pontos, larg, alt):
    """(zoom inteiro de onde vem o fundo, fator de reducao entre 0,7 e 1)."""
    xs, ys = zip(*[_mundo(p[0], p[1], 0) for p in pontos])
    sw, sh = max(xs) - min(xs), max(ys) - min(ys)
    ideal = min(math.log2(larg / sw) if sw > 0 else MAXZ,
                math.log2(alt / sh) if sh > 0 else MAXZ)
    ideal = max(MINZ, min(MAXZ, ideal))
    z = math.ceil(ideal - 1e-9)
    f = 2 ** (ideal - z)
    if f < 0.7:
        z, f = math.floor(ideal), 1.0
    return min(z, MAXZ), f


def _escolhe_zoom(pontos, larg, alt):
    lats = [p[0] for p in pontos]
    lons = [p[1] for p in pontos]
    for z in range(MAXZ, MINZ - 1, -1):
        x0, y0 = _mundo(max(lats), min(lons), z)
        x1, y1 = _mundo(min(lats), max(lons), z)
        if (x1 - x0) <= larg and (y1 - y0) <= alt:
            return z
    return MINZ


_disco = os.path.join(tempfile.gettempdir(), "costa_dourada_tiles")


def _bloco(z, x, y):
    n = 2 ** z
    x %= n
    if y < 0 or y >= n:
        return Image.new("RGB", (TILE, TILE), (230, 236, 240))
    arq = os.path.join(_disco, f"esri_{z}_{x}_{y}.img")
    if os.path.exists(arq) and time.time() - os.path.getmtime(arq) < 30 * 86400:
        try:
            return Image.open(arq).convert("RGB")
        except Exception:  # noqa: BLE001
            pass
    url = FUNDO.format(z=z, x=x, y=y)
    for t in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                dados = r.read()
            os.makedirs(_disco, exist_ok=True)
            with open(arq, "wb") as f:
                f.write(dados)
            return Image.open(io.BytesIO(dados)).convert("RGB")
        except Exception:  # noqa: BLE001
            time.sleep(2 * (t + 1))
    return Image.new("RGB", (TILE, TILE), (230, 236, 240))


# ---------------------------------------------------------------- texto

def _texto(d, xy, s, f, cor, esp=0.0):
    """Texto com espacamento entre letras (para as etiquetas em caixa alta)."""
    if not esp:
        d.text(xy, s, font=f, fill=cor)
        return d.textlength(s, font=f)
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=f, fill=cor)
        x += d.textlength(ch, font=f) + esp
    return x - xy[0]


def _larg(d, s, f, esp=0.0):
    return d.textlength(s, font=f) + esp * max(0, len(s) - 1)


def _corta(d, s, f, maximo):
    if d.textlength(s, font=f) <= maximo:
        return s
    while s and d.textlength(s + "…", font=f) > maximo:
        s = s[:-1]
    return s.rstrip() + "…"


# ---------------------------------------------------------------- desenho

def renderiza(spec):
    """spec: kicker, titulo, subtitulo, rotas[{linha, barco}], trechos[linha],
    areas[anel], marcos[{pos, tipo, tag, nome}], enquadra[pontos], legenda[(tipo, texto)]."""
    enquadra = [p for p in spec.get("enquadra") or [] if p]
    if not enquadra:
        for r in spec.get("rotas", []):
            enquadra += r["linha"]
    # um ponto sozinho abria no zoom maximo, so estrada e mar, sem uma cidade
    # para o leitor se achar (Rocky Creek Bridge, 13/09/2026)
    la0, la1 = min(p[0] for p in enquadra), max(p[0] for p in enquadra)
    lo0, lo1 = min(p[1] for p in enquadra), max(p[1] for p in enquadra)
    if la1 - la0 < 0.14:
        c = (la0 + la1) / 2
        enquadra = enquadra + [[c - 0.07, lo0], [c + 0.07, lo0]]
    if lo1 - lo0 < 0.18:
        c = (lo0 + lo1) / 2
        enquadra = enquadra + [[la0, c - 0.09], [la0, c + 0.09]]
    margem_x, margem_y = 150, 70
    z, f = _zoom_fracionado(enquadra, W - 2 * margem_x, MAPA_H - 2 * margem_y)
    xs, ys = zip(*[_mundo(p[0], p[1], z) for p in enquadra])
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    wz, hz = W / f, MAPA_H / f          # janela no zoom inteiro, antes de reduzir
    ox, oy = cx - wz / 2, cy - hz / 2

    def px(p, k=1):
        x, y = _mundo(p[0], p[1], z)
        return ((x - ox) * f * k, (y - oy) * f * k)

    # ---- fundo: compoe no zoom inteiro de cima e reduz ate o enquadramento
    # exato. Com zoom so em potencias de 2, um trajeto longo ocupava metade do
    # quadro; reduzir no maximo 30% ainda deixa os nomes do fundo legiveis.
    mapa = Image.new("RGB", (math.ceil(wz), math.ceil(hz)), (230, 236, 240))
    for tx in range(int(ox // TILE), int((ox + wz) // TILE) + 1):
        for ty in range(int(oy // TILE), int((oy + hz) // TILE) + 1):
            mapa.paste(_bloco(z, tx, ty), (int(tx * TILE - ox), int(ty * TILE - oy)))
    if mapa.size != (W, MAPA_H):
        mapa = mapa.resize((W, MAPA_H), Image.LANCZOS)
    veu = Image.new("RGB", mapa.size, (255, 255, 255))
    mapa = Image.blend(mapa, veu, 0.18)

    # ---- camadas vetoriais a 2x e reduzidas: o Pillow nao suaviza linha
    K = 2
    cam = Image.new("RGBA", (W * K, MAPA_H * K), (0, 0, 0, 0))
    dc = ImageDraw.Draw(cam)

    for anel in spec.get("areas", []):
        pts = [px(p, K) for p in anel]
        if len(pts) > 2:
            dc.polygon(pts, fill=DOURADO + (78,))
    for anel in spec.get("areas", []):
        pts = [px(p, K) for p in anel]
        if len(pts) > 2:
            dc.line(pts + [pts[0]], fill=(201, 134, 28, 230), width=3 * K, joint="curve")

    for r in spec.get("rotas", []):
        pts = [px(p, K) for p in r["linha"]]
        if len(pts) < 2:
            continue
        if r.get("barco"):
            _tracejado(dc, pts, ROTA + (255,), 5 * K, 16 * K, 11 * K)
        else:
            dc.line(pts, fill=(255, 255, 255, 235), width=12 * K, joint="curve")
            dc.line(pts, fill=ROTA + (255,), width=7 * K, joint="curve")

    for linha in spec.get("trechos", []):
        pts = [px(p, K) for p in linha]
        if len(pts) >= 2:
            dc.line(pts, fill=(255, 255, 255, 245), width=17 * K, joint="curve")
            dc.line(pts, fill=TRECHO + (255,), width=11 * K, joint="curve")

    cam = cam.resize((W, MAPA_H), Image.LANCZOS)
    mapa = Image.alpha_composite(mapa.convert("RGBA"), cam)

    # ---- marcadores e rotulos, a 1x, com desvio de colisao simples
    d = ImageDraw.Draw(mapa)
    ocupado = []
    evitar = []
    for r in spec.get("rotas", []):
        evitar += [px(q) for q in r["linha"]]
    for linha in spec.get("trechos", []):
        evitar += [px(q) for q in linha] * 3      # cobrir o trecho afetado pesa mais
    marcos = spec.get("marcos", [])
    # os de inicio e fim primeiro: sao eles que o leitor procura
    ordem = sorted(marcos, key=lambda m: {"inicio": 0, "fim": 1, "ponto": 2}.get(m["tipo"], 3))
    for m in ordem:
        x, y = px(m["pos"])
        if m["tipo"] == "parada":
            d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(255, 255, 255), outline=ROTA, width=4)
            ocupado.append((x - 9, y - 9, x + 9, y + 9))
        else:
            cor = {"inicio": INICIO, "fim": FIM}.get(m["tipo"], TRECHO)
            d.ellipse((x - 17, y - 17, x + 17, y + 17), fill=(255, 255, 255))
            d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=cor)
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255))
            ocupado.append((x - 19, y - 19, x + 19, y + 19))
    for m in ordem:
        x, y = px(m["pos"])
        if m["tipo"] == "parada":
            _rotulo_pequeno(d, x, y, m["nome"], ocupado, evitar)
        else:
            cor = {"inicio": INICIO, "fim": FIM}.get(m["tipo"], TRECHO)
            _rotulo(d, x, y, m.get("tag", ""), m["nome"], cor, ocupado, evitar)

    # visao geral no canto e a faixa do dia: so nos avisos que cruzam o trajeto
    if spec.get("trechos") and spec.get("faixa"):
        _inset(mapa, spec, enquadra_principal=(ox, oy, wz, hz, z))
    if spec.get("faixa"):
        _faixa_linear(mapa, spec["faixa"])

    # ---- montagem final
    tela = Image.new("RGB", (W, H), PAPEL)
    tela.paste(mapa.convert("RGB"), (0, TOPO))
    _cabecalho(tela, spec)
    _legenda(tela, spec.get("legenda", []))
    buf = io.BytesIO()
    tela.save(buf, "JPEG", quality=88, optimize=True, progressive=True)
    return buf.getvalue()


def _inset(mapa, spec, enquadra_principal):
    """Mapinha no canto com o trajeto inteiro e a area inteira do aviso, e um
    retangulo mostrando onde o mapa grande esta."""
    iw, ih, m = 300, 225, 16
    x0, y0 = W - iw - m, m
    pts = [p for r in spec.get("rotas", []) for p in r["linha"]] + \
          [p for a in spec.get("areas", []) for p in a]
    la0, la1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lo0, lo1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = math.cos(math.radians((la0 + la1) / 2))
    esc = min((iw - 24) / max((lo1 - lo0) * k, 1e-6), (ih - 24) / max(la1 - la0, 1e-6))
    cx, cy = (lo0 + lo1) / 2, (la0 + la1) / 2

    def q(p, K=2):
        return ((iw / 2 + (p[1] - cx) * k * esc) * K, (ih / 2 - (p[0] - cy) * esc) * K)

    K = 2
    img = Image.new("RGBA", (iw * K, ih * K), (233, 240, 243, 255))
    d = ImageDraw.Draw(img)
    for a in spec.get("areas", []):
        if len(a) > 2:
            d.polygon([q(p) for p in a], fill=(247, 221, 170, 255), outline=(201, 134, 28, 255))
    for r in spec.get("rotas", []):
        if len(r["linha"]) > 1:
            d.line([q(p) for p in r["linha"]], fill=ROTA + (255,), width=3 * K, joint="curve")
    for t in spec.get("trechos", []):
        if len(t) > 1:
            d.line([q(p) for p in t], fill=TRECHO + (255,), width=6 * K, joint="curve")
    # retangulo do mapa grande, convertido de pixels do mundo para lat/lon
    ox, oy, wz, hz, z = enquadra_principal

    def latlon(x, y):
        n = 2 ** z * TILE
        lon = x / n * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
        return [lat, lon]
    a, b = q(latlon(ox, oy)), q(latlon(ox + wz, oy + hz))
    d.rectangle((a[0], a[1], b[0], b[1]), outline=TINTA + (255,), width=2 * K)
    img = img.resize((iw, ih), Image.LANCZOS)
    dd = ImageDraw.Draw(mapa)
    dd.rounded_rectangle((x0 - 3, y0 - 3, x0 + iw + 3, y0 + ih + 3), radius=8, fill=(255, 253, 248),
                         outline=(216, 204, 184))
    mapa.paste(img.convert("RGB"), (x0, y0))
    _texto(dd, (x0 + 8, y0 + ih - 20), "VISÃO GERAL", fonte(12, True), TINTA2, 1.4)


def _faixa_linear(mapa, fx):
    """Barra com o dia inteiro de ponta a ponta e o pedaco dentro do aviso
    pintado: mostra de cara se e parcial ou total."""
    d = ImageDraw.Draw(mapa)
    bx0, bx1, h = 40, W - 40, 92
    by = MAPA_H - h - 14
    d.rounded_rectangle((bx0 - 16, by, bx1 + 16, by + h), radius=10, fill=(255, 253, 248),
                        outline=(216, 204, 184))
    ly = by + 50
    tot = max(fx["total"], 1)
    d.line((bx0, ly, bx1, ly), fill=ROTA, width=8)
    xs = []
    for ini, fim in fx.get("pedacos") or [(fx["ini"], fx["fim"])]:
        xa = bx0 + (bx1 - bx0) * ini / tot
        xb = max(bx0 + (bx1 - bx0) * fim / tot, xa + 6)
        d.line((xa, ly, xb, ly), fill=TRECHO, width=16)
        xs += [xa, xb]
    xa, xb = min(xs), max(xs)
    for x in (bx0, bx1):
        d.ellipse((x - 7, ly - 7, x + 7, ly + 7), fill=(255, 255, 255), outline=ROTA, width=3)
    f, fb = fonte(15), fonte(15, True)
    _texto(d, (bx0, by + 10), ("SEU DIA " + fx["dia"]).upper(), fonte(12, True), TINTA2, 1.4)
    d.text((bx0, ly + 12), fx["de"], font=fb, fill=TINTA)
    d.text((bx1 - d.textlength(fx["ate"], font=fb), ly + 12), fx["ate"], font=fb, fill=TINTA)
    txt = f"{max(1, round(fx.get('km', fx['fim'] - fx['ini'])))} de {round(tot)} km dentro do aviso"
    tx = min(max((xa + xb) / 2 - d.textlength(txt, font=fb) / 2, bx0 + 120), bx1 - 330)
    d.text((tx, by + 8), txt, font=fb, fill=TRECHO)


def _tracejado(d, pts, cor, larg, traco, vao):
    resto, desenhando = traco, True
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        pos = 0.0
        while seg - pos > 0:
            passo = min(resto, seg - pos)
            if desenhando:
                a = pos / seg
                b = (pos + passo) / seg
                d.line((x0 + (x1 - x0) * a, y0 + (y1 - y0) * a,
                        x0 + (x1 - x0) * b, y0 + (y1 - y0) * b), fill=cor, width=larg)
            pos += passo
            resto -= passo
            if resto <= 0:
                desenhando = not desenhando
                resto = traco if desenhando else vao


def _cabe(caixa, ocupado):
    x0, y0, x1, y1 = caixa
    if x0 < 6 or y0 < 6 or x1 > W - 6 or y1 > MAPA_H - 6:
        return False
    return all(x1 < a or x0 > c or y1 < b or y0 > e for (a, b, c, e) in ocupado)


def _escolhe(cands, ocupado, evitar):
    """A posicao que cabe, nao pisa em outro rotulo e cobre menos rota. Empate
    fica com a ordem de preferencia."""
    melhor, nota = None, None
    for i, caixa in enumerate(cands):
        if not _cabe(caixa, ocupado):
            continue
        x0, y0, x1, y1 = caixa
        cobre = sum(1 for (a, b) in evitar if x0 - 6 <= a <= x1 + 6 and y0 - 6 <= b <= y1 + 6)
        n = cobre * 10 + i
        if nota is None or n < nota:
            melhor, nota = caixa, n
    return melhor


def _rotulo(d, x, y, tag, nome, cor, ocupado, evitar=()):
    ft, fn = fonte(13, True), fonte(21, True)
    nome = _corta(d, nome, fn, 330)
    lw = max(_larg(d, tag, ft, 1.4), d.textlength(nome, font=fn)) + 34
    lh = 58
    cands = [(x + dx, y + dy, x + dx + lw, y + dy + lh) for dx, dy in (
        (26, -lh - 8), (26, 8), (-lw - 26, -lh - 8), (-lw - 26, 8),
        (26, -lh / 2), (-lw - 26, -lh / 2), (-lw / 2, -lh - 30), (-lw / 2, 30),
        (60, -lh - 50), (-lw - 60, -lh - 50), (60, 50), (-lw - 60, 50))]
    caixa = _escolhe(cands, ocupado, evitar) or cands[0]
    ancora = (min(max(x, caixa[0]), caixa[2]), min(max(y, caixa[1]), caixa[3]))
    d.line((x, y, ancora[0], ancora[1]), fill=cor, width=3)
    d.rounded_rectangle((caixa[0] + 2, caixa[1] + 3, caixa[2] + 2, caixa[3] + 3),
                        radius=9, fill=(28, 43, 49))
    d.rounded_rectangle(caixa, radius=9, fill=(255, 253, 248), outline=(216, 204, 184), width=1)
    d.rounded_rectangle((caixa[0], caixa[1], caixa[0] + 7, caixa[3]), radius=4, fill=cor)
    _texto(d, (caixa[0] + 18, caixa[1] + 8), tag, ft, cor, 1.4)
    d.text((caixa[0] + 18, caixa[1] + 25), nome, font=fn, fill=TINTA)
    ocupado.append(caixa)


def _rotulo_pequeno(d, x, y, nome, ocupado, evitar=()):
    f = fonte(16, True)
    lw, lh = d.textlength(nome, font=f) + 18, 28
    cands = [(x + dx, y + dy, x + dx + lw, y + dy + lh) for dx, dy in (
        (12, -lh - 4), (12, 6), (-lw - 12, -lh - 4), (-lw - 12, 6),
        (14, -lh / 2), (-lw - 14, -lh / 2))]
    caixa = _escolhe(cands, ocupado, evitar)
    if caixa is None:
        return      # sem espaco: melhor nao rotular que rotular por cima de outro
    d.rounded_rectangle(caixa, radius=14, fill=(255, 253, 248), outline=ROTA, width=2)
    d.text((caixa[0] + 9, caixa[1] + 4), nome, font=f, fill=PACIFICO)
    ocupado.append(caixa)


def _cabecalho(tela, spec):
    d = ImageDraw.Draw(tela)
    d.rectangle((0, 0, W, TOPO), fill=PACIFICO)
    for i in range(W):
        t = i / (W - 1)
        c = tuple(int(POPPY[k] + (DOURADO[k] - POPPY[k]) * t) for k in range(3))
        d.line((i, TOPO - 6, i, TOPO), fill=c)
    _texto(d, (38, 20), (spec.get("kicker") or "").upper(), fonte(15, True), DOURADO, 2.2)
    d.text((38, 44), _corta(d, spec.get("titulo", ""), fonte(34, True), W - 76),
           font=fonte(34, True), fill=(255, 248, 236))
    # subtitulo em ate duas linhas: e nele que esta o que o aviso quer dizer
    f = fonte(19)
    palavras, linhas, atual = (spec.get("subtitulo") or "").split(), [], ""
    for w in palavras:
        teste = (atual + " " + w).strip()
        if d.textlength(teste, font=f) <= W - 76 or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = w
    if atual:
        linhas.append(atual)
    if len(linhas) > 2:
        linhas = [linhas[0], _corta(d, " ".join(linhas[1:]), f, W - 76)]
    for i, ln in enumerate(linhas):
        d.text((38, 86 + i * 25), ln, font=f, fill=(191, 217, 228))


def _legenda(tela, itens):
    d = ImageDraw.Draw(tela)
    y0 = H - RODAPE
    d.rectangle((0, y0, W, H), fill=PAPEL)
    d.line((0, y0, W, y0), fill=LINHA, width=2)
    f = fonte(17)
    x, cy = 38, y0 + RODAPE / 2
    for tipo, txt in itens:
        if tipo == "rota":
            d.line((x, cy, x + 34, cy), fill=(255, 255, 255), width=10)
            d.line((x, cy, x + 34, cy), fill=ROTA, width=6)
            x += 44
        elif tipo == "barco":
            for k in range(3):
                d.line((x + k * 13, cy, x + k * 13 + 8, cy), fill=ROTA, width=5)
            x += 44
        elif tipo == "trecho":
            d.line((x, cy, x + 34, cy), fill=TRECHO, width=10)
            x += 44
        elif tipo == "parque":
            d.rectangle((x, cy - 10, x + 30, cy + 10), fill=PARQUE, outline=(150, 180, 130), width=1)
            x += 40
        elif tipo == "area":
            d.rectangle((x, cy - 10, x + 30, cy + 10), fill=(247, 221, 170), outline=(201, 134, 28), width=2)
            x += 40
        elif tipo in ("inicio", "fim", "ponto"):
            cor = {"inicio": INICIO, "fim": FIM}.get(tipo, TRECHO)
            d.ellipse((x, cy - 10, x + 20, cy + 10), fill=cor, outline=(255, 255, 255), width=2)
            x += 28
        elif tipo == "parada":
            d.ellipse((x, cy - 7, x + 14, cy + 7), fill=(255, 255, 255), outline=ROTA, width=3)
            x += 24
        d.text((x, cy - 11), txt, font=f, fill=TINTA)
        x += d.textlength(txt, font=f) + 30
    fc = fonte(13)
    for cred in (CREDITO, "Base: Esri · rotas: OpenStreetMap", "© Esri · OSM"):
        if W - 38 - d.textlength(cred, font=fc) > x - 10:
            break
    d.text((W - 38 - d.textlength(cred, font=fc), cy - 9), cred, font=fc, fill=TINTA2)
