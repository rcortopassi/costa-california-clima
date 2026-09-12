#!/usr/bin/env python3
"""Costa Dourada - monitor do clima da rota Los Angeles <-> Carmel.

Roda no GitHub Actions de 6 em 6 horas, publica a pagina no PythonAnywhere e
manda o resumo por Telegram/ntfy. So stdlib.

Variaveis de ambiente:
  PA_TOKEN        - token da API do PythonAnywhere (o mesmo de painel/.env)
  PA_USER         - usuario do PythonAnywhere (default: rafaelcortopassi)
  NTFY_TOPIC      - topico secreto do ntfy.sh
  TELEGRAM_TOKEN  - bot do Telegram (@dfcarvalho_bot)
  TELEGRAM_CHAT   - chat de destino

Fontes (todas sem chave de API):
  Open-Meteo          previsao horaria e diaria
  api.weather.gov     avisos oficiais do NWS (exige User-Agent)
  roads.dot.ca.gov    condicao das rodovias, Caltrans
  cpc.ncep.noaa.gov   boletim ENSO (El Nino)
"""

import html as html_mod
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

AQUI = Path(__file__).resolve().parent
STATE = AQUI / "state" / "state.json"
HIST = AQUI / "state" / "history.json"

def _carrega_env_local():
    """Le .env.local quando existir, sem sobrepor variavel ja definida. No
    Actions os valores vem dos secrets e o arquivo nem existe."""
    f = AQUI / ".env.local"
    if not f.exists():
        return
    for linha in f.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_carrega_env_local()

PA_TOKEN = os.environ.get("PA_TOKEN", "")
PA_USER = os.environ.get("PA_USER", "rafaelcortopassi")
PA_API = "https://www.pythonanywhere.com"
PA_DIR = "california"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT", "")

LINK_SITE = f"https://{PA_USER}.pythonanywhere.com/{PA_DIR}/"
UA = "costa-california-clima/1.0 (rafaelmcortopassi@gmail.com)"

PACIFICO = timezone(timedelta(hours=-8))   # PST, sem horario de verao em dezembro
BRT = timezone(timedelta(hours=-3))

# ---------------------------------------------------------------- a viagem
# Datas reais da confirmacao de reserva (lua de mel, 20/12/2026 a 06/01/2027).
VIAGEM = {
    "carro_lax": "2026-12-22T09:00",       # Alamo, terminal do LAX
    "devolve_lax": "2026-12-24T15:00",
    "voo_honolulu": "2026-12-24T17:43",
    "carro_oahu": "2026-12-27T10:00",      # centro de Honolulu
    "devolve_oahu": "2026-12-28T10:00",    # aeroporto HNL
    "carro_bi": "2026-12-28T16:00",        # Jeep Wrangler 4x4, aeroporto de Hilo
    "devolve_bi": "2027-01-04T14:00",      # aeroporto de Kona
}

REGIOES = [
    ("ca", "Costa da Califórnia", "America/Los_Angeles", -8),
    ("oahu", "Oahu", "Pacific/Honolulu", -10),
    ("bi", "Big Island", "Pacific/Honolulu", -10),
]

# id, nome, lat, lon, elevacao forcada (None = modelo decide), regiao, papel,
# normal climatologica da janela daquela regiao, mar (pede dado de onda)
PONTOS = [
    # ---- Califórnia: 21 a 24 de dezembro, normais 1995-2025
    ("lax", "Los Angeles", 33.9425, -118.4081, 40, "ca", "Hotel e aeroporto",
     {"tmax": 17.3, "tmin": 7.3, "mm": 3.5, "pct": 24, "forte": 15}, False),
    ("malibu", "Malibu / El Matador", 34.0387, -118.8747, 10, "ca", "Primeira parada da PCH",
     {"tmax": 17.3, "tmin": 7.3, "mm": 3.5, "pct": 24, "forte": 15}, False),
    ("sb", "Santa Barbara", 34.4208, -119.6982, 15, "ca", "Almoço do dia 22",
     {"tmax": 17.6, "tmin": 8.3, "mm": 4.0, "pct": 27, "forte": 15}, False),
    ("pismo", "Pismo Beach", 35.1428, -120.6413, 15, "ca", "Bosque das monarcas",
     {"tmax": 15.7, "tmin": 8.1, "mm": 3.6, "pct": 31, "forte": 19}, False),
    ("paso", "Paso Robles", 35.6266, -120.6910, None, "ca", "US-101 pelo interior",
     {"tmax": 15.7, "tmin": 8.1, "mm": 3.6, "pct": 31, "forte": 19}, False),
    ("salinas", "Salinas", 36.6777, -121.6555, None, "ca", "US-101, vale da neblina",
     {"tmax": 13.9, "tmin": 8.8, "mm": 2.8, "pct": 35, "forte": 18}, False),
    ("pg", "Pacific Grove", 36.6177, -121.9166, 15, "ca", "Pousada, 2 noites",
     {"tmax": 13.9, "tmin": 8.8, "mm": 2.8, "pct": 35, "forte": 18}, False),
    ("carmel", "Carmel-by-the-Sea", 36.5552, -121.9233, 20, "ca", "Vilarejo e Point Lobos",
     {"tmax": 13.9, "tmin": 8.8, "mm": 2.8, "pct": 35, "forte": 18}, False),
    ("bixby", "Bixby Bridge", 36.3719, -121.9024, 80, "ca", "Big Sur, ida e volta de Carmel",
     {"tmax": 13.9, "tmin": 8.8, "mm": 2.8, "pct": 35, "forte": 18}, False),

    # ---- Oahu: janela 26/12 a 05/01, normais 2000-2025
    ("waikiki", "Waikiki", 21.2760, -157.8270, 3, "oahu", "Hotel, 4 noites",
     {"tmax": 24.3, "tmin": 21.6, "mm": 2.1, "pct": 28, "forte": 8}, True),
    ("diamond", "Diamond Head", 21.2620, -157.8060, 150, "oahu", "Trilha do dia 26, abre 6h",
     {"tmax": 24.3, "tmin": 21.6, "mm": 2.1, "pct": 28, "forte": 8}, False),
    ("hanauma", "Hanauma Bay", 21.2690, -157.6940, 5, "oahu", "Só domingo 27, reserva 2 dias antes",
     {"tmax": 24.3, "tmin": 21.6, "mm": 2.1, "pct": 28, "forte": 8}, True),
    ("makapuu", "Makapuʻu", 21.3100, -157.6500, 60, "oahu", "Mirante do lado leste",
     {"tmax": 24.0, "tmin": 20.8, "mm": 2.5, "pct": 40, "forte": 10}, False),
    ("lanikai", "Kailua e Lanikai", 21.3930, -157.7350, 5, "oahu", "Água clara do barlavento",
     {"tmax": 24.0, "tmin": 20.8, "mm": 2.5, "pct": 40, "forte": 10}, True),
    ("kualoa", "Kualoa", 21.5200, -157.8380, 10, "oahu", "Costa de barlavento",
     {"tmax": 24.0, "tmin": 20.8, "mm": 2.5, "pct": 40, "forte": 10}, False),
    ("northshore", "North Shore", 21.6400, -158.0650, 10, "oahu", "Ondas gigantes do inverno",
     {"tmax": 24.0, "tmin": 20.2, "mm": 1.9, "pct": 45, "forte": 11}, True),
    ("haleiwa", "Haleʻiwa", 21.5930, -158.1030, 10, "oahu", "Food trucks do almoço",
     {"tmax": 24.0, "tmin": 20.2, "mm": 1.9, "pct": 45, "forte": 11}, False),

    # ---- Big Island
    ("hilo", "Hilo", 19.7070, -155.0850, 12, "bi", "Hotel, 3 noites",
     {"tmax": 23.1, "tmin": 17.7, "mm": 5.0, "pct": 72, "forte": 29}, False),
    ("kilauea", "Kilauea / HVNP", 19.4200, -155.2870, 1150, "bi", "Cratera e Chain of Craters",
     {"tmax": 19.4, "tmin": 13.7, "mm": 4.4, "pct": 59, "forte": 21}, False),
    ("mk_vis", "Mauna Kea, base (VIS)", 19.7600, -155.4560, 2804, "bi",
     "Aclimatação obrigatória, 9.200 pés",
     {"tmax": 12.0, "tmin": 3.0, "mm": 2.6, "pct": 35, "forte": 10}, False),
    ("mk_cume", "Mauna Kea, cume", 19.8207, -155.4681, 4207, "bi",
     "13.796 pés. Só com 4x4 e luz do dia na subida",
     {"tmax": 5.0, "tmin": -3.8, "mm": 2.3, "pct": 33, "forte": 9}, False),
    ("akaka", "Akaka Falls", 19.8550, -155.1520, 400, "bi", "Cachoeira, trilha curta",
     {"tmax": 23.1, "tmin": 17.7, "mm": 5.0, "pct": 72, "forte": 29}, False),
    ("waipio", "Waipiʻo", 20.1170, -155.5880, 300, "bi", "Mirante do vale",
     {"tmax": 23.1, "tmin": 17.7, "mm": 5.0, "pct": 72, "forte": 29}, False),
    ("punaluu", "Punaluʻu", 19.1360, -155.5050, 5, "bi", "Areia preta, travessia do dia 31",
     {"tmax": 22.5, "tmin": 18.0, "mm": 3.2, "pct": 55, "forte": 18}, False),
    ("kona", "Kailua-Kona / Keauhou", 19.5650, -155.9650, 10, "bi", "Resort, 4 noites",
     {"tmax": 27.0, "tmin": 20.0, "mm": 1.8, "pct": 40, "forte": 14}, True),
    ("kealakekua", "Kealakekua Bay", 19.4750, -155.9250, 5, "bi", "Snorkel do Capitão Cook",
     {"tmax": 27.0, "tmin": 20.0, "mm": 1.8, "pct": 40, "forte": 14}, True),
    ("hapuna", "Hāpuna Beach", 19.9930, -155.8250, 5, "bi", "Praia do dia livre",
     {"tmax": 27.0, "tmin": 20.0, "mm": 1.8, "pct": 40, "forte": 14}, True),
]

