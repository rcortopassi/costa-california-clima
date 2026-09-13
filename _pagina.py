"""Template da pagina. Separado do monitor para o HTML nao ficar preso no meio
da logica. Estetica: grade de dados no estilo windguru, cores e titulos da
California (papel queimado de sol, azul do Pacifico, laranja da papoula)."""

FAVICON = ("data:image/svg+xml;utf8,"
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
           "%3Crect width='64' height='64' rx='13' fill='%230B3B54'/%3E"
           "%3Ccircle cx='32' cy='26' r='12.5' fill='%23F7A93B'/%3E"
           "%3Cpath d='M2 41q9-6 17 0t17 0 16-4v27H2z' fill='%23166C8F'/%3E%3C/svg%3E")

CSS = r"""
*{box-sizing:border-box}
:root{
  --papel:#FBF6EC; --papel2:#F4EBDB; --cartao:#FFFDF8;
  --tinta:#1C2B31; --tinta2:#5E6D72; --linha:#E2D6C2;
  --pacifico:#0B3B54; --pacifico2:#166C8F;
  --poppy:#E8730F; --dourado:#F2A93B; --coral:#D24B36;
  --sequoia:#8A3B26; --sage:#7C8B68; --neblina:#BFC7CC;
  --sombra:0 1px 2px rgba(28,43,49,.07),0 8px 24px -12px rgba(28,43,49,.18);
  --sobre-pacifico:#FFF8EC;
}
@media (prefers-color-scheme:dark){:root:not([data-tema="claro"]){
  --papel:#0C1620; --papel2:#122130; --cartao:#132433;
  --tinta:#EAE2D4; --tinta2:#9BA8B0; --linha:#26394A;
  --pacifico:#8FC9E4; --pacifico2:#5FAFD0;
  --poppy:#F98E2B; --dourado:#F5BB5C; --coral:#E86B54;
  --sequoia:#C97B5E; --sage:#9DAC88; --neblina:#7C8A93;
  --sombra:0 1px 2px rgba(0,0,0,.4),0 10px 30px -14px rgba(0,0,0,.6);
  --sobre-pacifico:#0C1620;
}}
:root[data-tema="escuro"]{
  --papel:#0C1620; --papel2:#122130; --cartao:#132433;
  --tinta:#EAE2D4; --tinta2:#9BA8B0; --linha:#26394A;
  --pacifico:#8FC9E4; --pacifico2:#5FAFD0;
  --poppy:#F98E2B; --dourado:#F5BB5C; --coral:#E86B54;
  --sequoia:#C97B5E; --sage:#9DAC88; --neblina:#7C8A93;
  --sombra:0 1px 2px rgba(0,0,0,.4),0 10px 30px -14px rgba(0,0,0,.6);
  --sobre-pacifico:#0C1620;
}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--papel);color:var(--tinta);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.env{max-width:1180px;margin:0 auto;padding:0 18px 72px}
a{color:var(--pacifico2)}

/* ---------- cabecalho: faixa de poente sobre o Pacifico ---------- */
header.capa{position:relative;overflow:hidden;
  background:linear-gradient(176deg,#0A2E46 0%,#124B64 38%,#8A5A3C 68%,#E8730F 86%,#F2A93B 100%);
  color:#FFF8EC;padding:40px 0 0}
header.capa .env{padding-bottom:0}
.sol{position:absolute;right:9%;top:26px;width:104px;height:104px;border-radius:50%;
  background:radial-gradient(circle at 50% 50%,#FFE9A8,#F7A93B 58%,rgba(247,169,59,0) 72%);
  filter:blur(.3px)}
.marca{font-size:11px;letter-spacing:.34em;text-transform:uppercase;opacity:.82;
  font-weight:600}
h1{margin:.16em 0 .1em;font-size:clamp(30px,6.4vw,52px);line-height:1.02;
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-weight:600;letter-spacing:-.015em}
h1 em{font-style:normal;color:#FFD9A0}
.sub{font-size:15px;opacity:.9;max-width:44ch;margin:0 0 4px}
.regua{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0;padding:0 0 18px}
.selo{background:rgba(255,248,236,.13);border:1px solid rgba(255,248,236,.24);
  border-radius:999px;padding:5px 13px;font-size:12.5px;font-variant-numeric:tabular-nums;
  backdrop-filter:blur(3px)}
.selo b{font-weight:700;color:#FFE3B4}
.ondas{display:block;width:100%;height:34px;margin-bottom:-1px}

/* ---------- secoes ---------- */
section{margin:38px 0 0}
h2{font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--tinta2);
  margin:0 0 4px;font-weight:700}
h2+.leg{margin:0 0 16px;font-size:14px;color:var(--tinta2);max-width:70ch}
h3{font-family:"Iowan Old Style",Palatino,Georgia,serif;font-weight:600;
  font-size:21px;margin:0 0 2px;letter-spacing:-.01em}

.grade{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(248px,1fr))}
.cartao{background:var(--cartao);border:1px solid var(--linha);border-radius:14px;
  padding:16px;box-shadow:var(--sombra)}
.cartao.dirige{border-left:4px solid var(--poppy)}
.cartao .quando{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--poppy);font-weight:700}
.cartao .txt{font-size:13.5px;color:var(--tinta2);margin:8px 0 0}
.numerao{display:flex;gap:14px;align-items:baseline;margin:12px 0 2px;flex-wrap:wrap}
.numerao .t{font-size:30px;font-weight:650;font-variant-numeric:tabular-nums;
  letter-spacing:-.02em}
.numerao .u{font-size:13px;color:var(--tinta2)}
.pares{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;font-size:13px;
  margin:10px 0 0}
.pares dt{color:var(--tinta2)}
.pares dd{margin:0;font-variant-numeric:tabular-nums;text-align:right}

.faixa{display:inline-block;border-radius:5px;padding:1px 7px;font-size:11.5px;
  font-weight:700;letter-spacing:.04em;text-transform:uppercase}
.f-ok{background:rgba(124,139,104,.18);color:var(--sage)}
.f-at{background:rgba(242,169,59,.2);color:var(--sequoia)}
.f-ru{background:rgba(210,75,54,.16);color:var(--coral)}

/* ---------- grade windguru ---------- */
.abas{display:flex;gap:6px;overflow-x:auto;padding:2px 0 10px;scrollbar-width:thin}
.aba{flex:0 0 auto;border:1px solid var(--linha);background:var(--cartao);
  color:var(--tinta2);border-radius:999px;padding:11px 16px;font-size:13px;
  cursor:pointer;min-height:44px;font-weight:600;white-space:nowrap}
.aba[aria-selected="true"]{background:var(--pacifico);border-color:var(--pacifico);
  color:var(--sobre-pacifico)}
.rolagem{overflow-x:auto;border:1px solid var(--linha);border-radius:12px;
  background:var(--cartao);box-shadow:var(--sombra)}
table.wg{border-collapse:separate;border-spacing:0;font-size:11.5px;
  font-variant-numeric:tabular-nums;width:max-content;min-width:100%}
table.wg th,table.wg td{padding:3px 0;text-align:center;border-bottom:1px solid var(--linha);
  min-width:34px;height:23px;line-height:1.1}
table.wg th.rot{position:sticky;left:0;z-index:3;background:var(--cartao);
  text-align:left;padding:3px 10px 3px 12px;min-width:118px;white-space:nowrap;
  font-weight:600;font-size:11.5px;border-right:1px solid var(--linha);color:var(--tinta2)}
table.wg tr.dias th{background:var(--papel2);font-size:11.5px;letter-spacing:.06em;
  text-transform:uppercase;font-weight:700;border-left:1px solid var(--linha);
  color:var(--tinta);padding:6px 8px}
table.wg tr.dias th.rot{background:var(--papel2);text-transform:none;letter-spacing:0}
table.wg tr.dias th.seu{background:var(--poppy);color:#FFF8EC}
table.wg tr.horas th{color:var(--tinta2);font-weight:600;background:var(--cartao)}
table.wg td.d0{border-left:1px solid var(--linha)}
td.seta span{display:inline-block;font-size:13px;line-height:1;color:var(--pacifico)}
td.forte{font-weight:750}
td.branco{color:#FFF8EC}
.legenda{display:flex;flex-wrap:wrap;gap:12px;margin:10px 0 0;font-size:12px;
  color:var(--tinta2)}
.legenda i{display:inline-block;width:13px;height:13px;border-radius:3px;
  vertical-align:-2px;margin-right:5px;border:1px solid rgba(0,0,0,.08)}

/* ---------- estradas e avisos ---------- */
.item{border:1px solid var(--linha);border-left-width:4px;border-radius:11px;
  background:var(--cartao);padding:12px 15px;margin:0 0 9px;box-shadow:var(--sombra)}
.item.ok{border-left-color:var(--sage)}
.item.at{border-left-color:var(--dourado)}
.item.ru{border-left-color:var(--coral)}
.item .cab{display:flex;justify-content:space-between;gap:10px;align-items:baseline;
  flex-wrap:wrap;margin-bottom:3px}
.item .via{font-weight:700;font-size:13px;letter-spacing:.06em}
.item p{margin:0;font-size:13.5px;color:var(--tinta2)}
.vazio{font-size:14px;color:var(--tinta2);font-style:italic}

table.hist{width:100%;border-collapse:collapse;font-size:13.5px;
  font-variant-numeric:tabular-nums}
table.hist th,table.hist td{padding:7px 10px;border-bottom:1px solid var(--linha);
  text-align:right}
table.hist th:first-child,table.hist td:first-child{text-align:left}
table.hist thead th{font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--tinta2);font-weight:700}

footer{margin:48px 0 0;padding:20px 0 0;border-top:1px solid var(--linha);
  font-size:12.5px;color:var(--tinta2)}
footer a{color:var(--tinta2);text-decoration:underline}
.tema{position:fixed;right:14px;bottom:14px;z-index:9;border:1px solid var(--linha);
  background:var(--cartao);color:var(--tinta2);border-radius:999px;
  min-width:44px;min-height:44px;padding:0 15px;font-size:13px;cursor:pointer;
  box-shadow:var(--sombra)}
@media (max-width:560px){
  .env{padding:0 13px 72px}
  .sol{width:68px;height:68px;right:6%;top:20px}
  .pares{font-size:12.5px}
}
"""

