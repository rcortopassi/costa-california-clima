# Costa Dourada

Monitor de clima, mar e estrada da viagem de 20/12/2026 a 06/01/2027: costa da
Califórnia (Los Angeles a Carmel), Oahu e Big Island.

- `monitor.py` busca tudo, decide, gera a página e publica. Só stdlib.
- `_pagina.py` é o template: CSS, JS e HTML. Editar SEMPRE aqui, nunca o
  `index.html`, que é gerado e está no `.gitignore`.
- `state/` guarda o que já foi avisado, para o push ser sempre delta.

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