# dia, regiao, titulo, resumo, pontos (o ultimo e o destino), dirige
ETAPAS = [
    ("2026-12-21", "ca", "Chegada a Los Angeles",
     "Pouso às 18h10, transfer do Holiday Inn. Sem carro.", ["lax"], False),
    ("2026-12-22", "ca", "Los Angeles a Pacific Grove",
     "Carro às 9h no LAX. PCH até Malibu, 101 pela orla até Santa Barbara, "
     "101 pelo interior até Pacific Grove. Recepção fecha às 18h.",
     ["lax", "malibu", "sb", "pismo", "paso", "salinas", "pg"], True),
    ("2026-12-23", "ca", "Península de Monterey",
     "Aquário, Cannery Row, 17-Mile Drive, Carmel, Point Lobos. "
     "Sobra tempo para uma ida e volta até Bixby Bridge.",
     ["pg", "carmel", "bixby"], True),
    ("2026-12-24", "ca", "Pacific Grove a Los Angeles",
     "Saída às 8h. Carro de volta no LAX às 15h, voo para Honolulu às 17h43. "
     "Sem folga para desvio cênico.",
     ["pg", "salinas", "paso", "pismo", "sb", "lax"], True),
    ("2026-12-25", "oahu", "Natal em Waikiki",
     "Dia todo a pé pela orla. Quase tudo fechado na ilha.", ["waikiki"], False),
    ("2026-12-26", "oahu", "Diamond Head e Pearl Harbor",
     "Trilha no começo da manhã, Pearl Harbor depois. Sem carro.",
     ["diamond", "waikiki"], False),
    ("2026-12-27", "oahu", "Volta a Oahu de carro",
     "Carro às 10h no centro. Único dia com carro na ilha: Hanauma, costa leste, "
     "Kualoa e North Shore.",
     ["hanauma", "makapuu", "lanikai", "kualoa", "northshore", "haleiwa"], True),
    ("2026-12-28", "bi", "Oahu a Hilo",
     "Devolução às 10h no HNL. Jeep 4x4 às 16h no aeroporto de Hilo.",
     ["hilo"], True),
    ("2026-12-29", "bi", "Hawaii Volcanoes National Park",
     "Crater Rim, Nāhuku, Chain of Craters. Voltar ao anoitecer se houver "
     "atividade na cratera.", ["kilauea"], True),
    ("2026-12-30", "bi", "Costa Hamakua e Mauna Kea",
     "Jardim tropical, Akaka Falls, mirante do Waipiʻo. À noite, o cume do "
     "Mauna Kea para o poente e as estrelas.",
     ["akaka", "waipio", "mk_vis", "mk_cume"], True),
    ("2026-12-31", "bi", "Hilo a Kona pelo sul",
     "Travessia pelo sul com parada em Punaluʻu. Check-in às 16h, réveillon "
     "no resort.", ["punaluu", "kona"], True),
    ("2027-01-01", "bi", "Primeiro dia do ano em Keauhou",
     "Dia de resort, sem despertador.", ["kona"], False),
    ("2027-01-02", "bi", "Mar e vida marinha em Kona",
     "Catamarã à Kealakekua Bay de manhã, snorkel noturno com arraias-manta.",
     ["kealakekua", "kona"], False),
    ("2027-01-03", "bi", "Praias da costa oeste",
     "Magic Sands, Kua Bay ou Hāpuna. Ritmo livre.", ["hapuna", "kona"], True),
    ("2027-01-04", "ca", "Big Island a Los Angeles",
     "Carro de volta às 14h em Kona. Transfer do hotel no LAX.", ["kona", "lax"], True),
    ("2027-01-05", "ca", "Último dia em Los Angeles",
     "Dia livre a pé ou de aplicativo. Saída para o aeroporto às 20h.",
     ["lax"], False),
]