CSS += r"""
table.wg td.pt{color:#1C2B31}
table.wg td.pt.branco{color:#FFF8EC}
"""

JS = r"""
const D = DADOS;

/* Escalas de cor no espirito do windguru: o valor se le pela cor antes de se
   ler o numero. [limite, cor, textoBranco] */
const ESC_VENTO = [[3,"#E9F6FD"],[6,"#CFEAF8"],[9,"#AADFF2"],[12,"#82D2E9"],
  [15,"#84D6A6"],[18,"#BBDE6B"],[21,"#ECD84B"],[25,"#F2A93B"],[30,"#E8703A"],
  [35,"#D8402C",1],[999,"#A3228F",1]];
const ESC_TEMP = [[2,"#CFE4F5"],[6,"#BCD9EE"],[10,"#A9D9C7"],[14,"#D0E6A1"],
  [18,"#F2E58B"],[22,"#F5C066"],[26,"#EF8D4F"],[999,"#E05A3C",1]];
const ESC_CHUVA = [[0.05,""],[0.3,"#EFF7FC"],[1,"#D0E7F6"],[2.5,"#A0D1EF"],
  [5,"#65B3E1"],[10,"#2F90CD",1],[999,"#1C5FA8",1]];
const ESC_PROB = [[10,""],[30,"#F6F0DC"],[50,"#F7E3B0"],[70,"#F5CE85"],
  [85,"#F0B15C"],[999,"#E8902F"]];
const ESC_VIS = [[1,"#B794D6",1],[3,"#D6BFE9"],[8,"#EDE3F5"],[999,""]];

function cor(esc, v){
  if (v === null || v === undefined) return ["", 0];
  for (const linha of esc) if (v < linha[0]) return [linha[1], linha[2] || 0];
  return ["", 0];
}
function corNuvem(p){
  if (p === null || p === undefined) return ["", 0];
  const g = Math.round(252 - (252 - 148) * (p / 100));
  return ["rgb(" + g + "," + (g + 2) + "," + (g + 5) + ")", 0];
}

const DIAS_SEM = ["dom","seg","ter","qua","qui","sex","sab"];
function rotuloDia(iso){
  const d = new Date(iso + "T12:00:00");
  return DIAS_SEM[d.getDay()] + " " + iso.slice(8,10) + "/" + iso.slice(5,7);
}

/* Monta a grade de um ponto: colunas de 3 em 3 horas, linhas de parametro. */
function montaGrade(p){
  const h = p.hourly;
  const idx = h.time.map(function(_, i){ return i; });
  const porDia = [];
  for (const i of idx){
    const dia = h.time[i].slice(0,10);
    if (!porDia.length || porDia[porDia.length-1].dia !== dia)
      porDia.push({dia: dia, cols: []});
    porDia[porDia.length-1].cols.push(i);
  }

  let cab = '<tr class="dias"><th class="rot">' + p.nome + "</th>";
  for (const g of porDia){
    const seu = D.dias_viagem.indexOf(g.dia) >= 0 ? " seu" : "";
    cab += '<th class="' + ("d0" + seu).trim() + '" colspan="' + g.cols.length + '">'
         + rotuloDia(g.dia) + "</th>";
  }
  cab += "</tr>";

  let horas = '<tr class="horas"><th class="rot">hora local</th>';
  porDia.forEach(function(g){
    g.cols.forEach(function(i, k){
      horas += '<th class="' + (k === 0 ? "d0" : "") + '">' + h.time[i].slice(11,13) + "</th>";
    });
  });
  horas += "</tr>";

  const linhas = [
    {rot:"vento (nós)", campo:"wind_speed_10m", esc:ESC_VENTO, dec:0},
    {rot:"rajada (nós)", campo:"wind_gusts_10m", esc:ESC_VENTO, dec:0, forte:1},
    {rot:"direção", campo:"wind_direction_10m", seta:1},
    {rot:"temperatura (°C)", campo:"temperature_2m", esc:ESC_TEMP, dec:0},
    {rot:"chuva (mm/3h)", campo:"precipitation", esc:ESC_CHUVA, dec:1, zero:1},
    {rot:"chance de chuva", campo:"precipitation_probability", esc:ESC_PROB, dec:0, pct:1},
    {rot:"nuvens", campo:"cloud_cover", nuvem:1, pct:1},
    {rot:"visibilidade (km)", campo:"visibility", esc:ESC_VIS, dec:0, km:1}
  ];

  let corpo = "";
  for (const L of linhas){
    corpo += '<tr><th class="rot">' + L.rot + "</th>";
    porDia.forEach(function(g){
      g.cols.forEach(function(i, k){
        const bruto = h[L.campo] ? h[L.campo][i] : null;
        const borda = k === 0 ? " d0" : "";
        if (bruto === null || bruto === undefined){
          corpo += '<td class="pt' + borda + '">-</td>';
          return;
        }
        if (L.seta){
          corpo += '<td class="seta' + borda + '"><span style="transform:rotate('
                 + (bruto + 180) + 'deg)">↑</span></td>';
          return;
        }
        let v = bruto;
        if (L.km) v = v / 1000;
        const par = L.nuvem ? corNuvem(v) : cor(L.esc, v);
        let txt;
        if (L.zero && v < 0.05) txt = "";
        else if (L.pct) txt = Math.round(v);
        else txt = v.toFixed(L.dec);
        if (L.km && v >= 20) txt = "20+";
        const cls = "pt" + borda + (par[1] ? " branco" : "") + (L.forte ? " forte" : "");
        const est = par[0] ? ' style="background:' + par[0] + '"' : "";
        corpo += '<td class="' + cls + '"' + est + ">" + txt + "</td>";
      });
    });
    corpo += "</tr>";
  }
  return "<table class=\"wg\"><thead>" + cab + horas + "</thead><tbody>" + corpo + "</tbody></table>";
}

function abre(id){
  const p = D.pontos.find(function(x){ return x.id === id; });
  if (!p) return;
  document.getElementById("grade").innerHTML = montaGrade(p);
  document.querySelectorAll(".aba").forEach(function(b){
    b.setAttribute("aria-selected", b.dataset.p === id ? "true" : "false");
  });
  try { localStorage.setItem("cd-ponto", id); } catch (e) {}
}

function contagem(){
  const el = document.getElementById("contagem");
  if (!el) return;
  const quando = D.viagem.carro_lax;
  if (!quando){ el.textContent = "sem data de partida"; return; }
  const ms = new Date(quando + ":00-08:00") - new Date();
  if (!isFinite(ms)){ el.textContent = "sem data de partida"; return; }
  if (ms <= 0){ el.textContent = "a viagem começou"; return; }
  const dias = Math.floor(ms / 86400000);
  const horas = Math.floor((ms % 86400000) / 3600000);
  el.innerHTML = "faltam <b>" + dias + " dias</b> e " + horas + "h para o carro no LAX";
}

function tema(){
  const r = document.documentElement;
  const escuro = window.matchMedia("(prefers-color-scheme:dark)").matches;
  const atual = r.getAttribute("data-tema") || (escuro ? "escuro" : "claro");
  const novo = atual === "escuro" ? "claro" : "escuro";
  r.setAttribute("data-tema", novo);
  try { localStorage.setItem("cd-tema", novo); } catch (e) {}
}

(function inicia(){
  try {
    const t = localStorage.getItem("cd-tema");
    if (t) document.documentElement.setAttribute("data-tema", t);
  } catch (e) {}
  document.querySelectorAll(".aba").forEach(function(b){
    b.addEventListener("click", function(){ abre(b.dataset.p); });
  });
  const bt = document.getElementById("bt-tema");
  if (bt) bt.addEventListener("click", tema);
  let inicial = D.pontos[0].id;
  try {
    const salvo = localStorage.getItem("cd-ponto");
    if (salvo && D.pontos.some(function(x){ return x.id === salvo; })) inicial = salvo;
  } catch (e) {}
  abre(inicial);
  contagem();
  setInterval(contagem, 60000);
})();
"""


