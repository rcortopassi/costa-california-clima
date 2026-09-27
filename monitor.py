#!/usr/bin/env python3
"""Honeymoon - clima, estrada, mar e missa de cada dia da viagem de dezembro de 2026.

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

import hashlib
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
GEO = AQUI / "state" / "geo.json"
MAPAS_LOCAL = AQUI / "mapas"

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
PA_DIR = "honeymoon"
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
    "carro_oahu": "2026-12-27T10:00",      # 1778 Ala Moana Blvd, Honolulu
    "devolve_oahu": "2026-12-28T10:00",    # aeroporto HNL
    "carro_bi": "2026-12-28T16:00",        # Jeep Wrangler 4x4, aeroporto de Hilo
    "devolve_bi": "2027-01-04T14:00",      # aeroporto de Kona
}

REGIOES = [
    ("ca", "Golden Coast", "America/Los_Angeles", -8),
    ("oahu", "Oʻahu", "Pacific/Honolulu", -10),
    ("bi", "Hawaiʻi", "Pacific/Honolulu", -10),
]

# id, nome, lat, lon, elevacao forcada (None = modelo decide), regiao, papel,
# normal climatologica da janela daquela regiao, mar (pede dado de onda)
PONTOS = [
    # ---- California: 21 a 24 de dezembro, normais 1995-2025
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
    ("lanikai", "Kailua e Lanikai", 21.3930, -157.7350, 5, "oahu", "Água clara da Windward Coast",
     {"tmax": 24.0, "tmin": 20.8, "mm": 2.5, "pct": 40, "forte": 10}, True),
    ("kualoa", "Kualoa", 21.5200, -157.8380, 10, "oahu", "Windward Coast",
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
    ("mk_vis", "Mauna Kea VIS", 19.7600, -155.4560, 2804, "bi",
     "Aclimatação obrigatória, 9.200 pés",
     {"tmax": 12.0, "tmin": 3.0, "mm": 2.6, "pct": 35, "forte": 10}, False),
    ("mk_cume", "Mauna Kea Summit", 19.8207, -155.4681, 4207, "bi",
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
     "Voos: Brasília 2h, Panamá 6h a 11h35, Houston 14h54 a 16h30, Los Angeles 18h10. "
     "Transfer do Holiday Inn. Sem carro.", ["lax"], False),
    ("2026-12-22", "ca", "Los Angeles a Pacific Grove",
     "Carro às 9h no LAX. PCH até Malibu, 101 pela orla até Santa Barbara, "
     "101 pelo interior até Pacific Grove. Recepção fecha às 18h.",
     ["lax", "malibu", "sb", "pismo", "paso", "salinas", "pg"], True),
    ("2026-12-23", "ca", "Monterey Peninsula",
     "Aquário, Cannery Row, 17-Mile Drive, Carmel, Point Lobos. "
     "Sobra tempo para uma ida e volta até Bixby Bridge.",
     ["pg", "carmel", "bixby"], True),
    ("2026-12-24", "ca", "Pacific Grove a Los Angeles",
     "Saída às 6h10 e missa às 8h30 em Paso Robles. Carro de volta no LAX às 15h, voo "
     "para Honolulu às 17h43.",
     ["pg", "salinas", "paso", "pismo", "sb", "lax"], True),
    ("2026-12-25", "oahu", "Natal em Waikiki",
     "Dia todo a pé pela orla. Quase tudo fechado na ilha.", ["waikiki"], False),
    ("2026-12-26", "oahu", "Diamond Head e Pearl Harbor",
     "Trilha no começo da manhã, Pearl Harbor depois. Sem carro.",
     ["diamond", "waikiki"], False),
    ("2026-12-27", "oahu", "Volta a Oʻahu de carro",
     "Carro às 10h no centro. Único dia com carro na ilha: Hanauma, costa leste, "
     "Kualoa e North Shore.",
     ["hanauma", "makapuu", "lanikai", "kualoa", "northshore", "haleiwa"], True),
    ("2026-12-28", "bi", "Oʻahu a Hilo",
     "Carro devolvido às 10h no HNL, voo para Hilo às 14h17, pouso às 15h13. Jeep 4x4 "
     "às 16h no aeroporto de Hilo.",
     ["hilo"], True),
    ("2026-12-29", "bi", "Hawaii Volcanoes National Park",
     "Crater Rim, Nāhuku, Chain of Craters. Voltar ao anoitecer se houver "
     "atividade na cratera.", ["kilauea"], True),
    ("2026-12-30", "bi", "Hamakua Coast e Mauna Kea",
     "Jardim tropical, Akaka Falls, Waipiʻo Valley Lookout. À noite, o "
     "Mauna Kea Summit para o poente e as estrelas.",
     ["akaka", "waipio", "mk_vis", "mk_cume"], True),
    ("2026-12-31", "bi", "Hilo a Kona pelo sul",
     "Travessia pelo sul com parada em Punaluʻu. Check-in às 16h, réveillon "
     "no resort.", ["punaluu", "kona"], True),
    ("2027-01-01", "bi", "Primeiro dia do ano em Keauhou",
     "Dia de resort, sem despertador.", ["kona"], False),
    ("2027-01-02", "bi", "Mar e vida marinha em Kona",
     "Catamarã à Kealakekua Bay de manhã, snorkel noturno com arraias-manta.",
     ["kealakekua", "kona"], False),
    ("2027-01-03", "bi", "Praias de Kona e Kohala",
     "Magic Sands, Kua Bay ou Hāpuna. Ritmo livre.", ["hapuna", "kona"], True),
    ("2027-01-04", "ca", "Kona a Los Angeles",
     "Carro de volta às 14h em Kona, voo às 16h24, pouso em Los Angeles às 23h50. "
     "Transfer do Holiday Inn.", ["kona", "lax"], True),
    ("2027-01-05", "ca", "Último dia em Los Angeles",
     "Dia livre a pé ou de aplicativo. Saída para o aeroporto às 20h: voo para Houston "
     "à 0h40 de 06/01, Panamá e Brasília.",
     ["lax"], False),
]

# ---------------------------------------------------------------- roteiro
# Trechos com hora, distancia e a estrada exata. Poentes calculados para as
# datas e coordenadas reais, nao copiados de lugar nenhum.
# (hora, o que, como, duracao)
ROTEIRO = [
 {"dia": "2026-12-22", "regiao": "ca", "titulo": "Ida: Los Angeles a Pacific Grove",
  "cabecalho": "563 km e 6h40 de volante, poente às 16h49 no sul e 16h57 no norte",
  "trechos": [
    ("09:00", "Retirar o carro na Alamo", "Terminal do LAX. Conferir o tanque e a "
     "franquia antes de sair", "20 min"),
    ("09:20", "LAX até El Matador, em Malibu", "Lincoln Blvd norte, I-10 oeste, "
     "SR-1 (Pacific Coast Highway). Oceano à esquerda de Santa Monica em diante",
     "52 km, 1h"),
    ("10:20", "El Matador State Beach", "USD 10 por veículo. Escada na falésia até "
     "os arcos de pedra. Maré baixa deixa passar entre eles", "40 min"),
    ("11:00", "Malibu até Santa Barbara", "SR-1 até Oxnard, US-101 norte. De Ventura "
     "a Santa Barbara a 101 corre na praia: sair da PCH aqui não custa mar nenhum",
     "98 km, 1h15"),
    ("12:15", "Almoço em Santa Barbara", "State Street e o cais. Estacionamento "
     "municipal das primeiras 75 minutos de graça", "1h15"),
    ("13:30", "Santa Barbara até Pismo Beach", "US-101 pela orla até Gaviota, passando por "
     "El Capitán e Refugio; em Gaviota Pass a estrada entra no continente. Recusar a CA 154 "
     "(San Marcos Pass) que o GPS vai sugerir: 22 km mais curta, mas é serra por dentro da "
     "montanha, sem mar. Em Las Cruces ignorar a SR-1 para Lompoc", "155 km, 1h40"),
    ("15:10", "Monarch Butterfly Grove, em Pismo", "Na Dolliver St, a própria SR-1, "
     "dois minutos fora da 101. Gratuito. Dezembro é o pico das monarcas "
     "hibernando nos eucaliptos", "30 min"),
    ("15:40", "Pismo até Pacific Grove", "US-101 por San Luis Obispo, Atascadero, "
     "Paso Robles e Salinas. Interior, quatro pistas, rápido e sem graça, e é de "
     "propósito: é o trecho que sobra para depois do escuro", "257 km, 2h45"),
    ("18:25", "Gosby House Inn", "643 Lighthouse Ave. A recepção fecha às 18h",
     "chegada"),
  ],
  "notas": [
    "O dia todo tem 9 horas e o plano cheio pede 9h25. A saída não é cortar "
    "parada: é pedir à agência para avisar a Gosby House que vocês chegam entre "
    "18h30 e 19h. A própria confirmação diz que basta avisar antes.",
    "A ordem foi montada para o escuro cair no trecho feio. Tudo o que tem "
    "paisagem acontece antes das 16h; os últimos 257 km de 101 são retão de "
    "quatro pistas e não perdem nada por serem à noite.",
    "Solvang é a alternativa ao bosque das monarcas, cinco minutos fora da 101 em "
    "Buellton. Não cabem os dois. O bosque é gratuito, dura 30 minutos e é "
    "sazonal; o vilarejo dinamarquês fica lá o ano todo.",
    "Big Sur não entra na ida. Pegar a SR-1 em San Luis Obispo somaria 2h30 e "
    "jogaria a falésia toda para depois do poente.",
  ]},

 {"dia": "2026-12-23", "regiao": "ca", "titulo": "Monterey Peninsula e o pedaço de Big Sur",
  "cabecalho": "menos de 100 km no dia inteiro, poente às 16:57 em Carmel",
  "trechos": [
    ("09:45", "Fila do Monterey Bay Aquarium", "Abre às 10h. 23/12 é feriado cheio: "
     "chegar antes da abertura vale meia hora de fila", "2h30"),
    ("12:30", "Cannery Row e almoço", "A pé desde o aquário", "1h30"),
    ("14:00", "17-Mile Drive", "Entrar pelo Pacific Grove Gate e sair pelo Carmel "
     "Gate, no sentido do relógio. USD 12,75 por veículo", "1h15"),
    ("15:15", "Point Lobos", "USD 10 por veículo. Fecha ao anoitecer. Trilha curta "
     "da Cypress Grove", "30 min"),
    ("15:45", "Carmel até Bixby Bridge", "SR-1 sul. Passa por Hurricane Point e "
     "Rocky Creek antes da ponte", "24 km, 35 min"),
    ("16:30", "Bixby Bridge no poente", "O mirante do lado norte olha para a ponte "
     "e para o sul. Poente às 16:57", "45 min"),
    ("17:30", "Volta a Pacific Grove", "SR-1 norte no escuro. É o trecho manso, não "
     "a falésia exposta", "40 min"),
  ],
  "notas": [
    "Este é o dia que ganha o pedaço de Big Sur que a viagem não teria de outra "
    "forma. A ida e volta a Bixby custa 1h30 contando as paradas e entrega a "
    "vista mais fotografada da costa inteira.",
    "A versão cautelosa inverte: Bixby de manhã, das 8h às 10h30, e o aquário "
    "depois do almoço. Troca a luz dourada na ponte por não dirigir a SR-1 no "
    "escuro. Nenhuma das duas está errada.",
    "O Monarch Grove Sanctuary de Pacific Grove fica a 1,5 km da pousada, é "
    "gratuito e também está no pico em dezembro. Cabe em 30 minutos antes do "
    "aquário, e serve de plano B se Pismo não der na ida.",
    "Lovers Point, o poente que o roteiro original sugeria, fica a sete minutos a "
    "pé da pousada e continua disponível em qualquer uma das duas noites.",
  ]},

 {"dia": "2026-12-24", "regiao": "ca", "titulo": "Volta: Pacific Grove ao LAX",
  "cabecalho": "564 km pela US 101, com a missa das 8h30 em Paso Robles no caminho",
  "trechos": [
    ("06:10", "Sair de Pacific Grove", "CA 68 até Salinas, ainda no escuro: amanhece às 7h17. "
     "Farol baixo se houver neblina", "37 km, 35 min"),
    ("06:45", "Salinas Valley", "US-101 sul. É aqui que mora o único risco de neblina da viagem, "
     "e é neblina de vale, não de costa", "153 km, 1h30"),
    ("08:15", "Chegada a Paso Robles", "St. Rose of Lima fica a poucos minutos da 101. Café antes "
     "da missa", "15 min"),
    ("08:30", "Missa em St. Rose of Lima", "A missa do dia, e a razão do horário de saída", "35 min"),
    ("09:10", "Paso Robles até Buellton", "US-101 por San Luis Obispo, Cuesta Grade e "
     "Santa Maria", "146 km, 1h30"),
    ("10:40", "Buellton, a parada de comida", "Depois daqui não para mais", "30 min"),
    ("11:10", "Buellton até Santa Barbara pela orla", "US-101 por Gaviota e Refugio. A CA "
     "154 corta caminho e economiza uns 20 minutos: só se o dia apertar e não houver aviso "
     "de vento ou chuva na serra", "73 km, 45 min"),
    ("11:55", "Santa Barbara até Ventura", "US-101 na praia", "44 km, 30 min"),
    ("12:25", "Ventura até Woodland Hills", "US-101 pelo San Fernando Valley, já com "
     "trânsito de véspera de Natal", "70 km, 50 min"),
    ("13:15", "Woodland Hills até o LAX", "I-405 sul pela Sepulveda Pass, o trecho que "
     "mais trava. Não passar pelo centro", "41 km, 45 min"),
    ("14:00", "Abastecer perto do aeroporto", "A Alamo cobra caro pelo tanque. Posto na "
     "Century Blvd ou na Sepulveda", "15 min"),
    ("14:15", "Devolver o carro", "Locadoras do lado leste do LAX. Devolução marcada para "
     "15h", "folga de 45 min"),
    ("17:43", "Voo para Honolulu", "Chegada às 21h31, e cerca de 30 minutos de "
     "aplicativo até Waikiki", "—"),
  ],
  "notas": [
    "A missa do dia fica em Paso Robles, às 8h30, na própria US 101, e é ela que marca a "
    "saída às 6h10. Medido: 564 km e cerca de 6 horas de volante, mais missa, comida, "
    "abastecimento e o trânsito de véspera de Natal em Los Angeles, e ainda sobram uns 45 "
    "minutos antes das 15h. Do outro lado está o voo para Honolulu às 17h43.",
    "A alternativa é a missa das 7h30 na San Carlos Cathedral, em Monterey, saindo às 8h05. "
    "Ela troca o começo no escuro por dia claro, mas a folga até a devolução do carro some "
    "e a parada de comida vira drive-thru.",
    "Não existe trecho cênico possível na volta. Voltar pela SR-1 por Malibu dá "
    "quase a mesma distância, mas é mais lento e joga vocês no trânsito de véspera "
    "de Natal em Santa Monica com hora marcada para devolver o carro.",
    "A neblina do Salinas Valley é radiativa, de manhã, e some por volta das 10h. "
    "Se o painel mostrar visibilidade abaixo de 1,5 km no Salinas Valley, a conta muda: "
    "40 minutos a mais até clarear consomem a folga inteira, e aí o certo é sair às 5h50 "
    "para não perder nem a missa nem o voo.",
  ]},

 {"dia": "2026-12-27", "regiao": "oahu", "titulo": "A volta de Oʻahu",
  "cabecalho": "cerca de 180 km, o único dia com carro na ilha, poente às 17:58",
  "trechos": [
    ("10:00", "Retirar o carro", "1778 Ala Moana Blvd, a poucos minutos do hotel a "
     "pé", "20 min"),
    ("10:40", "Hanauma Bay", "Kalanianaʻole Hwy (SR-72). Entrada permitida só até "
     "13h30. Reserva abre às 7h de 25/12 e esgota em segundos", "1h30"),
    ("12:30", "Makapuʻu Point Lookout", "SR-72 contornando o extremo leste. O farol e "
     "a vista das ilhas Mānana", "30 min"),
    ("13:15", "Waimānalo e Kailua", "SR-72 e depois SR-61. Praia de areia branca e "
     "água rasa", "30 min"),
    ("13:45", "Almoço em Kailua e Lanikai", "Estacionar em Kailua e caminhar; "
     "Lanikai é bairro residencial com vaga escassa", "1h15"),
    ("15:00", "Kualoa", "Kamehameha Hwy (SR-83), a estrada da Windward Coast. "
     "Mokoliʻi (Chinaman's Hat) e os vales do Kualoa Ranch", "1h"),
    ("16:15", "Sunset Beach e Waimea Bay", "SR-83 até o North Shore. Ondas gigantes "
     "de inverno. Ver de cima, não entrar", "45 min"),
    ("17:30", "Poente e jantar em Haleʻiwa", "Food trucks e o camarão de Kahuku no "
     "caminho. Poente às 17:58", "1h30"),
    ("19:30", "Volta a Waikiki", "H-2 sul e H-1 leste, pelo centro da ilha",
     "60 km, 1h"),
  ],
  "notas": [
    "Se a Windward Coast estiver com chuva de manhã, inverter o laço: subir pelo centro "
    "até o North Shore primeiro e voltar por Kailua à tarde. O painel compara a "
    "chuva dos dois lados entre 8h e 13h e diz qual sentido pegar.",
    "Hanauma Bay é a única coisa do dia com hora marcada e só existe neste "
    "domingo: Hanauma Bay fecha segundas e terças, e no Natal e no Ano Novo. Se "
    "conseguirem a reserva, o laço começa por lá obrigatoriamente.",
    "O hotel cobra USD 51 de valet por noite, e vocês ficam com o carro uma noite "
    "só. Vale contar esse valor na conta do dia, porque estacionar em Waikiki na "
    "rua durante a noite não é opção.",
    "Devolução às 10h do dia 28 no aeroporto, não no centro. São endereços "
    "diferentes na reserva: retirada em Ala Moana, devolução no HNL.",
  ]},

 {"dia": "2026-12-29", "regiao": "bi", "titulo": "Kilauea, e a noite que decide",
  "cabecalho": "45 minutos de Hilo, ingresso de USD 30 por veículo e vale 7 dias",
  "trechos": [
    ("08:30", "Hilo até o parque", "SR-11 (Hawaii Belt Road) sudoeste", "47 km, 45 min"),
    ("09:15", "Crater Rim Drive e os mirantes", "Kīlauea Overlook, Keanakākoʻi, "
     "Steam Vents. Halemaʻumaʻu Crater é o palco dos episódios", "2h"),
    ("11:30", "Nāhuku (Thurston Lava Tube)", "Estacionamento lota cedo; ir antes do "
     "meio-dia", "45 min"),
    ("13:00", "Chain of Craters Road até o mar", "60 km ida e volta, descendo 1.100 m "
     "até a costa. Sem posto, sem água, sem sinal", "2h30"),
    ("16:00", "Volta a Hilo, jantar e descanso", "SR-11", "45 min"),
    ("19:00", "Se houver episódio ativo: voltar", "SR-11 outra vez, agora no escuro. "
     "O brilho da cratera só existe em erupção", "1h30 ida e volta"),
  ],
  "notas": [
    "Hoje o Kilauea está em ORANGE/WATCH e a sequência episódica iniciada em "
    "dezembro de 2024 continua. Cada episódio dura horas e as pausas duram dias, "
    "então nenhuma agenda alcança: o monitor do vulcão que já existe manda push "
    "quando uma fonte de lava começa.",
    "Esta é a decisão a proteger no roteiro. De Hilo o mirante fica a 45 minutos; "
    "depois da mudança para Kona, no dia 31, a mesma ida noturna passa a custar "
    "2h15 por trecho. Na prática só as noites de 28, 29 e 30 servem.",
    "O ingresso vale sete dias e vocês ficam na ilha até 4 de janeiro, então o "
    "bilhete não é o limite. A geografia é.",
    "Hilo chove em 72% dos dias desta janela, a maior taxa do roteiro inteiro. "
    "Nuvem encobrindo a cratera não é motivo para desistir: abre e fecha em "
    "minutos.",
  ]},

 {"dia": "2026-12-30", "regiao": "bi", "titulo": "Hamakua Coast de dia, Mauna Kea de noite",
  "cabecalho": "o cume a 4.207 m, poente às 17:53, e 4x4 obrigatório acima da VIS",
  "trechos": [
    ("08:30", "Hawaii Tropical Bioreserve Garden", "SR-19 norte, na Scenic Route de "
     "Onomea. USD 25 por pessoa", "1h30"),
    ("10:30", "Akaka Falls", "SR-19 até Honomū e subir. USD 10 por veículo. Trilha "
     "de 600 m em laço", "1h"),
    ("11:00", "Akaka Falls até Waipiʻo Valley Lookout", "SR-19 até Honokaʻa e SR-240. A "
     "descida do vale está fechada a quem não mora lá desde 2022: o mirante é o destino",
     "67 km, 1h10"),
    ("12:10", "Waipiʻo Valley Lookout", "Mirante sobre o vale e o mar", "40 min"),
    ("12:50", "Waipiʻo até Waimea", "SR-240 e SR-19 oeste. Em vez de voltar a Hilo, "
     "seguir para o lado de lá da montanha", "36 km, 40 min"),
    ("13:30", "Almoço e posto em Waimea", "Último posto de gasolina antes da Saddle "
     "Road. Comer e beber água: subir ao cume desidratado e de estômago vazio é "
     "como a altitude derruba as pessoas", "1h15"),
    ("14:45", "Waimea até a Mauna Kea VIS", "HI 190 (Mamalahoa Highway) por 22 km, HI 200 "
     "(Daniel K. Inouye Highway, a Saddle Road) por 38 km e Mauna Kea Access Road",
     "70 km, 1h15"),
    ("16:00", "Aclimatação na VIS, a 2.804 m", "Meia hora parado é o mínimo e é regra; "
     "com a folga do almoço dá para ficar 50 minutos", "50 min"),
    ("16:50", "Mauna Kea VIS até o Mauna Kea Summit", "13 km, os primeiros 7 sem asfalto "
     "e em rampa de 15%. Tração nas quatro rodas exigida, e o Wrangler da reserva "
     "atende", "30 min"),
    ("17:53", "Poente no cume", "Acima das nuvens, com a sombra da montanha se "
     "projetando no mar de nuvens a leste", "40 min"),
    ("18:30", "Descer para a VIS e olhar estrelas", "O cume tem de ser desocupado "
     "meia hora depois do poente. A observação de estrelas é na VIS, não lá em "
     "cima", "1h30"),
    ("20:00", "Volta a Hilo", "HI 200 (Saddle Road) leste, no escuro e sem iluminação",
     "73 km, 1h30"),
  ],
  "notas": [
    "O que fecha a estrada do cume é gelo, e gelo se antecipa: o painel vigia o "
    "nível de congelamento contra os 4.207 m do cume. Quando ele cai abaixo disso "
    "com chuva prevista, a estrada fecha e 4x4 não resolve. A média histórica do "
    "cume nesta janela é 5°C de máxima e 3,8°C abaixo de zero de mínima.",
    "Esta é a decisão flexível do roteiro, e por isso ela é que deve ceder. O cume "
    "alcança de Hilo em 1h30 e de Kona em cerca de 1h45, então existem sete noites "
    "candidatas entre 28/12 e 03/01. O painel escolhe a melhor.",
    "Por Waimea em vez de voltar a Hilo depois do Waipiʻo: medido no roteador, 285 km "
    "contra 321 km no dia e 40 minutos a menos ao volante. E Waimea tem onde almoçar "
    "e o último posto antes da Saddle Road, o que resolve as duas coisas que a volta "
    "a Hilo resolvia.",
    "Não há posto de gasolina na Saddle Road nem sinal de celular acima da VIS. "
    "Tanque cheio em Waimea, agasalho de verdade e água.",
    "Descer é o perigo real, não subir: freio de motor em marcha baixa, porque "
    "freio a disco superaquece e falha nos 15% de rampa. A locadora avisa, e a "
    "razão é essa.",
  ]},

 {"dia": "2026-12-31", "regiao": "bi", "titulo": "Travessia pelo sul, Hilo a Kona",
  "cabecalho": "200 km pelo caminho mais bonito, cerca de 4 horas com paradas",
  "trechos": [
    ("09:00", "Sair de Hilo", "SR-11 sudoeste, passando de novo pela borda do "
     "parque", "saída"),
    ("10:30", "Punaluʻu Black Sand Beach", "Areia vulcânica preta. Tartarugas verdes "
     "descansando ao sol são comuns, e é proibido tocar ou chegar perto", "1h"),
    ("11:45", "Desvio opcional a Ka Lae, o South Point", "20 km de estrada secundária "
     "cada trecho. O ponto mais ao sul dos Estados Unidos", "1h30 extra"),
    ("13:00", "Subida pela Kona Coast", "SR-11 pelos cafezais de Captain Cook e "
     "Kealakekua", "1h30"),
    ("15:00", "Kailua-Kona e o centro histórico", "Antes do check-in, se sobrar "
     "tempo", "1h"),
    ("16:00", "Check-in no Outrigger Kona, em Keauhou", "Luau do hotel às 17h",
     "chegada"),
  ],
  "notas": [
    "Se a noite do Kilauea não aconteceu nos dias 28, 29 ou 30, hoje é a última "
    "chance barata: o parque fica no caminho, a 1h30 de Hilo, e dá para parar no "
    "fim da tarde antes de seguir para Kona. Depois disso a ida passa a custar 4h30 "
    "de carro, saindo do resort.",
  ]},
]

# ---------------------------------------------------------------- missas
# Conferido em 13/09/2026 nos sites das proprias paroquias (e, onde o site
# bloqueia leitura, no diretorio oficial da diocese). Agregadores erraram quatro
# vezes: vigilia de Kona (e 16h, nao 17h), Little Blue Church de Keauhou (esta
# fechada), catedral de Monterey (7h30, nao 7h45) e os dias de semana de
# Waikiki. Natal e Ano Novo de 2026 ainda nao foram publicados: onde aparece
# "2025", e o horario do ano passado, a confirmar em dezembro.
IGREJAS = {
    "visitation": {
        "nome": "Church of the Visitation", "lugar": "Westchester, Los Angeles",
        "horarios": "segunda a sexta 8h · sábado 17h · domingo 8h, 9h30 e 11h",
        "busca": "Church of the Visitation, 6561 W 88th St, Los Angeles",
        "fonte": "https://www.visitationchurch-la.com/"},
    "sancarlos": {
        "nome": "San Carlos Cathedral (Royal Presidio Chapel)", "lugar": "Monterey",
        "horarios": "segunda a sexta 7h30 e 12h (exceto feriados) · sábado 16h · "
                    "domingo 7h30, 9h, 10h30, 12h em espanhol e 17h30",
        "busca": "San Carlos Cathedral, 500 Church St, Monterey, CA",
        "fonte": "https://sancarloscathedral.org/mass-schedule/"},
    "angela": {
        "nome": "St. Angela Merici", "lugar": "Pacific Grove",
        "horarios": "terça a sexta 8h30 · sábado 17h · domingo 8h, 10h e 12h",
        "busca": "St. Angela Merici Catholic Church, Pacific Grove, CA",
        "fonte": "https://stangelamericipacificgrove.org/mass-times"},
    "carmel": {
        "nome": "Carmel Mission Basilica", "lugar": "Carmel-by-the-Sea",
        "horarios": "quarta a sexta 12h · sábado 17h30 · domingo 9h e 11h",
        "busca": "Carmel Mission Basilica, 3080 Rio Rd, Carmel, CA",
        "fonte": "https://carmelmission.org/mass-and-events/"},
    "olacatedral": {
        "nome": "Cathedral of Our Lady of the Angels", "lugar": "Downtown Los Angeles",
        "horarios": "segunda a sexta 7h e 12h10 · domingo 8h, 10h e 12h30 em espanhol",
        "busca": "Cathedral of Our Lady of the Angels, 555 W Temple St, Los Angeles",
        "fonte": "https://olacathedral.org/mass-schedule"},
    "monica": {
        "nome": "St. Monica", "lugar": "Santa Monica",
        "horarios": "segunda a sexta 7h e 12h10 · em feriado, uma missa só, às 9h30",
        "busca": "St. Monica Catholic Community, 725 California Ave, Santa Monica",
        "fonte": "https://stmonica.net/"},
    "augustine": {
        "nome": "St. Augustine by-the-Sea", "lugar": "Waikiki",
        "horarios": "terça a sábado 7h (segunda é só culto de comunhão) · sábado 17h · "
                    "domingo 6h, 8h, 10h e 17h",
        "busca": "St. Augustine by-the-Sea, 130 Ohua Ave, Honolulu",
        "fonte": "https://staugustinebythesea.com/"},
    "catedralhnl": {
        "nome": "Cathedral Basilica of Our Lady of Peace",
        "lugar": "Kamiano Center, 1159 Fort Street Mall, Downtown Honolulu",
        "horarios": "segunda a sexta 6h30 e 12h · sábado 7h, 12h e 17h · "
                    "domingo 8h, 10h, 12h e 17h (missas no Kamiano Center, ao lado da catedral)",
        "busca": "Kamiano Center, 1159 Fort Street Mall, Honolulu",
        "fonte": "https://honolulucathedral.org/mass-schedule/"},
    "theresa": {
        "nome": "Co-Cathedral of St. Theresa", "lugar": "Honolulu",
        "horarios": "segunda a quinta 6h30 · sexta e sábado 8h · sábado 17h · "
                    "domingo 6h15, 8h, 10h30 e 18h",
        "busca": "Co-Cathedral of Saint Theresa, 712 N School St, Honolulu",
        "fonte": "https://www.catholichawaii.org/parish-listing/co-cathedral-of-saint-theresa/?viewFull=true"},
    "joseph": {
        "nome": "St. Joseph", "lugar": "Hilo",
        "horarios": "segunda a sexta 6h e 12h15 · sábado 7h e 17h · domingo 7h, 9h, 11h45 e 18h",
        "busca": "St. Joseph Catholic Church, 43 Kapiolani St, Hilo",
        "fonte": "https://stjoehilo.com/"},
    "michael": {
        "nome": "St. Michael the Archangel", "lugar": "Aliʻi Drive, Kailua-Kona",
        "horarios": "todos os dias 7h · sábado 16h · domingo 7h, 9h, 12h em espanhol e 16h",
        "busca": "St. Michael the Archangel Church, 75-5769 Alii Dr, Kailua-Kona",
        "fonte": "https://saintmichaelparishkona.org/our-parish/mass-times-and-locations/"},
    "rose": {
        "nome": "St. Rose of Lima", "lugar": "Paso Robles, na US 101",
        "horarios": "segunda a sexta 8h30 · sábado 8h e 17h · domingo 8h e 10h, e 13h e 18h em espanhol",
        "busca": "St. Rose of Lima Catholic Church, Paso Robles, CA",
        "fonte": "http://saintrosechurch.org/"},
    "sorrows": {
        "nome": "Our Lady of Sorrows", "lugar": "Santa Barbara",
        "horarios": "dias de semana 12h10, segundo o MassTimes (o site da paróquia bloqueia leitura)",
        "busca": "Our Lady of Sorrows Catholic Church, Santa Barbara, CA",
        "fonte": "https://masstimes.org/"},
    "usc": {
        "nome": "Our Savior e USC Caruso Catholic Center", "lugar": "University Park, Los Angeles",
        "horarios": "semestre de outono: segunda a sexta 21h · sábado 9h · domingo 10h, 17h e 20h",
        "busca": "USC Caruso Catholic Center, 844 W 32nd St, Los Angeles",
        "fonte": "https://www.catholictrojan.org/mass"},
    "santuariopty": {
        "nome": "Santuario Nacional del Corazón de María", "lugar": "Ciudad de Panamá",
        "horarios": "segunda a sexta 6h30, 8h30 e 17h30 (quinta 17h15), e 7h30 às segundas na cripta · "
                    "sábado 6h30, 8h30, 16h e 18h · domingo 6h30, 8h30, 10h30, 12h30, 16h, 18h e 20h",
        "busca": "Santuario Nacional del Corazón de María, Ciudad de Panamá",
        "fonte": "https://santuarionacional.net/sacramentos/"},
    "stjosephhou": {
        "nome": "St. Joseph Catholic Church", "lugar": "Houston",
        "horarios": "segunda, quarta e sexta 12h10 · terça 17h45 · quinta 7h · quarta e quinta 18h30 "
                    "em espanhol · sábado 17h · domingo 10h15 e 18h30",
        "busca": "St. Joseph Catholic Church, 1505 Kane St, Houston, TX",
        "fonte": "http://www.saintjoseph.org/en"},
    "stjameshou": {
        "nome": "St. James the Apostle", "lugar": "Spring, perto do aeroporto IAH",
        "horarios": "terça a sexta 8h · sábado 17h · domingo 7h30, 9h, 11h e 13h em espanhol",
        "busca": "St. James the Apostle Catholic Church, Spring, TX",
        "fonte": "http://www.stjta.org/"},
    "nazarebsb": {
        "nome": "Paróquia Nossa Senhora de Nazaré", "lugar": "Lago Sul, QI 01, Brasília",
        "horarios": "terça a quinta 19h30 · sábado 18h30 · domingo 9h30 e 19h30",
        "busca": "Paróquia Nossa Senhora de Nazaré, SHIS QI 01, Lago Sul, Brasília",
        "fonte": "https://arqbrasilia.com.br/todas_paroquias/nossa-senhora-de-nazare-lago-sul/"},
    "domboscobsb": {
        "nome": "Santuário São João Bosco", "lugar": "Asa Sul, Brasília",
        "horarios": "segunda a sexta 7h e 18h30 · sábado 12h e 18h · domingo 8h, 11h, 18h e 19h30",
        "busca": "Santuário Dom Bosco, Brasília",
        "fonte": "https://www.salesianos.br/institucional/santuario-sao-joao-bosco-horario-das-missas"},
    "catedralbsb": {
        "nome": "Catedral Metropolitana Nossa Senhora Aparecida", "lugar": "Esplanada, Brasília",
        "horarios": "terça a sexta 12h15 · sábado 17h · domingo 8h, 10h30 e 18h",
        "busca": "Catedral Metropolitana de Brasília",
        "fonte": "https://catedral.org.br/veja-as-orientacoes-para-participar-da-santa-missa-na-catedral.html"},
    "stgregoryhou": {
        "nome": "St. Gregory the Great", "lugar": "Houston, 20 km do aeroporto IAH",
        "horarios": "quarta a sexta 7h e terça 18h, segundo o MassTimes e o CatholicMassTime "
                    "(o site da paróquia bloqueia leitura)",
        "busca": "St. Gregory the Great Catholic Church, 10500 Nold Rd, Houston, TX",
        "fonte": "https://masstimes.org/"},
    "benedict": {
        "nome": "St. Benedict's Painted Church", "lugar": "Hōnaunau, South Kona",
        "horarios": "terça a sexta 7h · dias de preceito 7h · domingo 8h",
        "busca": "St. Benedict's Painted Church, Captain Cook, HI",
        "fonte": "https://www.catholichawaii.org/parish-listing/saint-benedict/?viewFull=true"},
}

# rec: a que encaixa melhor no dia. alts: as outras possiveis. sem: quando
# nenhuma cabe, e por que. confirmar: horario de 2025 ou nao publicado.
MISSAS = [
    {"dia": "2026-12-20", "regiao": "ca", "liturgia": "4º Domingo do Advento", "preceito": True,
     "rec": {"hora": "19h30", "igreja": "nazarebsb", "dist": "11 km do aeroporto de Brasília",
             "porque": "O voo para o Panamá sai às 2h de 21/12. Missa, jantar e aeroporto às 23h, "
                       "com folga."},
     "sem": "Se preferirem manter a missa das 7h que já está na agenda de vocês, o resto do "
            "domingo fica livre para as malas.",
     "alts": [{"hora": "18h ou 19h30", "igreja": "domboscobsb", "nota": "No caminho do aeroporto."},
              {"hora": "18h", "igreja": "catedralbsb", "nota": ""}]},
    {"dia": "2026-12-21", "regiao": "ca", "liturgia": "Advento",
     "rec": {"hora": "8h30", "igreja": "santuariopty", "dist": "22 km do aeroporto de Tocumen",
             "porque": "Escala no Panamá das 6h às 11h35. Pouso, imigração (brasileiro entra sem "
                       "visto), táxi de 40 a 50 minutos no trânsito da manhã, missa, e volta a "
                       "Tocumen por volta de 9h50 para despachar e embarcar para Houston."},
     "aviso": "Voltar a Tocumen até 9h50 para despachar e embarcar às 11h35.",
     "sem": "Os localizadores da ida são diferentes (Brasília-Panamá e Panamá-Houston): se a "
            "bagagem não vier despachada direto, as malas saem com vocês na imigração, e o "
            "despacho para Houston abre por volta de 8h35. Em Houston, das 14h54 às 16h30, não "
            "dá para sair do aeroporto.",
     "alts": [{"hora": "7h30", "igreja": "santuariopty",
               "nota": "Na cripta, só às segundas. Se a imigração for rápida, dá mais folga na volta."},
              {"hora": "21h", "igreja": "usc",
               "nota": "Plano B, na chegada a Los Angeles (pouso às 18h10). É o horário do semestre, "
                       "e 21/12 é férias na USC: confirmar em dezembro."}]},
    {"dia": "2026-12-22", "regiao": "ca", "liturgia": "Advento",
     "rec": {"hora": "8h", "igreja": "visitation", "dist": "5 km do Holiday Inn LAX",
             "porque": "Café do hotel antes. A missa termina por volta de 8h35 e as locadoras "
                       "ficam a 10 minutos de aplicativo: dá para pegar o carro às 9h."},
     "descartadas": "Old Mission Santa Barbara só celebra às 8h, quando vocês ainda estão em "
                    "Los Angeles. Não há missa ao meio-dia em Santa Barbara nem à noite em "
                    "Pacific Grove."},
    {"dia": "2026-12-23", "regiao": "ca", "liturgia": "Advento",
     "rec": {"hora": "7h30", "igreja": "sancarlos", "dist": "5 km da Gosby House Inn",
             "porque": "Igreja fundada por São Junípero Serra em 1770. Dá tempo de voltar para o "
                       "café da pousada e pegar a fila do aquário às 9h45."},
     "alts": [{"hora": "8h30", "igreja": "angela",
               "nota": "A 1 km, dá para ir a pé, mas aperta a fila do aquário."},
              {"hora": "12h", "igreja": "carmel",
               "nota": "Onde está sepultado São Junípero Serra. Obriga a refazer a tarde; "
                       "melhor visitar a basílica 20 minutos a caminho de Point Lobos, que "
                       "fica colada na SR 1."}]},
    {"dia": "2026-12-24", "regiao": "ca", "liturgia": "Véspera de Natal",
     "rec": {"hora": "8h30", "igreja": "rose", "dist": "190 km da Gosby House Inn",
             "porque": "Saindo de Pacific Grove às 6h10, a missa cabe no caminho e ainda sobram "
                       "uns 45 minutos antes de devolver o carro às 15h. O roteiro do dia já está "
                       "montado assim."},
     "alts": [{"hora": "7h30", "igreja": "sancarlos",
               "nota": "A 5 km da pousada e já com dia claro. Mas a saída vai para 8h05, a folga até "
                       "a devolução do carro some e a parada de comida vira drive-thru."},
              {"hora": "12h10", "igreja": "sorrows",
               "nota": "Na hora do almoço, no caminho. Horário do MassTimes, a confirmar: em véspera "
                       "de Natal a missa do meio-dia pode ser suspensa."}]},
    {"dia": "2027-01-05", "regiao": "ca", "liturgia": "São João Neumann",
     "rec": {"hora": "12h10", "igreja": "olacatedral", "dist": "de aplicativo, sem carro",
             "porque": "Para o programa Griffith Observatory ao pôr do sol: missa na catedral, "
                       "almoço no Grand Central Market e Griffith à tarde, tudo do mesmo lado "
                       "da cidade."},
     "alts": [{"hora": "12h10", "igreja": "monica",
               "nota": "Se o programa for Santa Monica e Venice Beach."},
              {"hora": "8h", "igreja": "visitation",
               "nota": "Se o programa for o Getty Center, que abre às 10h. Perto do hotel."},
              {"hora": "7h", "igreja": "olacatedral", "nota": "Também às 7h em St. Monica."}]},
    {"dia": "2027-01-06", "regiao": "ca", "liturgia": "Tempo do Natal", "confirmar": True,
     "rec": {"hora": "7h", "igreja": "stgregoryhou", "dist": "20 km do aeroporto IAH",
             "porque": "Pouso em Houston às 5h52 vindo de Los Angeles e embarque para o Panamá às "
                       "9h34. Aplicativo às 6h15, missa às 7h, volta ao aeroporto por volta de 8h05 "
                       "para passar de novo pela segurança. É a única missa possível no dia: no "
                       "Panamá a escala é de 1h42 e a chegada a Brasília já é 07/01."},
     "aviso": "Só sair do aeroporto se o voo pousar no horário. Com mais de 20 minutos de atraso, "
              "a volta para o voo das 9h34 fica arriscada."},
    {"dia": "2026-12-24", "regiao": "oahu", "liturgia": "Noite de Natal", "badge": "opcional",
     "confirmar": True,
     "sem": "A missa do dia 24 é de manhã, em Paso Robles (aba Golden Coast). Se quiserem também a "
            "Missa do Galo em Honolulu, dá tempo: vocês pousam às 21h31.",
     "alts": [{"hora": "0h (cânticos às 23h30)", "igreja": "catedralhnl",
               "nota": "Horário de 2025, a 5 km do hotel, de táxi. Em Waikiki as missas da noite "
                       "foram às 17h e às 20h, antes do pouso."}]},
    {"dia": "2026-12-25", "regiao": "oahu", "liturgia": "Natal do Senhor", "preceito": True,
     "confirmar": True,
     "rec": {"hora": "10h", "igreja": "augustine", "dist": "2 km a pé do The Ambassador",
             "porque": "Fica no caminho do Kapiʻolani Park, que já é o plano do dia de Natal."},
     "alts": [{"hora": "6h, 8h ou 17h", "igreja": "augustine",
               "nota": "Horários de 2025, a confirmar em dezembro."}]},
    {"dia": "2026-12-26", "regiao": "oahu", "liturgia": "Santo Estêvão",
     "rec": {"hora": "17h", "igreja": "augustine", "dist": "2 km a pé",
             "porque": "Vigília da Sagrada Família, na volta de Pearl Harbor. Já vale pelo "
                       "domingo e mantém o Diamond Head às 6h."},
     "alts": [{"hora": "7h", "igreja": "augustine",
               "nota": "Só se o Diamond Head ficar para as 8h: às 7h vocês estariam na trilha."}]},
    {"dia": "2026-12-27", "regiao": "oahu", "liturgia": "Sagrada Família", "preceito": True,
     "rec": {"hora": "8h", "igreja": "augustine", "dist": "2 km a pé",
             "porque": "Antes de pegar o carro às 10h na Ala Moana Blvd. O preceito já está "
                       "cumprido na vigília; esta é a missa do dia."},
     "alts": [{"hora": "6h", "igreja": "augustine", "nota": "Se preferirem começar mais cedo."}]},
    {"dia": "2026-12-28", "regiao": "oahu", "liturgia": "Santos Inocentes",
     "rec": {"hora": "6h30", "igreja": "catedralhnl", "dist": "5 km, já de carro e com as malas",
             "porque": "St. Augustine não tem missa às segundas. A catedral fica no caminho do "
                       "aeroporto, onde o carro é devolvido às 10h, e foi nela que São Damião de "
                       "Molokai foi ordenado. Em Hilo não há missa à tarde."},
     "alts": [{"hora": "6h30", "igreja": "theresa",
               "nota": "Mais perto da H-1, também no caminho do aeroporto."}]},

    {"dia": "2026-12-29", "regiao": "bi", "liturgia": "Oitava do Natal",
     "rec": {"hora": "6h", "igreja": "joseph", "dist": "3 km do Castle Hilo Hawaiian",
             "porque": "Café depois e saída para o Hawaii Volcanoes National Park às 8h30. "
                       "Seis da manhã em Hilo são oito no relógio que vocês trazem da Golden Coast."},
     "alts": [{"hora": "12h15", "igreja": "joseph",
               "nota": "Só se o dia no parque for encurtado."}]},
    {"dia": "2026-12-30", "regiao": "bi", "liturgia": "Oitava do Natal",
     "rec": {"hora": "6h", "igreja": "joseph", "dist": "3 km",
             "porque": "É o único horário que cabe no dia mais longo: Hamakua Coast, Waimea e "
                       "Mauna Kea Summit, com volta a Hilo por volta de 20h."}},
    {"dia": "2026-12-31", "regiao": "bi", "liturgia": "Oitava do Natal",
     "rec": {"hora": "6h", "igreja": "joseph", "dist": "3 km",
             "porque": "Antes da saída para Kona pelo sul, às 9h."}},
    {"dia": "2027-01-01", "regiao": "bi", "liturgia": "Santa Maria, Mãe de Deus",
     "preceito": True, "confirmar": True,
     "rec": {"hora": "7h", "igreja": "benedict", "dist": "14 km ao sul do Outrigger",
             "porque": "St. Michael não publicou horário de 1º de janeiro nem em 2025. A Painted "
                       "Church celebra às 7h em dia de preceito, com vista para a Kealakekua Bay."},
     "alts": [{"hora": "a confirmar", "igreja": "michael",
               "nota": "Se houver missa mais tarde, combina melhor com o dia sem despertador."}]},
    {"dia": "2027-01-02", "regiao": "bi", "liturgia": "São Basílio e São Gregório",
     "rec": {"hora": "7h", "igreja": "michael", "dist": "12 km pela Aliʻi Drive",
             "porque": "Dá tempo de voltar para o catamarã e deixa a noite livre para o snorkel "
                       "com arraias-manta em qualquer horário."},
     "alts": [{"hora": "16h", "igreja": "michael",
               "nota": "Vigília da Epifania, já vale pelo domingo. Pede o snorkel das 20h15."}]},
    {"dia": "2027-01-03", "regiao": "bi", "liturgia": "Epifania do Senhor", "preceito": True,
     "rec": {"hora": "16h", "igreja": "michael", "dist": "12 km",
             "porque": "Praia de manhã, com luz melhor e mar mais calmo. A missa é no centro "
                       "histórico de Kailua-Kona, onde o roteiro já fecha o dia, com o pôr do sol "
                       "e o jantar na Aliʻi Drive em seguida."},
     "alts": [{"hora": "7h ou 9h", "igreja": "michael", "nota": "Antes de ir para a praia."}]},
    {"dia": "2027-01-04", "regiao": "bi", "liturgia": "Santa Isabel Ana Seton",
     "rec": {"hora": "7h", "igreja": "michael", "dist": "12 km",
             "porque": "Café depois e a manhã livre até entregar o carro às 14h no aeroporto de Kona."}},
]


# ---------------------------------------------------------------- rotas
# Paradas na ORDEM em que voces passam, com coordenadas conferidas no
# OpenStreetMap em 13/09/2026 (o Hōlei Sea Arch estava 4 km fora no chute).
# "trajeto": True = dia de estrada do roteiro, desenhado em todo mapa de aviso
# daquela regiao. As outras sao os recortes que as decisoes usam.
_GOSBY = (36.6216, -121.9196, "Gosby House Inn")
# lado leste, onde ficam as locadoras; o centro do aeroporto fazia a rota contornar a pista
_LAX = (33.9491, -118.3868, "LAX")
# Ponto de passagem SEM nome (nao vira marcador): prende a rota na US 101 pela
# orla. Livre, o roteador corta Santa Barbara-Buellton pela CA 154 (San Marcos
# Pass), 22 km mais curta e por dentro da serra, que nao e o que o roteiro quer.
_ORLA_101 = (34.4630, -120.0710, None)
_HILO = (19.7281, -155.0667, "Castle Hilo Hawaiian Hotel")
ROTAS = {
    "ida_2212": {
        "dia": "2026-12-22", "regiao": "ca", "trajeto": True,
        "titulo": "LAX até Pacific Grove",
        "resumo": "PCH até Malibu, US 101 pela orla até Santa Barbara e pelo interior até Salinas",
        "paradas": [_LAX, (34.0380, -118.8745, "El Matador State Beach"),
                    (34.4100, -119.6858, "Santa Barbara"), _ORLA_101,
                    (35.1297, -120.6326, "Pismo Beach"), _GOSBY],
        "passagens": [(35.6266, -120.6910, "Paso Robles"), (36.6777, -121.6555, "Salinas")]},
    "peninsula_2312": {
        "dia": "2026-12-23", "regiao": "ca", "trajeto": True,
        "titulo": "Monterey Peninsula e Bixby Bridge",
        "resumo": "17-Mile Drive, Carmel-by-the-Sea, Point Lobos e SR 1 até Bixby Bridge",
        "paradas": [_GOSBY, (36.6181, -121.9017, "Monterey Bay Aquarium"),
                    (36.5687, -121.9652, "Lone Cypress"), (36.5147, -121.9428, "Point Lobos"),
                    (36.3716, -121.9019, "Bixby Bridge"), _GOSBY],
        "passagens": [(36.5552, -121.9233, "Carmel-by-the-Sea")]},
    "volta_2412": {
        "dia": "2026-12-24", "regiao": "ca", "trajeto": True,
        "titulo": "Pacific Grove até LAX",
        "resumo": "US 101 do começo ao fim, San Fernando Valley e I-405 até o LAX",
        # ponto na propria US 101: o centro de Salinas desviava a rota e dava 564 km
        "paradas": [_GOSBY, (36.6400, -121.6230, "Salinas"), _ORLA_101, _LAX],
        "passagens": [(35.6266, -120.6910, "Paso Robles"), (34.6136, -120.1929, "Buellton"),
                      (34.4100, -119.6858, "Santa Barbara"), (34.2805, -119.2945, "Ventura")]},
    "oahu_2712": {
        "dia": "2026-12-27", "regiao": "oahu", "trajeto": True,
        "titulo": "A volta de Oʻahu",
        "resumo": "SR 72 pela costa leste, SR 83 pela Windward Coast e North Shore, H-2 e H-1 na volta",
        "paradas": [(21.2855, -157.8375, "Alamo, Ala Moana Blvd"), (21.2696, -157.6938, "Hanauma Bay"),
                    (21.3110, -157.6490, "Makapuʻu Point"), (21.3966, -157.7259, "Kailua Beach Park"),
                    (21.5130, -157.8367, "Kualoa Regional Park"), (21.6708, -158.0457, "Sunset Beach"),
                    (21.6414, -158.0668, "Waimea Bay"), (21.5936, -158.1045, "Haleʻiwa"),
                    (21.2842, -157.8323, "The Ambassador Hotel Waikiki")]},
    "kilauea_2912": {
        "dia": "2026-12-29", "regiao": "bi", "trajeto": True,
        "titulo": "Hawaii Volcanoes National Park",
        "resumo": "SR 11 até o parque, Crater Rim Drive e Chain of Craters Road até o mar",
        "paradas": [_HILO, (19.4296, -155.2571, "Kīlauea Visitor Center"),
                    (19.4145, -155.2373, "Nāhuku"), (19.2958, -155.0957, "Hōlei Sea Arch"), _HILO]},
    "hamakua_3012": {
        "dia": "2026-12-30", "regiao": "bi", "trajeto": True,
        "titulo": "Hamakua Coast e Mauna Kea Summit",
        "resumo": "SR 19 pela Hamakua Coast, almoço em Waimea, HI 190, Saddle Road (HI 200) e Mauna Kea Access Road",
        "paradas": [_HILO, (19.8547, -155.1536, "Akaka Falls State Park"),
                    (20.1180, -155.5844, "Waipiʻo Valley Lookout"), (20.0230, -155.6718, "Waimea"),
                    (19.7607, -155.4563, "Mauna Kea VIS"), (19.8207, -155.4681, "Mauna Kea Summit"), _HILO]},
    "sul_3112": {
        "dia": "2026-12-31", "regiao": "bi", "trajeto": True,
        "titulo": "Hilo até Kona pelo sul",
        "resumo": "SR 11 contornando o sul da ilha, passando pela entrada do parque",
        "paradas": [_HILO, (19.1361, -155.5046, "Punaluʻu Black Sand Beach"),
                    (19.5584, -155.9647, "Outrigger Kona Resort")]},
    # recortes das decisoes
    "bixby": {
        "dia": "2026-12-23", "regiao": "ca", "titulo": "Carmel-by-the-Sea até Bixby Bridge",
        "resumo": "SR 1 sul, passando por Point Lobos e Rocky Creek",
        "paradas": [(36.5552, -121.9233, "Carmel-by-the-Sea"), (36.5147, -121.9428, "Point Lobos"),
                    (36.3716, -121.9019, "Bixby Bridge")]},
    "mk_subida": {
        "dia": "2026-12-30", "regiao": "bi", "titulo": "Hilo até Mauna Kea Summit",
        "resumo": "Saddle Road (SR 200), Mauna Kea VIS e os 13 km da Mauna Kea Access Road",
        "paradas": [_HILO, (19.7607, -155.4563, "Mauna Kea VIS"), (19.8207, -155.4681, "Mauna Kea Summit")]},
    "kilauea_noite": {
        "dia": "2026-12-29", "regiao": "bi", "titulo": "Hilo até Kīlauea Caldera",
        "resumo": "SR 11, 45 minutos por trecho",
        "paradas": [_HILO, (19.4296, -155.2571, "Kīlauea Visitor Center")]},
    "snorkel": {
        "dia": "2027-01-02", "regiao": "bi", "barco": True, "titulo": "Keauhou Bay até Kealakekua Bay",
        "resumo": "catamarã pela costa de Kona",
        "paradas": [(19.5613, -155.9643, "Keauhou Bay"), (19.4771, -155.9271, "Kealakekua Bay")]},
    "northshore": {
        "dia": "2026-12-27", "regiao": "oahu", "titulo": "Haleʻiwa até Sunset Beach",
        "resumo": "Kamehameha Hwy (SR 83) pelo North Shore",
        "paradas": [(21.5936, -158.1045, "Haleʻiwa"), (21.6414, -158.0668, "Waimea Bay"),
                    (21.6708, -158.0457, "Sunset Beach")]},
}
ROTA_DO_DIA = {r["dia"]: rid for rid, r in ROTAS.items() if r.get("trajeto")}
ROTA_DA_DECISAO = {"mk_cume": "mk_subida", "kilauea": "kilauea_noite",
                   "oahu_sentido": "oahu_2712", "ca_ida": "ida_2212", "ca_volta": "volta_2412",
                   "bixby": "bixby", "snorkel": "snorkel", "northshore": "northshore"}


# Condados e lugares que importam para a rota da California. O boletim da
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
    ponto de grade encosta acima e o Mauna Kea Summit vira uma colina."""
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
                "zonas": p.get("affectedZones") or [],
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