# Condados e lugares que importam para a rota da Califórnia. O boletim da
# Caltrans traz o estado inteiro; sem este filtro a pagina grita por causa de
# Fort Bragg e Point Reyes, a centenas de quilometros do roteiro.
CONDADOS_ROTA = ("monterey", "san luis obispo", "santa barbara", "ventura",
                 "los angeles", "big sur", "carmel", "salinas", "santa cruz",
                 "san benito", "cambria", "morro", "gaviota", "lompoc")

# Para casar os avisos do NWS (que vem por zona) com cada regiao.
ZONAS_NWS = {
    "ca": ("monterey", "santa cruz", "san benito", "san luis obispo", "santa barbara",
           "ventura", "los angeles", "big sur", "salinas", "carmel", "santa lucia",
           "cuyama", "santa ynez", "point conception", "malibu", "catalina"),
    "oahu": ("oahu", "honolulu", "koolau", "waianae", "kauai channel"),
    "bi": ("hawaii", "kona", "hilo", "kohala", "mauna", "volcano", "big island",
           "haleakala", "south point", "puna", "kau"),
}

HORAS_FRESCOR = 5          # guarda de frescor: pula a rodada se acabou de publicar
DIAS_GRADE = 7             # colunas da grade windguru


# ---------------------------------------------------------------- rede

def fetch(url, ua=UA, tentativas=3, timeout=45, accept=None):
    cab = {"User-Agent": ua}
    if accept:
        cab["Accept"] = accept
    ultimo = None
    for t in range(1, tentativas + 1):
        try:
            with urlopen(Request(url, headers=cab), timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            ultimo = e
            if t < tentativas:
                time.sleep(4 * t)
    raise RuntimeError(f"{url}: {ultimo}")


def fetch_json(url, **kw):
    return json.loads(fetch(url, **kw))


# ---------------------------------------------------------------- previsao

HORARIAS = ("temperature_2m,precipitation,precipitation_probability,snowfall,"
            "wind_speed_10m,wind_gusts_10m,wind_direction_10m,cloud_cover,visibility,"
            "freezing_level_height,relative_humidity_2m")
DIARIAS = ("temperature_2m_max,temperature_2m_min,precipitation_sum,"
           "precipitation_probability_max,wind_gusts_10m_max,sunrise,sunset")


def previsoes_lote(pontos):
    """UMA chamada para todos os pontos. O Open-Meteo aceita lista de
    coordenadas e devolve lista na mesma ordem; a elevacao tambem e por ponto,
    o que importa muito numa ilha vulcanica: sem forcar, o modelo escolhe o
    ponto de grade encosta acima e o cume do Mauna Kea vira uma colina."""
    fusos = {r[0]: r[2] for r in REGIOES}
    out = {}
    for reg, tz in sorted({(p[5], fusos[p[5]]) for p in pontos}):
        grupo = [p for p in pontos if p[5] == reg]
        lats = ",".join(str(p[2]) for p in grupo)
        lons = ",".join(str(p[3]) for p in grupo)
        elev = ",".join(("nan" if p[4] is None else str(p[4])) for p in grupo)
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lats}&longitude={lons}"
               f"&elevation={elev}&hourly={HORARIAS}&daily={DIARIAS}"
               f"&timezone={quote(tz)}&forecast_days=16&wind_speed_unit=kn")
        d = fetch_json(url, timeout=90)
        blocos = d if isinstance(d, list) else [d]
        if len(blocos) != len(grupo):
            raise RuntimeError(f"{reg}: pedi {len(grupo)} pontos, voltaram {len(blocos)}")
        for p, b in zip(grupo, blocos):
            out[p[0]] = {"hourly": b["hourly"], "daily": b["daily"],
                         "elev": b.get("elevation")}
        print(f"previsao {reg}: {len(grupo)} pontos")
    return out


def mar_lote(pontos):
    """Altura de onda para os pontos de mar. Decide snorkel e diz se o North
    Shore esta no modo espetaculo (ondas grandes) ou no modo praia."""
    mar = [p for p in pontos if p[8]]
    if not mar:
        return {}
    fusos = {r[0]: r[2] for r in REGIOES}
    out = {}
    for reg, tz in sorted({(p[5], fusos[p[5]]) for p in mar}):
        grupo = [p for p in mar if p[5] == reg]
        url = ("https://marine-api.open-meteo.com/v1/marine?latitude="
               + ",".join(str(p[2]) for p in grupo)
               + "&longitude=" + ",".join(str(p[3]) for p in grupo)
               + "&hourly=wave_height,swell_wave_height,swell_wave_period"
               + f"&timezone={quote(tz)}&forecast_days=16")
        try:
            d = fetch_json(url, timeout=90)
        except Exception as e:  # noqa: BLE001 - onda e complemento
            print(f"aviso: dados de onda em {reg} falharam ({e})")
            continue
        blocos = d if isinstance(d, list) else [d]
        for p, b in zip(grupo, blocos):
            out[p[0]] = b.get("hourly", {})
        print(f"ondas {reg}: {len(grupo)} pontos")
    return out


def alertas_por_area(areas=("CA", "HI")):
    """Avisos ativos do NWS por estado, numa chamada cada, e depois atribuidos
    a regiao pelo texto da area afetada. Consultar ponto por ponto seriam 27
    chamadas para a mesma informacao."""
    out = []
    for a in areas:
        try:
            d = fetch_json(f"https://api.weather.gov/alerts/active?area={a}",
                           accept="application/geo+json")
        except Exception as e:  # noqa: BLE001
            print(f"aviso: NWS area {a} falhou ({e})")
            continue
        for f in d.get("features", []):
            p = f.get("properties", {})
            onde = (p.get("areaDesc") or "").lower()
            regs = [r for r, chaves in ZONAS_NWS.items()
                    if any(c in onde for c in chaves)]
            if not regs:
                continue        # aviso em outra parte do estado: nao e nosso
            out.append({
                "evento": p.get("event", ""),
                "severidade": p.get("severity", ""),
                "manchete": (p.get("headline") or "").strip(),
                "descricao": (p.get("description") or "").strip()[:900],
                "onde": (p.get("areaDesc") or "")[:110],
                "regioes": regs,
                "fim": p.get("ends") or p.get("expires") or "",
                "id": p.get("id", ""),
            })
    print(f"avisos do NWS na rota: {len(out)}")
    return out