import html as _h
import json as _j

ONDAS = ('<svg class="ondas" viewBox="0 0 1200 40" preserveAspectRatio="none" '
         'aria-hidden="true"><path d="M0 40V22C150 10 300 6 450 14s300 20 450 12 '
         '250-16 300-18v34z" fill="var(--papel)"/></svg>')

LEGENDA_VENTO = [("até 9", "#AADFF2"), ("12", "#82D2E9"), ("15", "#84D6A6"),
                 ("18", "#BBDE6B"), ("21", "#ECD84B"), ("25", "#F2A93B"),
                 ("30", "#E8703A"), ("35+", "#D8402C")]


VER = {
    "bom":     ("ok", "f-ok", "pode ir"),
    "atencao": ("at", "f-at", "com ressalva"),
    "ruim":    ("ru", "f-ru", "não vá"),
    "espera":  ("es", "f-es", "regra armada"),
}
NOME_REG = {"ca": "California", "oahu": "Oahu", "bi": "Big Island"}


def _card_etapa(e, ponto, prev_dia, dias_para):
    """Cartao de um dia do roteiro. Mostra previsao quando a data ja cabe nos
    16 dias do modelo; fora disso mostra a climatologia, que e o unico numero
    honesto a essa distancia."""
    cls = "cartao dirige" if e["dirige"] else "cartao"
    br = e["dia"][8:10] + "/" + e["dia"][5:7]
    h = ['<article class="' + cls + '">',
         '<div class="quando">' + br + " &middot; " + NOME_REG[e["regiao"]]
         + (" &middot; estrada" if e["dirige"] else "") + "</div>",
         "<h3>" + _h.escape(e["titulo"]) + "</h3>"]
    if prev_dia:
        h.append('<div class="numerao"><span class="t">'
                 + str(round(prev_dia["tmax"])) + "&deg;</span>"
                 '<span class="u">máx &middot; mín ' + str(round(prev_dia["tmin"]))
                 + "&deg;C</span></div>")
        h.append('<dl class="pares">'
                 + "<dt>chuva prevista</dt><dd>" + f'{prev_dia["mm"]:.1f} mm</dd>'
                 + "<dt>chance de chuva</dt><dd>" + str(round(prev_dia["prob"])) + "%</dd>"
                 + "<dt>rajada máxima</dt><dd>" + str(round(prev_dia["rajada"])) + " nós</dd>"
                 + "<dt>sol</dt><dd>" + prev_dia["sol"] + "</dd></dl>"
                 '<p class="txt"><span class="faixa f-ok">previsão do modelo</span></p>')
    else:
        n = ponto["normal"]
        h.append('<div class="numerao"><span class="t">' + str(round(n["tmax"]))
                 + '&deg;</span><span class="u">máx &middot; mín '
                 + str(round(n["tmin"])) + "&deg;C, normal de 30 anos</span></div>")
        h.append('<dl class="pares">'
                 + "<dt>dias com chuva</dt><dd>" + str(n["pct"]) + "% dos casos</dd>"
                 + "<dt>chuva forte (&gt;5 mm)</dt><dd>" + str(n["forte"]) + "% dos casos</dd>"
                 + "<dt>poente em " + _h.escape(ponto["nome"][:18]) + "</dt><dd>"
                 + (ponto.get("por_do_sol") or "-") + "</dd>"
                 + "<dt>previsão entra em</dt><dd>"
                 + str(max(0, dias_para - 16)) + " dias</dd></dl>"
                 '<p class="txt"><span class="faixa f-at">climatologia, não previsão</span></p>')
    h.append('<p class="txt">' + _h.escape(e["resumo"]) + "</p></article>")
    return "".join(h)