def push_ntfy(titulo, corpo, prioridade="default", tags="", anexo=""):
    if not NTFY_TOPIC:
        print("aviso: NTFY_TOPIC nao definido; push pulado")
        return
    cab = {"Title": titulo.encode("ascii", "replace").decode("ascii"),
           "Priority": prioridade, "Click": LINK_SITE}
    if tags:
        cab["Tags"] = tags
    if anexo:
        cab["Attach"] = anexo        # o ntfy baixa a imagem do PythonAnywhere e mostra no push
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


def push_telegram_foto(jpeg, legenda_html, urgente=False):
    """Mapa por foto no Telegram. Legenda em HTML, no maximo 1024 caracteres."""
    if not (TG_TOKEN and TG_CHAT) or not jpeg:
        return
    lim = "----tg" + uuid.uuid4().hex
    partes = []
    for k, v in (("chat_id", str(TG_CHAT)), ("caption", legenda_html[:1024]),
                 ("parse_mode", "HTML"), ("disable_notification", "false" if urgente else "true")):
        partes.append(f'--{lim}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8"))
    partes.append((f'--{lim}\r\nContent-Disposition: form-data; name="photo"; filename="mapa.jpg"\r\n'
                   "Content-Type: image/jpeg\r\n\r\n").encode() + jpeg + b"\r\n")
    corpo = b"".join(partes) + f"--{lim}--\r\n".encode()
    req = Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto", data=corpo, method="POST",
                  headers={"Content-Type": f"multipart/form-data; boundary={lim}"})
    try:
        with urlopen(req, timeout=60) as r:
            print(f"telegram foto enviada ({r.getcode()}): {legenda_html[:60]}")
    except Exception as e:  # noqa: BLE001
        print(f"ERRO na foto do telegram: {e}")