def kilauea_status():
    """Cor e nivel do Kilauea pela API HANS do USGS. Ausente da lista de
    vulcoes elevados significa GREEN/NORMAL."""
    try:
        d = fetch_json("https://volcanoes.usgs.gov/hans-public/api/volcano/"
                       "getElevatedVolcanoes")
    except Exception as e:  # noqa: BLE001
        print(f"aviso: USGS falhou ({e})")
        return None
    for v in d if isinstance(d, list) else []:
        if str(v.get("vnum")) == "332010":
            return {"cor": v.get("color_code", ""), "nivel": v.get("alert_level", ""),
                    "aviso": v.get("notice_identifier", ""),
                    "quando": v.get("sent_utc", "")}
    return {"cor": "GREEN", "nivel": "NORMAL", "aviso": "", "quando": ""}


# ---------------------------------------------------------------- estradas

def _limpa(t):
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", html_mod.unescape(t)).strip()


def estradas(numeros=("1", "101")):
    """Boletim da Caltrans por rodovia, ja recortado nas areas Southern e
    Central California e classificado pelo que toca a rota."""
    out = []
    for n in numeros:
        try:
            h = fetch(f"https://roads.dot.ca.gov/roadscell.php?roadnumber={n}")
        except Exception as e:  # noqa: BLE001
            print(f"aviso: Caltrans {n} falhou ({e})")
            continue
        corpo = h.split("<hr>", 1)[-1]
        area = ""
        itens = []
        for bloco in re.findall(r"<p>(.*?)</p>", corpo, re.S):
            txt = _limpa(bloco)
            if not txt:
                continue
            m = re.match(r"\[IN THE (.+?) AREA\]\s*(.*)", txt, re.I)
            if m:
                area = m.group(1).strip().lower()
                txt = m.group(2).strip()
                if not txt:
                    continue
            # o roteiro nao passa do norte de Monterey: a area norte e ruido
            if "northern" in area:
                continue
            if txt.lower().startswith("no traffic restrictions"):
                itens.append({"area": area, "texto": txt, "fechado": False,
                              "na_rota": True, "livre": True})
                continue
            baixo = txt.lower()
            itens.append({
                "area": area,
                "texto": txt,
                "fechado": "is closed" in baixo or "closed" in baixo,
                "na_rota": any(c in baixo for c in CONDADOS_ROTA),
                "livre": False,
            })
        out.append({"rodovia": f"SR {n}" if n == "1" else f"US {n}", "itens": itens})
    return out


# ---------------------------------------------------------------- El Nino

def enso():
    """Status do boletim ENSO do Climate Prediction Center. E o unico dado com
    valor preditivo a 100 dias: previsao dia a dia nao existe nesse prazo."""
    try:
        h = fetch("https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/"
                  "enso_advisory/ensodisc.shtml")
    except Exception as e:  # noqa: BLE001
        print(f"aviso: CPC falhou ({e})")
        return None
    txt = _limpa(re.sub(r"(?is)<(script|style).*?</\1>", " ", h))
    st = re.search(r"ENSO Alert System Status:\s*([A-Za-zñÑ ]+?)(?:\s{2,}|$|synopsis)", txt, re.I)
    sin = re.search(r"synopsis:\s*(.+?)(?:\s*(?:During|Equatorial|In (?:August|September|October)|$))",
                    txt, re.I)
    emitido = re.search(r"issued by[^|]*?(\d{1,2}\s+\w+\s+20\d\d)", txt, re.I)
    if not emitido:
        emitido = re.search(r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|"
                            r"August|September|October|November|December)\s+20\d\d)", txt)
    return {
        "status": (st.group(1).strip() if st else ""),
        "sinopse": (sin.group(1).strip()[:700] if sin else ""),
        "emitido": (emitido.group(1) if emitido else ""),
    }


# ---------------------------------------------------------------- sol