def _bloco_decisoes(decs):
    h = []
    for d in decs:
        cls, faixa, rotulo = VER[d["veredito"]]
        h.append('<article class="item ' + cls + '">'
                 '<div class="cab"><span class="via">'
                 + d["dia"][8:10] + "/" + d["dia"][5:7] + " &middot; "
                 + _h.escape(d["titulo"]) + " &middot; " + _h.escape(d["quando"])
                 + '</span><span class="faixa ' + faixa + '">' + rotulo + "</span></div>"
                 "<p><b>" + _h.escape(d["motivo"]) + "</b></p>"
                 + ('<p class="num">' + _h.escape(d["numeros"]) + "</p>"
                    if d["numeros"] else "")
                 + '<p class="regra">Gatilho: ' + _h.escape(d["regra"]) + "</p>"
                 '<p class="txt">' + _h.escape(d["recomenda"]) + "</p></article>")
    return "".join(h)


def _bloco_mapa(url, link, efeito, alt):
    if not url:
        return ('<p class="efeito">' + _h.escape(efeito) + "</p>") if efeito else ""
    return ((('<p class="efeito">' + _h.escape(efeito) + "</p>") if efeito else "")
            # no celular o mapa sai com ~320 px; o toque abre a imagem inteira para ampliar
            + '<a class="mapa" href="' + _h.escape(url) + '" target="_blank" rel="noopener">'
            + '<img class="mapa" loading="lazy" src="' + _h.escape(url) + '" alt="'
            + _h.escape(alt) + '" width="1200" height="900"></a>'
            + (('<a class="gmaps" href="' + _h.escape(link) + '" target="_blank" rel="noopener">'
                "Abrir no Google Maps</a>") if link else ""))


