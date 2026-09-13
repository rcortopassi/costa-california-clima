# Costa Dourada

Monitor de clima, mar e estrada da viagem de 20/12/2026 a 06/01/2027: costa da
Califórnia (Los Angeles a Carmel), Oahu e Big Island.

- `monitor.py` busca tudo, decide, gera a página e publica. Só stdlib.
- `_pagina.py` é o template: CSS, JS e HTML. Editar SEMPRE aqui, nunca o
  `index.html`, que é gerado e está no `.gitignore`.
- `_geo.py` calcula rotas (OSRM), acha início e fim de cada interdição (feed LCS
  da Caltrans, com Nominatim de reserva) e a área de cada aviso do NWS.
- `_cartografia.py` decide o que cada mapa mostra e escreve a frase que diz se
  o aviso toca o trajeto. `_mapa.py` desenha (Pillow).
- `state/` guarda o que já foi avisado, para o push ser sempre delta, os hashes
  dos mapas publicados e o cache de geografia (`geo.json`).

Publicado em <https://rafaelcortopassi.pythonanywhere.com/california/>.

## Rodar à mão

    python3 monitor.py --forca --sem-publicar   # gera local, não sobe nada
    python3 monitor.py --forca                  # gera e publica

Sem `--forca`, a guarda de frescor encerra a rodada em segundos se a última
foi há menos de 5 horas. É o que permite pedir o cron de 2 em 2 horas sem
martelar as fontes: o agendador do GitHub descarta a maioria dos horários.

## Fontes, todas sem chave de API

| o que | onde |
|---|---|
| previsão horária e diária | Open-Meteo, elevação forçada por ponto |
| ondas | Open-Meteo Marine |
| climatologia | reanálise ERA5 via Open-Meteo (calculada uma vez, fixa no código) |
| avisos | api.weather.gov, uma chamada por estado (CA e HI) |
| estradas | roads.dot.ca.gov, SR 1 e US 101 |
| El Niño | Climate Prediction Center, NOAA |
| rotas | router.project-osrm.org, cacheadas em `state/geo.json` |
| início e fim das interdições | cwwp2.dot.ca.gov, feed LCS dos distritos 5 e 7 |
| fundo dos mapas | Esri World Street Map (a CARTO passou a exigir chave) |
| vulcão | API HANS do USGS, Kilauea vnum 332010 |

## Armadilhas já resolvidas, não reintroduzir

- **Elevação forçada.** Sem `elevation=` por ponto, o modelo escolhe o ponto de
  grade encosta acima e o cume do Mauna Kea, a 4.207 m, vira uma colina de
  2.000 m com 10 graus a mais. É o que decide a regra de gelo.
- **Uma chamada por região, não por ponto.** O Open-Meteo aceita lista de
  coordenadas. Ponto por ponto seriam 27 requisições e um 429 na certa.
- **Avisos do NWS por estado, filtrados por zona.** Consultar `?point=` de cada
  ponto seriam outras 27 chamadas para a mesma informação.
- **Caltrans traz o estado inteiro.** Sem o filtro de condados o painel grita
  por causa de Fort Bragg e Point Reyes, a centenas de quilômetros do roteiro.
- **A página injetava os 16 dias inteiros** com 11 variáveis por ponto e passava
  de 700 KB. Agora injeta só o que a grade desenha: 3 em 3 horas, 7 dias,
  arredondado. Ficou em 115 KB.
- **Validar o JS com `node --check` antes de publicar.** Já está no código e
  aborta a publicação se quebrar.

## Mapas nos avisos

Todo aviso com lugar vai com mapa: interdição com início e fim, aviso do NWS
com a área e os pontos onde o trajeto entra e sai dela, e sempre o trajeto de
vocês. Nomes de lugar ficam no original (Salinas Valley, Windward Coast,
Mauna Kea Summit), como nas placas e no Google Maps.

- **Ponto de passagem sem nome** (`_ORLA_101`) prende a rota na US 101 pela
  orla. Livre, o roteador corta Santa Barbara a Buellton pela CA 154 (San
  Marcos Pass), e o mapa passava a mostrar uma estrada que o roteiro não usa.
- Mudar `VERSAO` em `_cartografia.py` força redesenhar e reenviar todos.
- Testar sem incomodar: `python3 monitor.py --forca --sem-publicar --sem-avisar`
  grava os mapas em `mapas/`. No Actions, disparar com `avisar=false`.