def _solar(lat, lon, d, nascer, tz=-8, zenite=90.833):
    import math
    N = d.toordinal() - datetime(d.year, 1, 1).date().toordinal() + 1
    lng_h = lon / 15.0
    t = N + ((6 if nascer else 18) - lng_h) / 24.0
    M = (0.9856 * t) - 3.289
    L = (M + 1.916 * math.sin(math.radians(M)) + 0.020 * math.sin(math.radians(2 * M))
         + 282.634) % 360
    RA = math.degrees(math.atan(0.91764 * math.tan(math.radians(L)))) % 360
    RA = (RA + ((L // 90) * 90 - (RA // 90) * 90)) / 15.0
    sin_dec = 0.39782 * math.sin(math.radians(L))
    cos_dec = math.cos(math.asin(sin_dec))
    cos_h = ((math.cos(math.radians(zenite)) - sin_dec * math.sin(math.radians(lat)))
             / (cos_dec * math.cos(math.radians(lat))))
    if abs(cos_h) > 1:
        return None
    H = (360 - math.degrees(math.acos(cos_h))) if nascer else math.degrees(math.acos(cos_h))
    T = H / 15.0 + RA - (0.06571 * t) - 6.622
    h = (((T - lng_h) % 24) + tz) % 24
    return f"{int(h):02d}:{int(round((h % 1) * 60)):02d}"


def sol(lat, lon, dia="2026-12-23", tz=-8):
    d = datetime.fromisoformat(dia).date()
    return _solar(lat, lon, d, True, tz), _solar(lat, lon, d, False, tz)


# ---------------------------------------------------------------- push

def push_ntfy(titulo, corpo, prioridade="default", tags=""):
    if not NTFY_TOPIC:
        print("aviso: NTFY_TOPIC nao definido; push pulado")
        return
    cab = {"Title": titulo.encode("ascii", "replace").decode("ascii"),
           "Priority": prioridade, "Click": LINK_SITE}
    if tags:
        cab["Tags"] = tags
    req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=corpo.encode("utf-8"),
                  method="POST", headers=cab)
    try:
        with urlopen(req, timeout=30) as r:
            print(f"ntfy enviado ({r.getcode()}): {titulo}")
    except Exception as e:  # noqa: BLE001
        print(f"ERRO no ntfy: {e}")


def push_telegram(titulo, corpo, urgente=False):
    if not (TG_TOKEN and TG_CHAT):
        print("aviso: Telegram nao configurado")
        return
    sino = "\U0001f6a8 " if urgente else ""
    texto = (f"{sino}<b>{html_mod.escape(titulo)}</b>\n\n"
             f"<pre>{html_mod.escape(corpo)}</pre>\n{LINK_SITE}")
    dados = json.dumps({"chat_id": TG_CHAT, "text": texto[:4000], "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                        "disable_notification": not urgente}).encode("utf-8")
    req = Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=dados,
                  method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            print(f"telegram enviado ({r.getcode()}): {titulo}")
    except Exception as e:  # noqa: BLE001
        print(f"ERRO no telegram: {e}")


def upload_pa(conteudo, nome="index.html"):
    if not PA_TOKEN:
        print("aviso: PA_TOKEN nao definido; upload pulado")
        return False
    dest = f"/home/{PA_USER}/{PA_DIR}/{nome}"
    url = f"{PA_API}/api/v0/user/{PA_USER}/files/path{dest}"
    data = conteudo.encode("utf-8")
    lim = "----pa" + uuid.uuid4().hex
    corpo = ((f"--{lim}\r\n"
              f'Content-Disposition: form-data; name="content"; filename="{nome}"\r\n'
              "Content-Type: application/octet-stream\r\n\r\n").encode()
             + data + f"\r\n--{lim}--\r\n".encode())
    req = Request(url, data=corpo, method="POST", headers={
        "Authorization": f"Token {PA_TOKEN}",
        "Content-Type": f"multipart/form-data; boundary={lim}"})
    for tent in range(1, 4):
        try:
            with urlopen(req, timeout=90) as r:
                print(f"pagina publicada ({r.getcode()}): {dest}")
                return True
        except Exception as e:  # noqa: BLE001
            if tent < 3:
                print(f"upload tentativa {tent} falhou ({e}); repetindo")
                time.sleep(10 * tent)
            else:
                print(f"ERRO: upload falhou: {e}")
    return False


# ---------------------------------------------------------------- decisoes

def janela(hourly, dia, h0, h1):
    """Agrega as horas de um dia entre h0 e h1 (hora local do proprio ponto).
    Devolve None quando o dia esta fora do alcance do modelo, que e o caso
    normal enquanto a viagem estiver longe."""
    idx = [i for i, t in enumerate(hourly.get("time", []))
           if t[:10] == dia and h0 <= int(t[11:13]) < h1]
    if not idx:
        return None

    def vals(k):
        serie = hourly.get(k) or []
        return [serie[i] for i in idx if i < len(serie) and serie[i] is not None]

    def agg(k, f, div=1.0, pad=None):
        v = vals(k)
        return (f(v) / div) if v else pad

    return {
        "t": agg("temperature_2m", lambda v: sum(v) / len(v)),
        "raj": agg("wind_gusts_10m", max),
        "vento": agg("wind_speed_10m", max),
        "chuva": agg("precipitation", sum),
        "prob": agg("precipitation_probability", max),
        "nuv": agg("cloud_cover", lambda v: sum(v) / len(v)),
        "vis": agg("visibility", min, 1000.0),
        "neve": agg("snowfall", sum),
        "congel": agg("freezing_level_height", min),
    }



# Noites em que eles estao na Big Island com o 4x4 na mao (28/12 16h a 04/01 14h).
# O ingresso do parque vale 7 dias, e o cume nao tem hora marcada: as duas
# decisoes podem escolher a melhor noite em vez de obedecer ao roteiro.
NOITES_BI = ["2026-12-28", "2026-12-29", "2026-12-30", "2026-12-31",
             "2027-01-01", "2027-01-02", "2027-01-03"]
ORDEM_VER = {"bom": 0, "atencao": 1, "ruim": 2}


def melhor_noite(prev, pid, dias, h0, h1, avaliar):
    """Entre as noites possiveis, a de melhor veredito. Empate fica com a do
    roteiro original, que e a primeira da lista com dado."""
    p = prev.get(pid)
    if not p:
        return dias[1]
    melhor, nota = None, 9
    for dia in dias:
        w = janela(p["hourly"], dia, h0, h1)
        if w is None:
            continue
        n = ORDEM_VER.get(avaliar(w)[0], 3)
        if n < nota:
            melhor, nota = dia, n
    return melhor or dias[1]


def decisoes(prev, mar, kil):
    """Regras de ida ou nao ida, cada uma amarrada num numero que o modelo
    entrega. Enquanto o dia nao cabe na previsao, a regra fica 'armada': o
    painel mostra o gatilho, nao um palpite."""
    out = []

    def J(pid, dia, h0, h1):
        p = prev.get(pid)
        if not p:
            return None
        w = janela(p["hourly"], dia, h0, h1)
        if w is not None and pid in mar:
            h = mar[pid]
            i = [k for k, t in enumerate(h.get("time", []))
                 if t[:10] == dia and h0 <= int(t[11:13]) < h1]
            ondas = [h["wave_height"][k] for k in i
                     if h.get("wave_height") and h["wave_height"][k] is not None]
            w["onda"] = max(ondas) if ondas else None
        return w

    def add(cid, titulo, dia, quando, regra, w, avaliar, recomenda):
        if w is None:
            out.append({"id": cid, "titulo": titulo, "dia": dia, "quando": quando,
                        "regra": regra, "veredito": "espera", "numeros": "",
                        "motivo": "Fora do alcance do modelo. A regra dispara quando "
                                  "o dia entrar nos 16 dias de previsão.",
                        "recomenda": recomenda})
            return
        ver, motivo, numeros = avaliar(w)
        out.append({"id": cid, "titulo": titulo, "dia": dia, "quando": quando,
                    "regra": regra, "veredito": ver, "motivo": motivo,
                    "numeros": numeros, "recomenda": recomenda})

    # 1. Cume do Mauna Kea. A estrada do cume fecha por gelo, e gelo se antecipa
    #    pelo nivel de congelamento caindo abaixo dos 4.207 m do cume COM chuva.
    def av_mk(w):
        gelo = (w["neve"] or 0) > 0 or ((w["congel"] or 9999) < 4250
                                        and (w["chuva"] or 0) > 0.2)
        raj = w["raj"] or 0
        num = (f"rajada {raj:.0f} nós, nuvens {w['nuv'] or 0:.0f}%, nível de "
               f"congelamento {w['congel'] or 0:.0f} m, neve {w['neve'] or 0:.1f} cm, "
               f"{w['t'] or 0:.0f}°C no cume")
        if gelo:
            return "ruim", ("Gelo ou neve na estrada do cume. A Mauna Kea Access Road "
                            "fecha nessa condição, e 4x4 não resolve gelo."), num
        if raj > 45:
            return "ruim", f"Rajada de {raj:.0f} nós no cume. Acima de 45 não se fica de pé.", num
        if raj > 30 or (w["nuv"] or 0) > 75:
            return "atencao", ("Vento forte ou cume dentro da nuvem. Subir sim, "
                               "contar com estrelas não."), num
        return "bom", "Cume limpo e vento tolerável. É a noite de subir.", num

    dia_mk = melhor_noite(prev, "mk_cume", NOITES_BI, 15, 21, av_mk)
    add("mk_cume", "Cume do Mauna Kea, poente e estrelas", dia_mk, "15h às 21h",
        "Não sobe com neve, ou nível de congelamento abaixo de 4.250 m com chuva, "
        "ou rajada acima de 45 nós.",
        J("mk_cume", dia_mk, 15, 21), av_mk,
        "Aclimatar 30 minutos na VIS, a 2.804 m, antes de seguir. Subir com luz e "
        "descer no escuro. Sem posto de gasolina na subida e sem sinal de celular. "
        "O Wrangler 4x4 da reserva atende a exigência da estrada.")

    # 2. Brilho da cratera do Kilauea: depende de estar em erupcao E de ter ceu.
    def av_kil(w):
        cor = (kil or {}).get("cor", "")
        num = (f"nuvens {w['nuv'] or 0:.0f}%, chuva {w['chuva'] or 0:.1f} mm, "
               f"{w['t'] or 0:.0f}°C, USGS {cor or 'sem leitura'}")
        if cor not in ("ORANGE", "RED"):
            return "atencao", ("Sem fonte de lava agora. O mirante vale de dia; o "
                               "brilho noturno só existe em episódio ativo."), num
        if (w["nuv"] or 0) > 80 or (w["chuva"] or 0) > 2:
            return "atencao", ("Em erupção, mas cratera encoberta. Ir mesmo assim: "
                               "a nuvem abre e fecha em minutos."), num
        return "bom", "Em erupção e céu aberto. É a noite.", num

    dia_kil = melhor_noite(prev, "kilauea", NOITES_BI, 17, 22, av_kil)
    add("kilauea", "Cratera do Kilauea ao anoitecer", dia_kil, "17h às 22h",
        "Aviso urgente se o USGS puser o Kilauea em ORANGE ou RED durante a viagem.",
        J("kilauea", dia_kil, 17, 22), av_kil,
        "O ingresso do parque vale sete dias, então serve qualquer noite entre "
        "29/12 e 04/01, e vocês estarão na ilha até o dia 4. Quem marca a hora é "
        "o vulcão, não a agenda.")

    # 3. Sentido da volta de Oahu: barlavento chove de manha; se chover, inverte.
    lan = J("lanikai", "2026-12-27", 8, 13)
    nor = J("northshore", "2026-12-27", 8, 13)

    def av_oahu(w):
        cl = (lan or {}).get("chuva") or 0
        cn = (nor or {}).get("chuva") or 0
        num = f"chuva de manhã: barlavento {cl:.1f} mm, North Shore {cn:.1f} mm"
        if cl > cn + 1.5:
            return "atencao", ("Barlavento mais molhado. Inverter o laço: subir pelo "
                               "centro até o North Shore e voltar por Kailua à tarde."), num
        return "bom", ("Barlavento igual ou melhor que o North Shore. Seguir o "
                       "sentido normal: leste primeiro, North Shore no fim."), num

    add("oahu_sentido", "Sentido da volta da ilha de Oahu", "2026-12-27", "manhã",
        "Inverte o laço se o barlavento tiver 1,5 mm mais de chuva que o North "
        "Shore entre 8h e 13h.",
        lan, av_oahu,
        "Se quiserem Hanauma Bay, a reserva abre às 7h de 25/12 e esgota em "
        "segundos; a entrada só vale até 13h30, e aí o laço começa por lá de "
        "qualquer maneira. Carro às 10h no centro de Honolulu e devolução às 10h "
        "do dia 28 no aeroporto: a volta inteira cabe num dia, 180 km.")

    # 4. Ida pela costa, 22/12.
    def av_ida(w):
        num = (f"chuva 9h-18h {w['chuva'] or 0:.1f} mm, rajada {w['raj'] or 0:.0f} nós, "
               f"visibilidade mínima {w['vis'] or 20:.0f} km")
        if (w["chuva"] or 0) > 15 or (w["raj"] or 0) > 35:
            return "ruim", ("Rio atmosférico no dia da transferência. Cortar Malibu e "
                            "fazer 101 direto: chegar seco vale mais que El Matador."), num
        if (w["chuva"] or 0) > 4:
            return "atencao", "Chuva no caminho. Manter o plano e encurtar as paradas.", num
        return "bom", "Dia de estrada limpo. Plano cheio de pé.", num

    add("ca_ida", "Ida: Los Angeles a Pacific Grove", "2026-12-22", "9h às 18h",
        "Corta as paradas se a chuva do dia passar de 15 mm ou a rajada de 35 nós.",
        J("sb", "2026-12-22", 9, 18), av_ida,
        "PCH de Santa Monica a Malibu, 101 pela orla de Ventura a Santa Barbara, "
        "101 pelo interior de Gaviota a Pacific Grove. Big Sur não entra na ida: "
        "seriam 2h30 a mais e no escuro.")

    # 5. Volta, 24/12. O risco da madrugada aqui e neblina no vale, nao chuva.
    def av_volta(w):
        vis = w["vis"] if w["vis"] is not None else 20
        num = (f"visibilidade mínima 6h-9h {vis:.1f} km, chuva {w['chuva'] or 0:.1f} mm")
        if vis < 1.5:
            return "ruim", ("Neblina fechada no vale de Salinas. Sair às 7h e contar "
                            "com 40 minutos a mais até clarear."), num
        if vis < 5:
            return "atencao", ("Neblina no vale. Farol baixo e sem pressa nos "
                               "primeiros 80 km."), num
        return "bom", "Vale limpo. 101 direto até o LAX.", num

    add("ca_volta", "Volta: Pacific Grove ao LAX", "2026-12-24", "6h às 9h",
        "Sair uma hora mais cedo se a visibilidade no vale de Salinas cair abaixo "
        "de 1,5 km.",
        J("salinas", "2026-12-24", 6, 9), av_volta,
        "São 5h20 de 101 para uma janela de 7h, com devolução às 15h e voo às "
        "17h43. Não cabe desvio cênico. Sair às 7h em vez de 8h transforma 1h20 "
        "de folga em 2h20, e é a única mudança que eu faria no roteiro.")

    # 6. Ida e volta a Bixby Bridge, no dia da peninsula.
    def av_bixby(w):
        num = (f"nuvens {w['nuv'] or 0:.0f}%, chuva {w['chuva'] or 0:.1f} mm, "
               f"rajada {w['raj'] or 0:.0f} nós")
        if (w["chuva"] or 0) > 5 or (w["raj"] or 0) > 35:
            return "ruim", "Chuva e vento na falésia. Ficar na península.", num
        if (w["nuv"] or 0) > 80:
            return "atencao", "Encoberto. A ponte aparece, o horizonte não.", num
        return "bom", "Tarde boa para o trecho norte de Big Sur.", num

    add("bixby", "Ida e volta de Carmel a Bixby Bridge", "2026-12-23", "14h às 17h",
        "Desiste se a chuva da tarde passar de 5 mm ou a rajada de 35 nós.",
        J("bixby", "2026-12-23", 14, 17), av_bixby,
        "24 km ao sul de Carmel, 35 minutos de carro, no trecho que ficou aberto "
        "depois dos incêndios. É o pedaço de Big Sur que cabe nesta viagem. Poente "
        "às 16h57: saindo de Point Lobos às 15h30 a luz dourada pega a ponte.")

    # 7. Snorkel em Kealakekua.
    def av_snorkel(w):
        onda = w.get("onda")
        num = ((f"onda {onda:.1f} m" if onda is not None else "sem dado de onda")
               + f", vento {w['vento'] or 0:.0f} nós")
        if onda is not None and onda > 2.0:
            return "ruim", "Mar grande na baía. Visibilidade do snorkel vai a zero.", num
        if onda is not None and onda > 1.2:
            return "atencao", "Mar mexido. O catamarã sai, a água fica turva.", num
        return "bom", "Baía calma. É o melhor snorkel da ilha.", num

    add("snorkel", "Catamarã e snorkel na Kealakekua Bay", "2027-01-02", "9h às 13h",
        "Mar acima de 2 m fecha a janela de visibilidade.",
        J("kealakekua", "2027-01-02", 9, 13), av_snorkel,
        "O snorkel noturno com arraias-manta é na enseada de Keauhou, protegida, e "
        "aguenta mar que a baía aberta não aguenta.")

    # 8. North Shore: onda grande e o espetaculo, e tambem o perigo.
    def av_ns(w):
        onda = w.get("onda")
        num = f"onda {onda:.1f} m" if onda is not None else "sem dado de onda"
        if onda is not None and onda > 3.5:
            return "atencao", ("Swell grande: é o espetáculo do inverno em Waimea e "
                               "Sunset. Ver de cima, não entrar na água."), num
        if onda is not None and onda < 1.2:
            return "atencao", "Mar pequeno para o North Shore. Sem show de ondas.", num
        return "bom", "Mar de inverno na medida: onda para ver e praia para andar.", num

    add("northshore", "North Shore: as ondas do inverno", "2026-12-27", "12h às 17h",
        "Acima de 3,5 m é espetáculo para assistir, nunca para nadar.",
        J("northshore", "2026-12-27", 12, 17), av_ns,
        "Waimea Bay e Sunset Beach. Correntes de retorno matam gente ali todo "
        "inverno. Praia de andar é Haleʻiwa, e o almoço é nos food trucks.")

    return out


# ---------------------------------------------------------------- resumo

VER_TXT = {"bom": "OK", "atencao": "ATENCAO", "ruim": "NAO", "espera": "armada"}


def resumo_texto(d):
    """Corpo do aviso de 6 em 6 horas. Texto puro, sem emoji e sem acento nos
    titulos, para o ntfy nao mutilar."""
    L = [f"Atualizado {d['gerado'].replace('T',' ')} na costa (PST).",
         f"Faltam {d['dias_para']} dias para o carro no LAX."]
    e = d.get("enso") or {}
    if e.get("status"):
        L += ["", f"EL NINO: {e['status']}"]
        if e.get("sinopse"):
            L.append(f"  {e['sinopse'][:240]}")
    k = d.get("kilauea") or {}
    if k.get("cor"):
        L += ["", f"KILAUEA: {k['cor']}/{k['nivel']}"
                  + ("  (fonte de lava ativa)" if k["cor"] in ("ORANGE", "RED") else "")]
    L += ["", "AGORA"]
    for pid in ("lax", "pg", "waikiki", "hilo", "kona", "mk_cume"):
        p = d["por_id"].get(pid)
        a = (p or {}).get("agora")
        if a:
            L.append(f"  {p['nome'][:22]:<22} {a['t']:>5.0f}C  {a['mm']:.1f} mm  "
                     f"vento {a['v']:.0f} no  nuvens {a['n']:.0f}%")
    L += ["", "DECISOES"]
    for dec in d["decisoes"]:
        L.append(f"  [{VER_TXT[dec['veredito']]:<8}] {dec['dia'][8:10]}/"
                 f"{dec['dia'][5:7]} {dec['titulo'][:40]}")
        if dec["veredito"] != "espera":
            L.append(f"             {dec['motivo'][:110]}")
    if d["prev_por_dia"]:
        L += ["", "DIAS JA COM PREVISAO"]
        for et in d["etapas"]:
            pv = d["prev_por_dia"].get(et["dia"])
            if pv:
                L.append(f"  {et['dia'][8:10]}/{et['dia'][5:7]} {et['titulo'][:32]:<32} "
                         f"{pv['tmax']:.0f}/{pv['tmin']:.0f}C  {pv['mm']:.1f} mm  {pv['prob']}%")
    else:
        L += ["", f"Nenhum dia do roteiro cabe nos 16 dias do modelo ainda. "
                  f"O primeiro entra em {max(0, d['dias_para'] - 16)} dias."]
    L += ["", "ESTRADA (Caltrans, condados da rota)"]
    achou = False
    for v in d["estradas"]:
        for i in v["itens"]:
            if not i["na_rota"]:
                continue
            achou = True
            marca = "FECHADA" if i["fechado"] else ("livre" if i.get("livre") else "restricao")
            L.append(f"  {v['rodovia']}: {marca} - {i['texto'][:140]}")
    if not achou:
        L.append("  sem boletim para os condados da rota")
    if d["alertas"]:
        L += ["", "AVISOS DO NWS"]
        for a in d["alertas"]:
            L.append(f"  {a['evento']} ({a['severidade']}) - {a['onde'][:70]}")
    else:
        L += ["", "AVISOS DO NWS: nenhum ativo na rota."]
    return "\n".join(L)


# ---------------------------------------------------------------- main

def _le(p, padrao):
    if not p.exists():
        return padrao
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - estado corrompido nao pode travar a rodada
        return padrao


def main():
    forca = "--forca" in sys.argv
    so_local = "--sem-publicar" in sys.argv
    estado = _le(STATE, {})
    agora = datetime.now(timezone.utc)

    if not forca and estado.get("rodada_utc"):
        try:
            passou = (agora - datetime.fromisoformat(estado["rodada_utc"])).total_seconds()
            if passou < HORAS_FRESCOR * 3600:
                print(f"guarda de frescor: publicado ha {passou/3600:.1f} h "
                      f"(limite {HORAS_FRESCOR} h). Nada a fazer.")
                return 0
        except Exception:  # noqa: BLE001
            pass

    prev = previsoes_lote(PONTOS)
    mar = mar_lote(PONTOS)
    alertas = alertas_por_area()
    vias = estradas()
    es = enso()
    kil = kilauea_status()
    print(f"kilauea: {(kil or {}).get('cor')}/{(kil or {}).get('nivel')}")

    fusos = {r[0]: r[3] for r in REGIOES}
    dia_ref = {"ca": "2026-12-23", "oahu": "2026-12-27", "bi": "2026-12-30"}
    pontos = []
    for (pid, nome, lat, lon, elev, reg, papel, normal, tem_mar) in PONTOS:
        pr = prev.get(pid)
        if not pr:
            print(f"AVISO: {pid} sem previsao; fica fora da pagina")
            continue
        nasc, poe = sol(lat, lon, dia_ref[reg], fusos[reg])
        h = pr["hourly"]
        # "agora" = a hora cheia mais proxima do relogio local daquele ponto
        local = agora + timedelta(hours=fusos[reg])
        chave = local.strftime("%Y-%m-%dT%H:00")
        i = h["time"].index(chave) if chave in h["time"] else 0
        pontos.append({
            "id": pid, "nome": nome, "regiao": reg, "papel": papel, "normal": normal,
            "nascer": nasc, "por_do_sol": poe, "elev": pr.get("elev"),
            "hourly": h, "daily": pr["daily"], "mar": mar.get(pid),
            "agora": {"t": h["temperature_2m"][i] or 0, "mm": h["precipitation"][i] or 0,
                      "v": h["wind_speed_10m"][i] or 0, "n": h["cloud_cover"][i] or 0,
                      "hora": chave[11:16]},
        })
    por_id = {p["id"]: p for p in pontos}

    etapas = [{"dia": e[0], "regiao": e[1], "titulo": e[2], "resumo": e[3],
               "pontos": e[4], "dirige": e[5]} for e in ETAPAS]

    # previsao do dia de cada etapa, medida no DESTINO daquela etapa
    prev_por_dia = {}
    for et in etapas:
        p = por_id.get(et["pontos"][-1])
        if not p:
            continue
        dl = p["daily"]
        if et["dia"] in dl["time"]:
            j = dl["time"].index(et["dia"])
            prev_por_dia[et["dia"]] = {
                "tmax": dl["temperature_2m_max"][j], "tmin": dl["temperature_2m_min"][j],
                "mm": dl["precipitation_sum"][j] or 0,
                "prob": dl["precipitation_probability_max"][j] or 0,
                "rajada": dl["wind_gusts_10m_max"][j] or 0,
                "sol": (dl["sunrise"][j][11:16] + " / " + dl["sunset"][j][11:16]),
            }

    partida = datetime.fromisoformat(VIAGEM["carro_lax"]).replace(tzinfo=PACIFICO)
    dias_para = max(0, (partida - agora).days)

    d = {
        "gerado": (agora + timedelta(hours=-8)).strftime("%d/%m/%YT%H:%M"),
        "gerado_brt": agora.astimezone(BRT).strftime("%d/%m/%YT%H:%M"),
        "dias_para": dias_para, "viagem": VIAGEM, "dias_grade": DIAS_GRADE,
        "dias_viagem": [e["dia"] for e in etapas],
        "regioes": [{"id": r[0], "nome": r[1]} for r in REGIOES],
        "pontos": pontos, "por_id": por_id, "etapas": etapas,
        "prev_por_dia": prev_por_dia, "estradas": vias, "alertas": alertas,
        "enso": es, "kilauea": kil,
        "decisoes": decisoes(prev, mar, kil),
    }

    # ---- alertas urgentes, sempre por DELTA: repetir o mesmo aviso a cada 6 h
    # treina o usuario a ignorar o push.
    vistos = set(estado.get("vistos") or [])
    novos_ids, urgentes = [], []
    for a in alertas:
        if a["severidade"] in ("Severe", "Extreme") and a["id"] not in vistos:
            novos_ids.append(a["id"])
            urgentes.append(f"NWS {a['evento']}: {a['manchete'][:180]}")
    for v in vias:
        for i in v["itens"]:
            if i["fechado"] and i["na_rota"]:
                marca = "via:" + str(hash(i["texto"][:120]))
                if marca not in vistos:
                    novos_ids.append(marca)
                    urgentes.append(f"{v['rodovia']} fechada: {i['texto'][:180]}")
    cor_kil = (kil or {}).get("cor", "")
    if cor_kil in ("ORANGE", "RED") and estado.get("kilauea_cor") not in ("ORANGE", "RED"):
        urgentes.append(f"Kilauea subiu para {cor_kil}: fonte de lava ativa. "
                        f"Detalhe no monitor do vulcao.")
    for dec in d["decisoes"]:
        if dec["veredito"] == "ruim":
            marca = "dec:" + dec["id"] + ":" + dec["dia"]
            if marca not in vistos:
                novos_ids.append(marca)
                urgentes.append(f"{dec['titulo']} ({dec['dia'][8:10]}/"
                                f"{dec['dia'][5:7]}): {dec['motivo'][:160]}")

    corpo = resumo_texto(d)
    print("\n" + corpo + "\n")

    if urgentes:
        titulo = "Costa Dourada: " + urgentes[0][:60]
        push_ntfy(titulo, "\n".join(urgentes) + "\n\n" + corpo,
                  prioridade="high", tags="warning")
        push_telegram(titulo, "\n".join(urgentes) + "\n\n" + corpo, urgente=True)
    else:
        push_telegram(f"Costa Dourada, faltam {dias_para} dias", corpo, urgente=False)

    from _pagina import monta
    html, js = monta(d)
    (AQUI / "index.html").write_text(html, encoding="utf-8")
    print(f"pagina gerada: {len(html)//1024} KB")

    if not so_local:
        # valida o JS antes de publicar: aspas aninhadas dentro de string JS ja
        # derrubaram paginas inteiras sem avisar
        import shutil
        import subprocess
        if shutil.which("node"):
            jf = AQUI / "state" / "_check.js"
            jf.write_text(js, encoding="utf-8")
            r = subprocess.run(["node", "--check", str(jf)], capture_output=True, text=True)
            jf.unlink(missing_ok=True)
            if r.returncode != 0:
                print("ERRO: JS invalido, NAO publiquei:\n" + r.stderr[:800])
                return 2
            print("JS validado pelo node")
        else:
            print("aviso: node ausente, JS nao validado")
        if not upload_pa(html):
            return 3

    estado.update({
        "rodada_utc": agora.isoformat(timespec="seconds"),
        "kilauea_cor": cor_kil,
        "vistos": sorted(vistos | set(novos_ids))[-400:],
        "dias_para": dias_para,
    })
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    hist = _le(HIST, [])
    hist.append({"utc": agora.isoformat(timespec="seconds"), "dias_para": dias_para,
                 "kilauea": cor_kil, "avisos": len(alertas),
                 "urgentes": len(urgentes)})
    HIST.write_text(json.dumps(hist[-500:], ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