def _bloco_estradas(vias):
    if not vias:
        return '<p class="vazio">Boletim da Caltrans indisponível nesta rodada.</p>'
    h = []
    for v in vias:
        relevantes = [i for i in v["itens"] if i["na_rota"]]
        if not relevantes:
            h.append('<div class="item ok"><div class="cab"><span class="via">'
                     + v["rodovia"] + '</span><span class="faixa f-ok">sem restrição '
                     'no trecho da rota</span></div></div>')
            continue
        for i in relevantes:
            if i.get("livre"):
                cls, faixa = "ok", '<span class="faixa f-ok">liberada</span>'
            elif i["fechado"]:
                cls, faixa = "ru", '<span class="faixa f-ru">fechada</span>'
            else:
                cls, faixa = "at", '<span class="faixa f-at">restrição</span>'
            h.append('<div class="item ' + cls + '"><div class="cab"><span class="via">'
                     + v["rodovia"] + " &middot; " + _h.escape(i["area"].title())
                     + "</span>" + faixa + "</div><p>" + _h.escape(i["texto"])
                     + "</p>" + _bloco_mapa(i.get("mapa_url"), i.get("mapa_link"),
                                            i.get("efeito", ""), "Mapa: " + i["texto"][:120])
                     + "</div>")
    return "".join(h)


def _bloco_avisos(alertas):
    if not alertas:
        return ('<p class="vazio">Nenhum aviso ativo do National Weather Service '
                'em nenhum ponto do roteiro, nem na California nem no Hawaii.</p>')
    h = []
    for a in alertas:
        grave = a["severidade"] in ("Severe", "Extreme")
        cls = "ru" if grave else "at"
        h.append('<div class="item ' + cls + '"><div class="cab"><span class="via">'
                 + _h.escape(a["evento"]) + " &middot; "
                 + ", ".join(NOME_REG.get(r, r) for r in a["regioes"])
                 + '</span><span class="faixa f-' + ("ru" if grave else "at") + '">'
                 + _h.escape(a["severidade"] or "aviso") + "</span></div><p>"
                 + _h.escape(a["manchete"] or a["descricao"][:300]) + "</p>"
                 '<p class="num">' + _h.escape(a["onde"]) + "</p>"
                 + _bloco_mapa(a.get("mapa_url"), a.get("mapa_link"), a.get("efeito", ""),
                               "Mapa do aviso " + a["evento"]) + "</div>")
    return "".join(h)