def upload_pa(conteudo, nome="index.html"):
    if not PA_TOKEN:
        print("aviso: PA_TOKEN nao definido; upload pulado")
        return False
    dest = f"/home/{PA_USER}/{PA_DIR}/{nome}"
    url = f"{PA_API}/api/v0/user/{PA_USER}/files/path{dest}"
    data = conteudo if isinstance(conteudo, bytes) else conteudo.encode("utf-8")
    lim = "----pa" + uuid.uuid4().hex
    corpo = ((f"--{lim}\r\n"
              f'Content-Disposition: form-data; name="content"; filename="{nome.split("/")[-1]}"\r\n'
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
# O cume alcanca dos dois lados: de Hilo pela Saddle Road sao 1h30, de
# Kona/Waikoloa cerca de 1h45. Sete noites candidatas.
NOITES_CUME = ["2026-12-28", "2026-12-29", "2026-12-30", "2026-12-31",
               "2027-01-01", "2027-01-02", "2027-01-03"]
# A cratera nao: de Hilo sao 45 min por trecho, de Kona 2h15. Uma ida noturna
# saindo de Kona vira uma viagem de 5 horas. Na pratica so as noites de Hilo
# contam, e sao tres.
NOITES_CRATERA = ["2026-12-28", "2026-12-29", "2026-12-30"]
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

    dia_mk = melhor_noite(prev, "mk_cume", NOITES_CUME, 15, 21, av_mk)
    add("mk_cume", "Mauna Kea Summit: poente e estrelas", dia_mk, "15h às 21h",
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

    dia_kil = melhor_noite(prev, "kilauea", NOITES_CRATERA, 17, 22, av_kil)
    add("kilauea", "Kilauea Caldera ao anoitecer", dia_kil, "17h às 22h",
        "Aviso urgente se o USGS puser o Kilauea em ORANGE ou RED durante a viagem.",
        J("kilauea", dia_kil, 17, 22), av_kil,
        "Só as três noites de Hilo servem: 28, 29 e 30/12, a 45 minutos do "
        "mirante. Depois da mudança para Kona, no dia 31, a mesma ida noturna "
        "passa a custar 2h15 por trecho, e 5 horas de carro no escuro. Se a "
        "cratera estiver ativa, esta é a decisão a proteger no roteiro, não o "
        "Mauna Kea, que alcança dos dois lados.")

    # 3. Sentido da volta de Oahu: barlavento chove de manha; se chover, inverte.
    lan = J("lanikai", "2026-12-27", 8, 13)
    nor = J("northshore", "2026-12-27", 8, 13)

    def av_oahu(w):
        cl = (lan or {}).get("chuva") or 0
        cn = (nor or {}).get("chuva") or 0
        num = f"chuva de manhã: Windward Coast {cl:.1f} mm, North Shore {cn:.1f} mm"
        if cl > cn + 1.5:
            return "atencao", ("Windward Coast mais molhada. Inverter o laço: subir pelo "
                               "centro até o North Shore e voltar por Kailua à tarde."), num
        return "bom", ("Windward Coast igual ou melhor que o North Shore. Seguir o "
                       "sentido normal: leste primeiro, North Shore no fim."), num

    add("oahu_sentido", "Sentido da volta de Oʻahu", "2026-12-27", "manhã",
        "Inverte o laço se a Windward Coast tiver 1,5 mm mais de chuva que o North "
        "Shore entre 8h e 13h.",
        lan, av_oahu,
        "Se quiserem Hanauma Bay, a reserva abre às 7h de 25/12 e esgota em "
        "segundos; a entrada só vale até 13h30, e aí o laço começa por lá de "
        "qualquer maneira. Carro às 10h na Ala Moana Blvd e devolução às 10h "
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
        "PCH de Santa Monica a Malibu, 101 pela orla de Ventura a Gaviota, 101 pelo "
        "interior até Pacific Grove. Em Santa Barbara, recusar a CA 154 que o GPS "
        "sugere. Big Sur não entra na ida: seriam 2h30 a mais e no escuro.")

    # 5. Volta, 24/12. O risco da madrugada aqui e neblina no vale, nao chuva.
    def av_volta(w):
        vis = w["vis"] if w["vis"] is not None else 20
        num = (f"visibilidade mínima 6h-9h {vis:.1f} km, chuva {w['chuva'] or 0:.1f} mm")
        if vis < 1.5:
            return "ruim", ("Neblina fechada no Salinas Valley. Sair às 5h50 e contar "
                            "com 40 minutos a mais até clarear."), num
        if vis < 5:
            return "atencao", ("Neblina no vale. Farol baixo e sem pressa nos "
                               "primeiros 80 km."), num
        return "bom", "Vale limpo. 101 direto até o LAX.", num

    add("ca_volta", "Volta: Pacific Grove ao LAX", "2026-12-24", "6h às 9h",
        "Sair às 5h50 em vez das 6h10 se a visibilidade no Salinas Valley cair abaixo "
        "de 1,5 km.",
        J("salinas", "2026-12-24", 6, 9), av_volta,
        "São 564 km e cerca de 6 horas de 101, com a missa das 8h30 em Paso Robles no "
        "caminho, até a devolução às 15h e o voo às 17h43. Saindo às 6h10 sobram uns 45 "
        "minutos. Não cabe desvio cênico.")

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
            return "ruim", "Mar grande na Kealakekua Bay. Visibilidade do snorkel vai a zero.", num
        if onda is not None and onda > 1.2:
            return "atencao", "Mar mexido. O catamarã sai, a água fica turva.", num
        return "bom", "Kealakekua Bay calma. É o melhor snorkel da ilha.", num

    add("snorkel", "Catamarã e snorkel na Kealakekua Bay", "2027-01-02", "9h às 13h",
        "Mar acima de 2 m fecha a janela de visibilidade.",
        J("kealakekua", "2027-01-02", 9, 13), av_snorkel,
        "O snorkel noturno com arraias-manta é na Keauhou Bay, protegida, e "
        "aguenta mar que a Kealakekua Bay, aberta, não aguenta.")

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
            if i.get("efeito"):
                L.append(f"    {i['efeito']}")
    if not achou:
        L.append("  sem boletim para os condados da rota")
    if d["alertas"]:
        L += ["", "AVISOS DO NWS"]
        for a in d["alertas"]:
            L.append(f"  {a['evento']} ({a['severidade']}) - {a['onde'][:70]}")
            if a.get("efeito"):
                L.append(f"    {a['efeito']}")
    else:
        L += ["", "AVISOS DO NWS: nenhum ativo na rota."]
    return "\n".join(L)


# ---------------------------------------------------------------- main

def _marca(texto):
    """Identidade estavel de um aviso, para o delta funcionar entre processos.
    hash() embutido nao serve: e aleatorizado a cada execucao do Python."""
    return hashlib.md5(" ".join(texto.split())[:160].encode("utf-8")).hexdigest()[:12]



def resumo_indice(d):
    """O que o cartao do indice precisa saber, e nada alem disso."""
    cont = {"bom": 0, "atencao": 0, "ruim": 0, "espera": 0}
    for dec in d["decisoes"]:
        cont[dec["veredito"]] = cont.get(dec["veredito"], 0) + 1
    vias = sum(1 for v in d["estradas"] for i in v["itens"]
               if i["fechado"] and i["na_rota"])
    return {
        "gerado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "partida": VIAGEM["carro_lax"] + ":00-08:00",
        "fim": "2027-01-06T00:40:00-08:00",
        "pontos": len(d["pontos"]), "regioes": len(d["regioes"]),
        "decisoes": cont,
        "dias_com_previsao": len(d["prev_por_dia"]),
        "vias_fechadas": vias,
        "avisos_rota": len(d["alertas"]),
        "kilauea": (d.get("kilauea") or {}).get("cor", ""),
    }


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
        "decisoes": decisoes(prev, mar, kil), "roteiro": ROTEIRO,
        "missas": MISSAS, "igrejas": IGREJAS,
    }

    for dec in d["decisoes"]:
        rid = ROTA_DA_DECISAO.get(dec["id"])
        dec["regiao"] = ROTAS[rid]["regiao"] if rid in ROTAS else "ca"

    # Cotacao do dolar (e do canadense) para o cartao no cabecalho. Publicada a
    # parte, pelo repositorio precos-zfold8 (LaunchAgent do Mac de hora em hora
    # e o workflow cotacao-wise de 3 em 3h de rede de seguranca), que desde
    # 26/09/2026 escreve aqui em vez de no painel de precos, apagado nessa
    # data. Buscada ao vivo so para a pagina nascer com um valor de reserva; a
    # propria pagina refaz o fetch de mesma origem assim que carrega.
    try:
        d["wise"] = fetch_json(
            "https://rafaelcortopassi.pythonanywhere.com/honeymoon/wise.json",
            timeout=15, tentativas=1)
    except Exception as e:
        print(f"aviso: wise.json indisponivel ({type(e).__name__}); "
              f"cartao do dolar nasce sem valor de reserva")
        d["wise"] = {"pares": {}}

    # ---- mapas: um por dia de estrada e um por aviso que tenha lugar. Falha
    # aqui nao pode calar o aviso: sem mapa, o texto sai do mesmo jeito.
    geo = _le(GEO, {})
    geo_antes = json.dumps(geo, sort_keys=True)
    mapas = {}
    try:
        import _cartografia as carto
        rotas = carto.prepara_rotas(ROTAS, geo)
        lcs = {}
        for dia, rid in ROTA_DO_DIA.items():
            if rid in rotas:
                r = rotas[rid]
                mapas["trajeto_" + rid] = carto.com_hash({
                    "tipo": "trajeto", "regiao": r["regiao"], "spec": carto.spec_trajeto(r),
                    "titulo": r["titulo"], "efeito": "", "toca": True,
                    "link": carto.link_gmaps([p[:2] for p in r["paradas"]])})
        for v in vias:
            for i in v["itens"]:
                if i["na_rota"] and not i.get("livre"):
                    m = carto.mapa_interdicao(v["rodovia"], i, rotas, geo, lcs)
                    if m:
                        i["mapa"] = "via_" + _marca(i["texto"])
                        i["efeito"] = m["efeito"]
                        mapas[i["mapa"]] = carto.com_hash(m)
        for a in alertas:
            m = carto.mapa_aviso(a, rotas, geo)
            if m:
                a["mapa"] = "nws_" + _marca(a["id"])
                a["efeito"] = m["efeito"]
                mapas[a["mapa"]] = carto.com_hash(m)
        for reg in ("ca", "oahu", "bi"):
            itens = [m for m in mapas.values()
                     if m["regiao"] == reg and m["tipo"] in ("interdicao", "aviso")]
            m = carto.mapa_resumo(reg, itens, rotas)
            if m:
                mapas["resumo_" + reg] = carto.com_hash(m)
        for dec in d["decisoes"]:
            rid = ROTA_DA_DECISAO.get(dec["id"])
            if dec["veredito"] == "ruim" and rid in rotas:
                dec["mapa"] = "dec_" + dec["id"]
                mapas[dec["mapa"]] = carto.com_hash(carto.mapa_decisao(dec, rotas[rid]))
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: mapas indisponiveis nesta rodada ({type(e).__name__}: {e})")
    try:
        import _geo
        if _geo.USADAS and "rotas" in geo:
            geo["rotas"] = {k: v for k, v in geo["rotas"].items() if k in _geo.USADAS}
    except Exception:  # noqa: BLE001
        pass
    if json.dumps(geo, sort_keys=True) != geo_antes:
        GEO.parent.mkdir(parents=True, exist_ok=True)
        GEO.write_text(json.dumps(geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ---- alertas urgentes, sempre por DELTA: repetir o mesmo aviso a cada 6 h
    # treina o usuario a ignorar o push.
    vistos = set(estado.get("vistos") or [])
    novos_ids, urgentes = [], []
    for a in alertas:
        if a["severidade"] in ("Severe", "Extreme") and a["id"] not in vistos:
            novos_ids.append(a["id"])
            urgentes.append({"texto": f"NWS {a['evento']}: {a['manchete'][:180]}",
                             "mapa": a.get("mapa"), "extra": ""})
    for v in vias:
        for i in v["itens"]:
            if i["fechado"] and i["na_rota"]:
                marca = "via:" + _marca(i["texto"])
                if marca not in vistos:
                    novos_ids.append(marca)
                    urgentes.append({"texto": f"{v['rodovia']} fechada: {i['texto'][:180]}",
                                     "mapa": i.get("mapa"), "extra": i["texto"]})
    cor_kil = (kil or {}).get("cor", "")
    if cor_kil in ("ORANGE", "RED") and estado.get("kilauea_cor") not in ("ORANGE", "RED"):
        urgentes.append({"texto": f"Kilauea subiu para {cor_kil}: fonte de lava ativa. "
                                  f"Detalhe no monitor do vulcao.", "mapa": None, "extra": ""})
    for dec in d["decisoes"]:
        if dec["veredito"] == "ruim":
            marca = "dec:" + dec["id"] + ":" + dec["dia"]
            if marca not in vistos:
                novos_ids.append(marca)
                urgentes.append({"texto": f"{dec['titulo']} ({dec['dia'][8:10]}/"
                                          f"{dec['dia'][5:7]}): {dec['motivo'][:160]}",
                                 "mapa": dec.get("mapa"), "extra": ""})

    # ---- desenha e publica os mapas. Redesenha so o que mudou, mais o que
    # vai ser enviado agora (o Telegram recebe a imagem em bytes, e nao pela
    # URL, porque o PythonAnywhere as vezes serve arquivo pela metade logo
    # depois do upload).
    enviar = {u["mapa"] for u in urgentes if u["mapa"]} if urgentes else \
        {k for k in mapas if k.startswith("resumo_")}
    anterior = estado.get("mapas") or {}
    publicados, imagens = {}, {}
    try:
        import _mapa
        print(f"mapas: {len(mapas)} (fonte {_mapa.nome_fonte()})")
        for mid, m in mapas.items():
            mudou = anterior.get(mid) != m["hash"]
            if mudou or mid in enviar or so_local:
                try:
                    imagens[mid] = _mapa.renderiza(m["spec"])
                except Exception as e:  # noqa: BLE001
                    print(f"aviso: mapa {mid} nao desenhou ({e})")
                    continue
            if so_local:
                MAPAS_LOCAL.mkdir(exist_ok=True)
                (MAPAS_LOCAL / f"{mid}.jpg").write_bytes(imagens[mid])
                publicados[mid] = m["hash"]
            elif mudou:
                if upload_pa(imagens[mid], f"mapas/{mid}.jpg"):
                    publicados[mid] = m["hash"]
            else:
                publicados[mid] = m["hash"]
    except ImportError as e:
        print(f"AVISO: Pillow ausente, avisos sem mapa ({e})")

    def url_mapa(mid, absoluta=False):
        if mid not in publicados:
            return ""
        return (LINK_SITE if absoluta else "") + f"mapas/{mid}.jpg?v={publicados[mid]}"

    for v in vias:
        for i in v["itens"]:
            if i.get("mapa"):
                i["mapa_url"], i["mapa_link"] = url_mapa(i["mapa"]), mapas[i["mapa"]]["link"]
    for a in alertas:
        if a.get("mapa"):
            a["mapa_url"], a["mapa_link"] = url_mapa(a["mapa"]), mapas[a["mapa"]]["link"]
    for perna in ROTEIRO:
        mid = "trajeto_" + ROTA_DO_DIA.get(perna["dia"], "")
        perna["mapa_url"] = url_mapa(mid)
        perna["mapa_link"] = mapas[mid]["link"] if mid in mapas else ""

    def legenda(mid, extra=""):
        m = mapas[mid]
        partes = [f"<b>{html_mod.escape(m['spec']['titulo'])}</b>"]
        if m["spec"].get("subtitulo"):
            partes.append(html_mod.escape(m["spec"]["subtitulo"]))
        if extra:
            partes.append("<i>" + html_mod.escape(extra[:320]) + "</i>")
        links = []
        if m.get("link"):
            links.append(f'<a href="{m["link"]}">Abrir no Google Maps</a>')
        links.append(f'<a href="{LINK_SITE}">Painel</a>')
        partes.append(" · ".join(links))
        return "\n\n".join(partes)

    corpo = resumo_texto(d)
    print("\n" + corpo + "\n")

    if "--sem-avisar" in sys.argv:
        print("--sem-avisar: nada enviado")
    elif urgentes:
        titulo = "Honeymoon: " + urgentes[0]["texto"][:60]
        anexo = next((url_mapa(u["mapa"], True) for u in urgentes if u["mapa"] and url_mapa(u["mapa"])), "")
        textos = "\n".join(u["texto"] for u in urgentes)
        push_ntfy(titulo, textos + "\n\n" + corpo, prioridade="high", tags="warning", anexo=anexo)
        push_telegram(titulo, textos + "\n\n" + corpo, urgente=True)
        for u in urgentes:
            if u["mapa"] in imagens:
                push_telegram_foto(imagens[u["mapa"]], legenda(u["mapa"], u["extra"]), urgente=True)
    else:
        push_telegram(f"Honeymoon, faltam {dias_para} dias", corpo, urgente=False)
        for mid in sorted(enviar):
            if mid in imagens:
                push_telegram_foto(imagens[mid], legenda(mid), urgente=False)

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
        # Contrato pequeno para o indice em /home/. O indice roda no Mac e a copia
        # local deste repo NAO recebe os commits do Actions, entao ler o state/
        # local daria numero velho. Estes arquivos sao opcionais: falha aqui nao
        # derruba a rodada.
        from _pagina import FAVICON
        from urllib.parse import unquote
        upload_pa(json.dumps(resumo_indice(d), ensure_ascii=False,
                             separators=(",", ":")), "resumo.json")
        upload_pa(unquote(FAVICON.split(",", 1)[1]), "favicon.svg")
        estado["mapas"] = publicados

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