def _bloco_pacifico(e, k):
    h = []
    if e and e.get("status"):
        h.append('<div class="item at"><div class="cab">'
                 '<span class="via">El Niño &middot; Climate Prediction Center, NOAA</span>'
                 '<span class="faixa f-at">' + _h.escape(e["status"]) + "</span></div>"
                 "<p>" + _h.escape(e.get("sinopse") or "") + "</p>"
                 '<p class="num">Boletim de '
                 + _h.escape(e.get("emitido") or "data não lida")
                 + ". O CPC concentra o sinal de chuva acima da média na costa da "
                   "California com pico entre janeiro e março de 2027, ou seja, "
                   "depois da viagem.</p></div>")
    else:
        h.append('<p class="vazio">Boletim ENSO indisponível nesta rodada.</p>')
    if k and k.get("cor"):
        ativo = k["cor"] in ("ORANGE", "RED")
        h.append('<div class="item ' + ("ru" if k["cor"] == "RED" else
                                        ("at" if ativo else "ok"))
                 + '"><div class="cab"><span class="via">Kilauea &middot; '
                   'Hawaiian Volcano Observatory, USGS</span>'
                   '<span class="faixa f-' + ("at" if ativo else "ok") + '">'
                 + _h.escape(k["cor"] + " / " + k["nivel"]) + "</span></div><p>"
                 + ("Fonte de lava ativa ou episódio em curso. Vale a subida noturna "
                    "ao mirante da cratera." if ativo else
                    "Sem episódio ativo agora. A cratera vale de dia; o brilho "
                    "noturno só existe em erupção.")
                 + '</p><p class="num">Detalhe completo, fotos e mapa no monitor '
                   'dedicado: <a href="../kilauea/">/kilauea/</a></p></div>')
    return "".join(h)



CAMPOS_GRADE = ("time", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m",
                "temperature_2m", "precipitation", "precipitation_probability",
                "cloud_cover", "visibility")


def _enxuga(hourly, dias, passo=3):
    """So o que a grade desenha: de 3 em 3 horas, os primeiros dias, numeros
    arredondados. A pagina injetava os 16 dias inteiros com 11 variaveis e
    passava de 700 KB."""
    n = dias * 24
    idx = list(range(0, min(n, len(hourly.get("time", []))), passo))
    out = {}
    for c in CAMPOS_GRADE:
        serie = hourly.get(c)
        if not serie:
            continue
        if c == "time":
            out[c] = [serie[i] for i in idx]
        elif c == "precipitation":
            out[c] = [None if serie[i] is None else round(serie[i], 1) for i in idx]
        elif c == "visibility":
            out[c] = [None if serie[i] is None else int(serie[i]) for i in idx]
        else:
            out[c] = [None if serie[i] is None else round(serie[i]) for i in idx]
    return out


def monta(d):
    """Devolve (html, js) para o monitor validar o JS antes de publicar."""
    dados = {
        "gerado": d["gerado"], "viagem": d["viagem"], "dias_grade": d["dias_grade"],
        "dias_viagem": d["dias_viagem"],
        "pontos": [{"id": p["id"], "nome": p["nome"],
                    "hourly": _enxuga(p["hourly"], d["dias_grade"])}
                   for p in d["pontos"]],
    }
    js = JS.replace("DADOS", _j.dumps(dados, ensure_ascii=False, separators=(",", ":")), 1)

    abas = []
    for r in d["regioes"]:
        meus = [p for p in d["pontos"] if p["regiao"] == r["id"]]
        if not meus:
            continue
        abas.append('<span class="grupo">' + _h.escape(r["nome"]) + "</span>")
        abas += ['<button class="aba" role="tab" aria-selected="false" data-p="'
                 + p["id"] + '" title="' + _h.escape(p["papel"]) + '">'
                 + _h.escape(p["nome"]) + "</button>" for p in meus]

    cards = "".join(_card_etapa(e, d["por_id"][e["pontos"][-1]],
                                d["prev_por_dia"].get(e["dia"]), d["dias_para"])
                    for e in d["etapas"] if e["pontos"][-1] in d["por_id"])

    leg = "".join('<span><i style="background:' + c + '"></i>' + t + "</span>"
                  for t, c in LEGENDA_VENTO)

    hist = []
    for r in d["regioes"]:
        meus = [p for p in d["pontos"] if p["regiao"] == r["id"]]
        if not meus:
            continue
        hist.append('<tr class="sec"><th colspan="7">' + _h.escape(r["nome"])
                    + "</th></tr>")
        for p in meus:
            n = p["normal"]
            hist.append("<tr><td>" + _h.escape(p["nome"]) + "</td><td>"
                        + f'{n["tmax"]:.1f}' + "</td><td>" + f'{n["tmin"]:.1f}'
                        + "</td><td>" + f'{n["mm"]:.1f}' + "</td><td>"
                        + str(n["pct"]) + "%</td><td>" + str(n["forte"])
                        + "%</td><td>" + (p.get("por_do_sol") or "-") + "</td></tr>")

    return (HTML
            .replace("{{CSS}}", CSS)
            .replace("{{FAVICON}}", FAVICON)
            .replace("{{ABAS}}", "".join(abas))
            .replace("{{CARDS}}", cards)
            .replace("{{DECISOES}}", _bloco_decisoes(d["decisoes"]))
            .replace("{{ROTEIRO}}", _bloco_roteiro(d["roteiro"]))
            .replace("{{LEGENDA}}", leg)
            .replace("{{ESTRADAS}}", _bloco_estradas(d["estradas"]))
            .replace("{{AVISOS}}", _bloco_avisos(d["alertas"]))
            .replace("{{PACIFICO}}", _bloco_pacifico(d.get("enso"), d.get("kilauea")))
            .replace("{{HIST}}", "".join(hist))
            .replace("{{GERADO_PST}}", d["gerado"].replace("T", " às "))
            .replace("{{GERADO_BRT}}", d["gerado_brt"].replace("T", " às "))
            .replace("{{N_PONTOS}}", str(len(d["pontos"])))
            .replace("{{JS}}", js)), js


CSS += r"""
.f-es{background:rgba(94,109,114,.15);color:var(--tinta2)}
.item.es{border-left-color:var(--neblina)}
.item .num{margin:5px 0 0;font-size:12.5px;color:var(--tinta2);
  font-variant-numeric:tabular-nums}
.item .regra{margin:7px 0 0;font-size:12.5px;color:var(--tinta2);
  padding-left:11px;border-left:2px solid var(--linha)}
.item .txt{margin:8px 0 0;font-size:13.5px;color:var(--tinta)}
.item h3{font-size:17px}
.abas .grupo{flex:0 0 auto;align-self:center;font-size:11px;font-weight:700;
  letter-spacing:.16em;text-transform:uppercase;color:var(--tinta2);
  padding:0 6px 0 10px;white-space:nowrap}
.abas .grupo:first-child{padding-left:0}
table.hist tr.sec th{text-align:left;font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--poppy);padding-top:14px;font-weight:700;
  border-bottom:1px solid var(--linha)}
.duplo{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
"""

HTML = """<!DOCTYPE html>
<html lang="pt-BR" data-tema="">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>Costa Dourada &middot; clima e estrada da lua de mel</title>
<link rel="icon" href="{{FAVICON}}">
<style>{{CSS}}</style>
</head>
<body>
<header class="capa">
  <div class="sol" aria-hidden="true"></div>
  <div class="env">
    <div class="marca">Rafael e Ana Cecília &middot; 20/12/2026 a 06/01/2027</div>
    <h1>Costa <em>Dourada</em></h1>
    <p class="sub">O tempo, a luz, o mar e a estrada nos {{N_PONTOS}} pontos do
    roteiro: costa da California, Oahu e Big Island.</p>
    <div class="regua">
      <span class="selo" id="contagem">calculando</span>
      <span class="selo">atualizado <b>{{GERADO_PST}}</b> na costa</span>
      <span class="selo">{{GERADO_BRT}} em Brasília</span>
    </div>
  </div>
  """ + ONDAS + """
</header>

<div class="env">

<section>
  <h2>Ir ou não ir</h2>
  <p class="leg">Cada decisão do roteiro está amarrada a um número que o modelo
  entrega, não a uma impressão. Enquanto o dia não cabe na previsão, a regra
  fica armada e o painel mostra o gatilho em vez de um palpite.</p>
  {{DECISOES}}
</section>

<section>
  <h2>Dia por dia</h2>
  <p class="leg">Enquanto a viagem estiver a mais de 16 dias, nenhum modelo
  prevê o dia. O cartão então mostra a climatologia da janela real de cada
  ilha, calculada sobre 1995 a 2025 na California e 2000 a 2025 no Hawaii, e
  avisa quando a previsão de verdade entra.</p>
  <div class="grade">{{CARDS}}</div>
</section>

<section>
  <h2>Trecho por trecho</h2>
  <p class="leg">Os quatro dias de estrada, com a rodovia exata, a distância e o
  horário. Os poentes foram calculados para a data e a coordenada de cada
  ponto: na California é a semana do solstício e o sol se põe antes das 17h,
  quase uma hora mais cedo do que no fim de janeiro.</p>
  {{ROTEIRO}}
</section>

<section>
  <h2>O Pacífico e o vulcão</h2>
  <p class="leg">A esta distância, os dois sinais com valor preditivo são o
  estado do El Niño, que inclina a estação inteira, e o nível de alerta do
  Kilauea, que decide se existe lava para ver.</p>
  <div class="duplo">{{PACIFICO}}</div>
</section>

<section>
  <h2>Ponto por ponto</h2>
  <p class="leg">Grade de 3 em 3 horas, sete dias, hora local de cada ilha. A
  cor diz o valor antes do número: azul e verde é calmo, amarelo e laranja é
  vento, vermelho é tempestade. Violeta na última linha é visibilidade baixa.
  As colunas laranja são os dias do roteiro.</p>
  <div class="abas" role="tablist">{{ABAS}}</div>
  <div class="rolagem" id="grade"></div>
  <div class="legenda"><span>vento e rajada, em nós:</span>{{LEGENDA}}</div>
</section>

<section>
  <h2>A estrada</h2>
  <p class="leg">Boletim da Caltrans para a SR 1 e a US 101, recortado nos
  condados do roteiro. O que acontece de Santa Cruz para o norte fica de fora
  de propósito. No Hawaii não existe boletim equivalente: a estrada que fecha é
  a Mauna Kea Access Road, até o Mauna Kea Summit, e ela fecha por gelo, o que a grade acima antecipa.</p>
  {{ESTRADAS}}
</section>

<section>
  <h2>Avisos oficiais</h2>
  <p class="leg">Alertas ativos do National Weather Service em qualquer ponto
  do roteiro, na California e no Hawaii.</p>
  {{AVISOS}}
</section>

<section>
  <h2>O que a história diz</h2>
  <p class="leg">Médias da janela de cada ilha e a hora do poente. Na
  California é a semana do solstício, a de dias mais curtos do ano.</p>
  <div class="rolagem" style="padding:2px 14px 8px">
  <table class="hist">
    <thead><tr><th>ponto</th><th>máx</th><th>mín</th><th>mm/dia</th>
    <th>dias com chuva</th><th>&gt;5 mm</th><th>poente</th></tr></thead>
    <tbody>{{HIST}}</tbody>
  </table></div>
</section>

<footer>
  <p>Previsão e reanálise: <a href="https://open-meteo.com/">Open-Meteo</a>
  (ICON, GFS e ERA5), com elevação forçada em cada ponto, sem o quê o cume do
  Mauna Kea viraria uma colina. Ondas: Open-Meteo Marine. Avisos:
  <a href="https://api.weather.gov/">National Weather Service</a>. Estradas:
  <a href="https://roads.dot.ca.gov/">Caltrans</a>. El Niño:
  <a href="https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml">Climate
  Prediction Center</a>. Vulcão:
  <a href="https://www.usgs.gov/observatories/hvo">Hawaiian Volcano Observatory</a>.</p>
  <p>Página gerada de 6 em 6 horas pelo GitHub Actions e publicada no
  PythonAnywhere. Horário da California é PST (UTC-8), do Hawaii é HST (UTC-10).</p>
</footer>
</div>
<button class="tema" id="bt-tema">tema</button>
<script>{{JS}}</script>
</body>
</html>
"""


CSS += r"""
.perna{background:var(--cartao);border:1px solid var(--linha);border-radius:14px;
  padding:18px 18px 6px;margin:0 0 14px;box-shadow:var(--sombra)}
.perna>.cab{display:flex;justify-content:space-between;gap:12px;align-items:baseline;
  flex-wrap:wrap;border-bottom:1px solid var(--linha);padding-bottom:11px;
  margin-bottom:4px}
.perna .data{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--poppy);font-weight:700}
.perna .resumo{font-size:12.5px;color:var(--tinta2);font-variant-numeric:tabular-nums}
table.pernas{width:100%;border-collapse:collapse;font-size:13.5px}
table.pernas td{padding:9px 8px 9px 0;border-bottom:1px solid var(--linha);
  vertical-align:baseline}
table.pernas tr:last-child td{border-bottom:0}
table.pernas td.h{width:58px;font-weight:700;font-variant-numeric:tabular-nums;
  color:var(--pacifico2);white-space:nowrap}
table.pernas td.q b{display:block;font-weight:650}
table.pernas td.q span{color:var(--tinta2);font-size:13px}
table.pernas td.dur{width:96px;text-align:right;color:var(--tinta2);font-size:12.5px;
  white-space:nowrap;font-variant-numeric:tabular-nums}
.perna ul{margin:12px 0 14px;padding-left:0;list-style:none}
.perna ul li{position:relative;padding:0 0 9px 18px;font-size:13.5px;
  color:var(--tinta)}
.perna ul li:before{content:"";position:absolute;left:0;top:.55em;width:6px;
  height:6px;border-radius:50%;background:var(--dourado)}
@media (max-width:560px){
  .perna{padding:15px 14px 4px}
  table.pernas td.dur{display:none}
  table.pernas td.h{width:50px;font-size:12.5px}
}
"""


def _bloco_roteiro(pernas):
    h = []
    for p in pernas:
        br = p["dia"][8:10] + "/" + p["dia"][5:7]
        h.append('<article class="perna"><div class="cab"><div>'
                 '<div class="data">' + br + " &middot; "
                 + NOME_REG[p["regiao"]] + "</div><h3>"
                 + _h.escape(p["titulo"]) + '</h3></div>'
                 '<div class="resumo">' + _h.escape(p["cabecalho"]) + "</div></div>")
        h.append(_bloco_mapa(p.get("mapa_url"), p.get("mapa_link"), "",
                             "Mapa do trajeto de " + br))
        h.append('<table class="pernas">')
        for hora, oque, como, dur in p["trechos"]:
            h.append('<tr><td class="h">' + _h.escape(hora) + '</td>'
                     '<td class="q"><b>' + _h.escape(oque) + "</b><span>"
                     + _h.escape(como) + '</span></td>'
                     '<td class="dur">' + _h.escape(dur) + "</td></tr>")
        h.append("</table>")
        if p.get("notas"):
            h.append("<ul>" + "".join("<li>" + _h.escape(n) + "</li>"
                                      for n in p["notas"]) + "</ul>")
        h.append("</article>")
    return "".join(h)


CSS += r"""
img.mapa{display:block;width:100%;height:auto;margin:12px 0 6px;border-radius:10px;
  border:1px solid var(--linha);background:var(--papel2)}
a.gmaps{display:inline-flex;align-items:center;min-height:44px;font-size:13.5px;
  font-weight:650;color:var(--pacifico2);text-decoration:none}
a.gmaps:after{content:" \2192";margin-left:4px}
.item p.efeito,.perna p.efeito{margin:8px 0 0;font-size:13.5px;color:var(--tinta);
  font-weight:600}
"""
