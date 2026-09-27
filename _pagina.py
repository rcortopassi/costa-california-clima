"""Template da pagina. Separado do monitor para o HTML nao ficar preso no meio
da logica.

Leitura principal por dia: faixa de datas no topo, cartao do dia escolhido e do
dia seguinte (missa, horarios, tempo, atencao, mapa). Tudo o que e consulta de
fundo (grade windguru, Caltrans, avisos completos, El Nino, Kilauea,
climatologia e decisoes) fica recolhido por regiao no fim da pagina."""

import html as _h
import json as _j
import re as _re
from datetime import date

# Favicon: Bixby Bridge ao pôr do sol, escolhido pelo usuário em 13/09/2026 (opção G
# de sete). Fica em data URI url-encoded; o monitor faz unquote para publicar favicon.svg.
_FAVICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    '<defs>'
    "<clipPath id='c'>"
    "<rect width='64' height='64' rx='14'/>"
    '</clipPath>'
    "<linearGradient id='g' x1='0' y1='0' x2='0' y2='1'>"
    "<stop offset='0' stop-color='#F7B24A'/>"
    "<stop offset='1' stop-color='#E8730F'/>"
    '</linearGradient>'
    '</defs>'
    "<g clip-path='url(#c)'>"
    "<rect width='64' height='64' fill='url(#g)'/>"
    "<circle cx='32' cy='16' r='8' fill='#FFE3A1'/>"
    "<rect y='56' width='64' height='8' fill='#166C8F'/>"
    "<line x1='15' y1='33' x2='15' y2='52.5' stroke='#0B3B54' stroke-width='2.6'/>"
    "<line x1='21' y1='33' x2='21' y2='45.8' stroke='#0B3B54' stroke-width='2.6'/>"
    "<line x1='43' y1='33' x2='43' y2='45.8' stroke='#0B3B54' stroke-width='2.6'/>"
    "<line x1='49' y1='33' x2='49' y2='52.5' stroke='#0B3B54' stroke-width='2.6'/>"
    "<path d='M8 64 Q32 18 56 64' fill='none' stroke='#0B3B54' stroke-width='5'/>"
    "<rect x='0' y='29' width='64' height='5' fill='#0B3B54'/>"
    '</g>'
    '</svg>')
FAVICON = "data:image/svg+xml;utf8," + (_FAVICON_SVG.replace("%", "%25").replace("<", "%3C")
                                        .replace(">", "%3E").replace("#", "%23"))

CSS = r"""
*{box-sizing:border-box}
:root{
  --fundo:#F7F5F0; --cartao:#FFFFFF; --tinta:#1C2A30; --tinta2:#57656B;
  --linha:#E2DCD1; --linha2:#EEE9E1;
  --azul:#0B3B54; --azul2:#15678A; --sobre-azul:#FFFFFF; --laranja:#B9590B;
  --r-ca:#D08A2E; --r-oahu:#2F89B5; --r-bi:#B4543F;
  --ok:#4F7440; --ok-bg:rgba(85,122,69,.13);
  --at:#8F540F; --at-bg:rgba(226,150,40,.18);
  --ru:#B23A28; --ru-bg:rgba(200,70,50,.13);
  --es:#57656B; --es-bg:rgba(90,103,109,.13);
}
@media (prefers-color-scheme:dark){:root:not([data-tema="claro"]){
  --fundo:#0E1820; --cartao:#15232E; --tinta:#E9E3D9; --tinta2:#A0ABB2;
  --linha:#2A3A45; --linha2:#1E2C36;
  --azul:#8CC8E6; --azul2:#7BBEE0; --sobre-azul:#0E1820; --laranja:#F3A155;
  --r-ca:#E3A451; --r-oahu:#63B2DA; --r-bi:#DA7F66;
  --ok:#A5C08F; --ok-bg:rgba(157,172,136,.16);
  --at:#F2BE6A; --at-bg:rgba(245,187,92,.14);
  --ru:#EE8672; --ru-bg:rgba(232,107,84,.16);
  --es:#A0ABB2; --es-bg:rgba(160,171,178,.14);
}}
:root[data-tema="escuro"]{
  --fundo:#0E1820; --cartao:#15232E; --tinta:#E9E3D9; --tinta2:#A0ABB2;
  --linha:#2A3A45; --linha2:#1E2C36;
  --azul:#8CC8E6; --azul2:#7BBEE0; --sobre-azul:#0E1820; --laranja:#F3A155;
  --r-ca:#E3A451; --r-oahu:#63B2DA; --r-bi:#DA7F66;
  --ok:#A5C08F; --ok-bg:rgba(157,172,136,.16);
  --at:#F2BE6A; --at-bg:rgba(245,187,92,.14);
  --ru:#EE8672; --ru-bg:rgba(232,107,84,.16);
  --es:#A0ABB2; --es-bg:rgba(160,171,178,.14);
}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--fundo);color:var(--tinta);
  font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.env{max-width:1100px;margin:0 auto;padding:0 14px}
a{color:var(--azul2)}
.r-ca{--rc:var(--r-ca)} .r-oahu{--rc:var(--r-oahu)} .r-bi{--rc:var(--r-bi)}

/* ---------- cabecalho baixo ---------- */
header.topo{border-bottom:1px solid var(--linha);background:var(--cartao)}
.topo-in{display:flex;align-items:center;justify-content:space-between;gap:12px;
  padding-top:8px;padding-bottom:8px}
.marca{min-width:0}
h1{margin:0;font-size:20px;line-height:1.2;font-weight:700;letter-spacing:-.01em;color:var(--azul)}
.meta{margin:1px 0 0;font-size:13px;color:var(--tinta2);line-height:1.35}
.linha1{display:flex;align-items:baseline;flex-wrap:wrap;gap:0 10px}
.contagem{font-size:14px;font-weight:650;color:var(--laranja);white-space:nowrap;
  font-variant-numeric:tabular-nums}
button.tema{flex:0 0 auto}
button.tema{border:1px solid var(--linha);background:transparent;color:var(--tinta2);
  border-radius:10px;min-width:44px;min-height:44px;font-size:18px;cursor:pointer;padding:0}

/* ---------- cambio (dolar e canadense, cotacao da Wise) ----------
   Cartao independente do painel de preco de celulares, decomissionado em
   26/09/2026: mesma fonte (Wise, de hora em hora) e mesma leitura (par, seta
   e variacao), so a pele muda para a linguagem desta pagina. Fica numa faixa
   fina abaixo do cabecalho, e nao dentro dele, porque a linha1 ja disputa
   espaco com o titulo e a contagem; aqui tem a largura toda para respirar. */
.cambio-faixa{background:var(--cartao);border-bottom:1px solid var(--linha)}
.cambio{display:flex;flex-wrap:wrap;align-items:center;gap:4px 14px;padding:6px 0;
  font-size:13px;color:var(--tinta2)}
.cambio .par{display:inline-flex;align-items:baseline;gap:6px}
.cambio .rot{color:var(--tinta2)}
.cambio .vl{font-weight:650;color:var(--tinta);font-variant-numeric:tabular-nums}
.cambio .var{font-size:12px;font-weight:700;white-space:nowrap}
.cambio .var.up{color:var(--ru)} .cambio .var.dn{color:var(--ok)} .cambio .var.eq{color:var(--tinta2)}
.cambio .fx{display:block;vertical-align:middle;overflow:visible}
.cambio .sep{width:1px;height:14px;background:var(--linha)}
.cambio .fonte{color:var(--tinta2);font-size:12px}
.cambio .fonte a{color:inherit;text-decoration:underline;text-underline-offset:2px}
@media (max-width:560px){
  .cambio{font-size:12.5px;gap:4px 10px}
  .cambio .sep{display:none}
}

/* ---------- faixa de datas ---------- */
nav.datas{position:sticky;top:0;z-index:20;background:var(--fundo);
  border-bottom:1px solid var(--linha)}
.faixa-rola{display:flex;gap:12px;overflow-x:auto;padding:6px 14px 7px;
  max-width:1100px;margin:0 auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.faixa-rola::-webkit-scrollbar{display:none}
.grupo{flex:0 0 auto}
.g-nome{display:block;font-size:11.5px;line-height:16px;font-weight:650;color:var(--tinta2);
  white-space:nowrap;padding-left:2px}
.g-nome:before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;
  background:var(--rc);margin-right:5px;vertical-align:0}
.g-dias{display:flex;gap:3px}
a.d{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;
  width:46px;min-height:48px;border-radius:9px;text-decoration:none;color:var(--tinta);
  border:1px solid transparent;font-variant-numeric:tabular-nums;line-height:1.1}
a.d small{font-size:11.5px;color:var(--tinta2)}
a.d b{font-size:17px;font-weight:650}
a.d:after{content:"";position:absolute;left:9px;right:9px;bottom:4px;height:3px;border-radius:2px;
  background:linear-gradient(90deg,var(--c1) 50%,var(--c2) 50%)}
a.d.seguinte{border-color:var(--linha);background:var(--cartao)}
a.d[aria-current="date"]{background:var(--azul);color:var(--sobre-azul)}
a.d[aria-current="date"] small{color:inherit;opacity:.85}
a.d.hoje small{font-weight:700;color:var(--laranja)}
a.d[aria-current="date"].hoje small{color:inherit}

/* ---------- cartao do dia ---------- */
main{padding-top:14px}
.cartoes{display:grid;gap:14px;align-items:start}
@media (min-width:1000px){.cartoes{grid-template-columns:1fr 1fr}}
.dia{background:var(--cartao);border:1px solid var(--linha);border-radius:12px;
  padding:14px 16px 6px}
.js .dia{display:none}
.js .dia.ativo{display:block}
.dia-sup{margin:0;display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px;font-size:14px;
  color:var(--tinta2)}
.rel{font-weight:750;color:var(--laranja);text-transform:uppercase;letter-spacing:.06em;font-size:13px}
.rel:empty{display:none}
.dia-data{font-weight:600;color:var(--tinta)}
.dia-reg:before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;
  background:var(--rc);margin-right:5px}
.dia h2{margin:2px 0 0;font-size:22px;line-height:1.25;font-weight:700;letter-spacing:-.01em}
.bl{border-top:1px solid var(--linha2);margin-top:12px;padding-top:10px}
.rot-linha{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 8px;margin:0 0 4px}
h3.rot{margin:0;font-size:12px;font-weight:750;letter-spacing:.1em;text-transform:uppercase;
  color:var(--tinta2)}
.rot-linha .lit{font-size:14px;color:var(--tinta2)}
.tag{display:inline-block;font-size:12px;font-weight:650;border-radius:5px;padding:0 6px;
  line-height:20px;background:var(--es-bg);color:var(--es)}
.tag.t-prec{background:var(--at-bg);color:var(--at)}

/* missa */
.missa{display:flex;align-items:center;gap:12px}
.missa .hora{flex:0 0 auto;font-size:30px;line-height:1.1;font-weight:750;color:var(--azul);
  font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.missa .onde{flex:1 1 auto;min-width:0}
.onde b,.op-n{display:block;font-size:17px;line-height:1.3;font-weight:650}
.onde span,.op-l{display:block;font-size:15px;color:var(--tinta2);line-height:1.35}
a.bt-mapa,a.bt{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;
  min-height:44px;min-width:64px;padding:0 14px;border:1px solid var(--linha);border-radius:10px;
  font-size:15px;font-weight:650;color:var(--azul2);text-decoration:none;background:var(--cartao)}
p.sem{margin:2px 0 6px;font-size:16px}
ul.opcoes{list-style:none;margin:0;padding:0}
li.op{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--linha2)}
li.op:last-child{border-bottom:0}
.op-txt{flex:1 1 auto;min-width:0}
.op-h{display:block;font-size:17px;font-weight:750;color:var(--azul);font-variant-numeric:tabular-nums}
.op-nota{display:block;font-size:15px;color:var(--tinta);margin-top:2px}
.extra-rot{margin:10px 0 0;font-size:14px;color:var(--tinta2)}

/* detalhes recolhidos dentro do cartao */
details.mais-info{margin:4px 0 4px}
details summary{cursor:pointer;list-style:none}
details summary::-webkit-details-marker{display:none}
details.mais-info>summary{display:flex;align-items:center;min-height:44px;font-size:15px;
  font-weight:600;color:var(--azul2)}
details.mais-info>summary:before,details.sec>summary:before,details.mapa-dia>summary:before{
  content:"";flex:0 0 auto;width:7px;height:7px;margin:0 10px 0 2px;
  border-right:2px solid currentColor;border-bottom:2px solid currentColor;
  transform:rotate(-45deg)}
details[open]>summary:before{transform:rotate(45deg)}
.info{font-size:15px;color:var(--tinta);padding:0 0 8px}
.info p{margin:0 0 8px}
.info h4{margin:12px 0 2px;font-size:12px;font-weight:750;letter-spacing:.1em;
  text-transform:uppercase;color:var(--tinta2)}
.info ul{margin:0 0 8px;padding-left:18px}
.info li{margin:0 0 6px}
.info .fraco{color:var(--tinta2)}

/* o dia */
p.dia-cab2{margin:0 0 4px;font-size:14px;color:var(--tinta2)}
ol.horas{list-style:none;margin:0;padding:0}
ol.horas li{display:flex;gap:10px;padding:3px 0;font-size:16px;line-height:1.4}
ol.horas .h{flex:0 0 3.1em;font-weight:700;color:var(--azul);font-variant-numeric:tabular-nums}
ol.trechos{list-style:none;margin:0 0 8px;padding:0}
ol.trechos li{display:flex;gap:10px;padding:6px 0;border-bottom:1px solid var(--linha2)}
ol.trechos li:last-child{border-bottom:0}
ol.trechos .h{flex:0 0 3.1em;font-weight:700;color:var(--azul);font-variant-numeric:tabular-nums}
ol.trechos b{display:block;font-weight:650}
ol.trechos .como{display:block;color:var(--tinta2)}
ol.trechos .dur{display:block;font-size:14px;color:var(--tinta2);font-variant-numeric:tabular-nums}
p.resumo{margin:0;font-size:16px}

/* tempo */
p.tempo{margin:0;display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 12px;font-size:16px;
  font-variant-numeric:tabular-nums}
p.tempo b{font-weight:700}
.selo{font-size:12px;font-weight:650;border-radius:5px;padding:0 6px;line-height:20px}
.selo.s-prev{background:var(--ok-bg);color:var(--ok)}
.selo.s-clim{background:var(--es-bg);color:var(--es)}

/* atencao */
ul.atencao{list-style:none;margin:0;padding:0}
ul.atencao li{padding:6px 0 6px 10px;border-left:3px solid var(--at);margin:0 0 6px;font-size:15px}
ul.atencao li.v-ru{border-left-color:var(--ru)}
ul.atencao li b{font-weight:650}
ul.atencao li .faixa{margin-right:6px}

/* links */
.links{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start;padding-bottom:10px}
details.mapa-dia{flex:0 0 auto}
details.mapa-dia[open]{flex:1 1 100%}
details.mapa-dia>summary{display:inline-flex;align-items:center;min-height:44px;padding:0 14px 0 10px;
  border:1px solid var(--linha);border-radius:10px;font-size:15px;font-weight:650;color:var(--azul2)}
details.mapa-dia img{display:block;width:100%;height:auto;margin:8px 0 0;border-radius:8px;
  border:1px solid var(--linha);background:var(--linha2)}

/* ---------- area secundaria ---------- */
section.detalhes{margin:28px 0 0}
section.detalhes>h2{margin:0 0 8px;font-size:13px;font-weight:750;letter-spacing:.1em;
  text-transform:uppercase;color:var(--tinta2)}
.regs{display:flex;gap:6px;margin:0 0 8px}
button.reg{flex:1 1 0;min-width:0;min-height:44px;border:1px solid var(--linha);border-radius:10px;
  background:var(--cartao);color:var(--tinta);font:inherit;font-size:15px;font-weight:650;cursor:pointer;
  padding:0 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
button.reg:before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;
  background:var(--rc);margin-right:6px;vertical-align:1px}
button.reg[aria-selected="true"]{border-color:var(--azul);box-shadow:inset 0 0 0 1px var(--azul)}
.painel{background:var(--cartao);border:1px solid var(--linha);border-radius:12px;padding:0 14px}
details.sec{border-bottom:1px solid var(--linha2)}
details.sec:last-child{border-bottom:0}
details.sec>summary{display:flex;align-items:center;min-height:48px;font-size:16px;font-weight:650}
details.sec>summary .dica{margin-left:auto;padding-left:10px;font-size:14px;font-weight:400;flex:0 1 auto;
  color:var(--tinta2);text-align:right}
.sec-corpo{padding:0 0 14px;min-width:0}
.kil-full{margin-top:12px}
.kil-moldura{border:1px solid var(--linha);border-radius:10px;overflow:hidden;
 background:#14110d;box-shadow:0 2px 10px rgba(60,40,20,.12)}
.kil-moldura iframe{display:block;width:100%;height:min(1180px,88vh);border:0}
@media (max-width:640px){.kil-moldura iframe{height:min(980px,80vh)}}
.sec-corpo .leg{margin:0 0 10px;font-size:14px;color:var(--tinta2)}

.faixa{display:inline-block;border-radius:5px;padding:0 6px;font-size:12px;line-height:20px;
  font-weight:700;letter-spacing:.02em;white-space:nowrap}
.f-ok{background:var(--ok-bg);color:var(--ok)}
.f-at{background:var(--at-bg);color:var(--at)}
.f-ru{background:var(--ru-bg);color:var(--ru)}
.f-es{background:var(--es-bg);color:var(--es)}

.item{border:1px solid var(--linha);border-left-width:3px;border-radius:8px;
  padding:10px 12px;margin:0 0 8px}
.item.ok{border-left-color:var(--ok)}
.item.at{border-left-color:var(--at)}
.item.ru{border-left-color:var(--ru)}
.item.es{border-left-color:var(--linha)}
.item .cab{display:flex;justify-content:space-between;gap:8px;align-items:baseline;
  flex-wrap:wrap;margin-bottom:3px}
.item .via{font-weight:650;font-size:15px}
.item p{margin:4px 0 0;font-size:15px;color:var(--tinta)}
.item .num,.item .regra{font-size:14px;color:var(--tinta2)}
.item .txt{color:var(--tinta2)}
.item p.efeito{font-weight:600}
.vazio{margin:0;font-size:15px;color:var(--tinta2)}
img.mapa{display:block;width:100%;height:auto;margin:10px 0 4px;border-radius:8px;
  border:1px solid var(--linha);background:var(--linha2)}
a.gmaps{display:inline-flex;align-items:center;min-height:44px;font-size:15px;
  font-weight:650;color:var(--azul2);text-decoration:none}

.abas{display:flex;gap:6px;overflow-x:auto;padding:0 0 8px;scrollbar-width:thin}
.aba{flex:0 0 auto;border:1px solid var(--linha);background:var(--cartao);
  color:var(--tinta2);border-radius:999px;padding:0 14px;font-size:14px;
  cursor:pointer;min-height:44px;font-weight:600;white-space:nowrap}
.aba[aria-selected="true"]{background:var(--azul);border-color:var(--azul);color:var(--sobre-azul)}
.rolagem{overflow-x:auto;border:1px solid var(--linha);border-radius:8px;background:var(--cartao)}
table.wg{border-collapse:separate;border-spacing:0;font-size:12px;
  font-variant-numeric:tabular-nums;width:max-content;min-width:100%}
table.wg th,table.wg td{padding:3px 0;text-align:center;border-bottom:1px solid var(--linha2);
  min-width:34px;height:24px;line-height:1.1}
table.wg th.rot{position:sticky;left:0;z-index:3;background:var(--cartao);
  text-align:left;padding:3px 10px;min-width:112px;white-space:nowrap;
  font-weight:600;border-right:1px solid var(--linha);color:var(--tinta2)}
table.wg tr.dias th{background:var(--linha2);font-weight:700;border-left:1px solid var(--linha);
  color:var(--tinta);padding:6px 8px}
table.wg tr.dias th.rot{background:var(--linha2)}
table.wg tr.dias th.seu{background:var(--azul);color:var(--sobre-azul)}
table.wg tr.horas th{color:var(--tinta2);font-weight:600;background:var(--cartao)}
table.wg td.d0{border-left:1px solid var(--linha)}
table.wg td.pt{color:#1C2B31}
table.wg td.pt.branco{color:#FFF8EC}
td.seta span{display:inline-block;font-size:13px;line-height:1;color:var(--azul2)}
td.forte{font-weight:750}
.legenda{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0 0;font-size:13px;color:var(--tinta2)}
.legenda i{display:inline-block;width:12px;height:12px;border-radius:3px;
  vertical-align:-1px;margin-right:4px;border:1px solid rgba(0,0,0,.08)}
.tab-rola{overflow-x:auto}
table.hist{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}
table.hist th,table.hist td{padding:7px 8px;border-bottom:1px solid var(--linha2);text-align:right;
  white-space:nowrap}
table.hist th:first-child,table.hist td:first-child{text-align:left}
table.hist thead th{font-size:12px;color:var(--tinta2);font-weight:700}

footer{margin:28px 0 0;padding:14px 0 40px;border-top:1px solid var(--linha);
  font-size:13px;color:var(--tinta2)}
footer p{margin:0 0 6px}
footer a{color:var(--tinta2)}
.nw{white-space:nowrap}

@media (max-width:560px){
  .env{padding:0 10px}
  .faixa-rola{padding-left:10px;padding-right:10px}
  .dia{padding:12px 13px 4px}
  .dia h2{font-size:20px}
  .missa .hora{font-size:27px}
  .meta .longo{display:none}
}
@media (max-width:420px){
  button.reg{font-size:14px;padding:0 4px}
  button.reg:before{display:none}
}
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

const DIAS_SEM = ["dom","seg","ter","qua","qui","sex","sáb"];
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
  const alvo = document.getElementById("grade-" + p.regiao);
  if (!alvo) return;
  alvo.innerHTML = montaGrade(p);
  alvo.dataset.ponto = id;
  document.querySelectorAll('.abas[data-reg="' + p.regiao + '"] .aba').forEach(function(b){
    b.setAttribute("aria-selected", b.dataset.p === id ? "true" : "false");
  });
  try { localStorage.setItem("hm-ponto-" + p.regiao, id); } catch (e) {}
}

/* A grade so e desenhada quando alguem abre a secao. */
function iniciaGrade(reg){
  const g = document.getElementById("grade-" + reg);
  if (!g || g.dataset.ponto) return;
  let inicial = null;
  try { inicial = localStorage.getItem("hm-ponto-" + reg); } catch (e) {}
  const daRegiao = D.pontos.filter(function(x){ return x.regiao === reg; });
  if (!daRegiao.some(function(x){ return x.id === inicial; }))
    inicial = daRegiao.length ? daRegiao[0].id : null;
  if (inicial) abre(inicial);
}

const SLUGS = {"golden-coast": "ca", "oahu": "oahu", "hawaii": "bi"};
const LISTA = D.dias.map(function(x){ return x.dia; });
const INICIO = Date.parse("2026-12-20T00:00:00-03:00");
const FIM = Date.parse("2027-01-07T00:00:00-03:00");

/* Onde voces estao num instante: decide o fuso do "hoje". */
function regiaoDaData(t){
  if (t >= Date.parse("2027-01-04T14:00:00-10:00")) return "ca";
  if (t >= Date.parse("2026-12-28T10:00:00-10:00")) return "bi";
  if (t >= Date.parse("2026-12-24T17:43:00-08:00")) return "oahu";
  return "ca";
}
/* Antes de 21/12 voces ainda estao no Brasil ou em conexao: vale o relogio de Brasilia. */
function fusoDe(t){
  if (t < Date.parse("2026-12-21T00:00:00-03:00")) return -3;
  return regiaoDaData(t) === "ca" ? -8 : -10;
}
function hojeLocal(t){
  return new Date(t + fusoDe(t) * 3600000).toISOString().slice(0, 10);
}
function diaPadrao(t){
  if (t < INICIO) return LISTA[0];
  const iso = hojeLocal(t);
  if (iso < LISTA[0]) return LISTA[0];
  if (iso > LISTA[LISTA.length - 1]) return LISTA[LISTA.length - 1];
  return LISTA.indexOf(iso) >= 0 ? iso : LISTA[0];
}
function hojeNaViagem(t){
  if (t < INICIO || t >= FIM) return "";
  const iso = hojeLocal(t);
  return LISTA.indexOf(iso) >= 0 ? iso : "";
}

function mostraRegiao(reg){
  document.querySelectorAll(".painel").forEach(function(el){
    el.hidden = el.dataset.reg !== reg;
  });
  document.querySelectorAll("button.reg").forEach(function(b){
    b.setAttribute("aria-selected", b.dataset.reg === reg ? "true" : "false");
  });
}

let diaAtual = "";
function selecionaDia(dia, origem){
  const i = LISTA.indexOf(dia);
  if (i < 0) return;
  diaAtual = dia;
  const prox = i + 1 < LISTA.length ? LISTA[i + 1] : "";
  const hoje = hojeNaViagem(Date.now());
  const amanha = hoje ? LISTA[LISTA.indexOf(hoje) + 1] || "" : "";

  document.querySelectorAll("article.dia").forEach(function(a){
    const d = a.dataset.dia;
    const ativo = d === dia || d === prox;
    a.classList.toggle("ativo", ativo);
    const rel = a.querySelector(".rel");
    if (!rel) return;
    if (!ativo) { rel.textContent = ""; return; }
    if (d === hoje) rel.textContent = "Hoje";
    else if (d === amanha) rel.textContent = "Amanhã";
    else if (d === prox) rel.textContent = "Dia seguinte";
    else rel.textContent = "";
  });

  const rola = document.getElementById("faixa");
  document.querySelectorAll("a.d").forEach(function(b){
    const d = b.dataset.dia;
    if (d === dia) b.setAttribute("aria-current", "date");
    else b.removeAttribute("aria-current");
    b.classList.toggle("seguinte", d === prox);
    b.classList.toggle("hoje", d === hoje);
    const s = b.querySelector("small");
    if (s) s.textContent = d === hoje ? "hoje" : s.dataset.sem;
    if (d === dia && rola){
      rola.scrollLeft = Math.max(0, b.offsetLeft - rola.offsetLeft - rola.clientWidth / 2 + b.offsetWidth / 2);
    }
  });

  const card = document.getElementById("d-" + dia);
  if (card) mostraRegiao(card.dataset.reg);

  if (origem === "toque"){
    try { history.replaceState(null, "", "#dia-" + dia); } catch (e) {}
    if (card){
      const topo = card.getBoundingClientRect().top + window.pageYOffset
                 - (document.querySelector("nav.datas").offsetHeight + 8);
      if (window.pageYOffset > topo) window.scrollTo(0, topo);
    }
  }
}

function diaDoEndereco(){
  const h = (location.hash || "").replace("#", "");
  if (h.indexOf("dia-") === 0 && LISTA.indexOf(h.slice(4)) >= 0) return h.slice(4);
  const reg = SLUGS[h];
  if (reg){
    const padrao = diaPadrao(Date.now());
    const x = D.dias.find(function(y){ return y.dia === padrao; });
    if (x && x.reg === reg) return padrao;
    const primeiro = D.dias.find(function(y){ return y.reg === reg; });
    return primeiro ? primeiro.dia : "";
  }
  return "";
}

function contagem(){
  const el = document.getElementById("contagem");
  if (!el) return;
  const t = Date.now();
  if (t < INICIO){
    const dias = Math.ceil((INICIO - t) / 86400000);
    el.textContent = dias === 1 ? "falta 1 dia" : "faltam " + dias + " dias";
  } else if (t < FIM){
    const i = LISTA.indexOf(hojeLocal(t));
    el.textContent = i >= 0 ? "dia " + (i + 1) + " de " + LISTA.length : "em viagem";
  } else {
    el.textContent = "viagem concluída";
  }
}

function tema(){
  const r = document.documentElement;
  const escuro = window.matchMedia("(prefers-color-scheme:dark)").matches;
  const atual = r.getAttribute("data-tema") || (escuro ? "escuro" : "claro");
  const novo = atual === "escuro" ? "claro" : "escuro";
  r.setAttribute("data-tema", novo);
  try { localStorage.setItem("cd-tema", novo); } catch (e) {}
}

/* ---------- cambio (dolar e canadense, cotacao da Wise) ----------
   Mesmo mecanismo do painel de precos que este cartao substitui (decomissionado
   em 26/09/2026): wise.json fica ao lado do index.html, mesma origem, e e
   reescrito de hora em hora pelo LaunchAgent do Mac e a cada 3h pelo workflow
   cotacao-wise, no repositorio precos-zfold8. D.wise traz o valor de quando a
   pagina foi gerada, para quem abre sem rede ou antes do primeiro fetch; dai
   pra frente quem manda e o fetch de mesma origem em buscaCambio(). Nao da pra
   ir na Wise direto do navegador: o endpoint dela responde 200 mas sem
   Access-Control-Allow-Origin. */
function fmtTaxa(v){
  return v.toLocaleString("pt-BR", {minimumFractionDigits: 4, maximumFractionDigits: 4});
}
function faixaCambio(serie){
  if (!serie || serie.length < 2) return "";
  const min = Math.min.apply(null, serie), max = Math.max.apply(null, serie);
  const w = 44, h = 16, n = serie.length, amp = (max - min) || 1;
  const pts = serie.map(function(v, i){
    const x = (i / (n - 1)) * w, y = h - ((v - min) / amp) * h;
    return x.toFixed(1) + "," + y.toFixed(1);
  }).join(" ");
  // dolar em alta e ma noticia para quem vai gastar em dolar na viagem, entao
  // sobe em vermelho (--ru) e cai em verde (--ok), a mesma convencao de bom e
  // ruim que o resto da pagina usa para tempo e estrada.
  const cor = serie[serie.length - 1] >= serie[0] ? "var(--ru)" : "var(--ok)";
  return '<svg class="fx" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '" aria-hidden="true">' +
    '<polyline points="' + pts + '" fill="none" stroke="' + cor + '" stroke-width="1.6" ' +
    'stroke-linecap="round" stroke-linejoin="round"/></svg>';
}
function pintaCambio(w){
  const el = document.getElementById("cambio");
  if (!el || !w) return;
  const pares = w.pares || {};
  const usd = pares.USDBRL, cad = pares.CADBRL;
  if (!usd && !cad){ el.hidden = true; return; }

  function bloco(rot, d){
    if (!d) return "";
    const serie = d.serie || [];
    const faixa = faixaCambio(serie);
    let variacao = "";
    const base = serie.length > 1 ? serie[serie.length - 2] : d.anterior;
    if (base){
      const pct = (d.valor / base - 1) * 100;
      const cls = Math.abs(pct) < 0.005 ? "eq" : (pct > 0 ? "up" : "dn");
      const seta = cls === "eq" ? "" : (pct > 0 ? "▲" : "▼");
      variacao = ' <span class="var ' + cls + '">' + seta +
        Math.abs(pct).toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2}) +
        "%</span>";
    }
    const aviso = d.velho ? " Leitura mais recente falhou; valor anterior mantido." : "";
    return '<span class="par" title="Cotação intermediária da Wise, atualiza de hora em hora.' + aviso + '">' +
      '<span class="rot">' + rot + '</span>' +
      '<span class="vl">R$ ' + fmtTaxa(d.valor) + '</span>' + variacao + faixa + '</span>';
  }

  const dt = w.atualizado ? new Date(w.atualizado) : null;
  const hora = dt ? dt.toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit"}) : "";
  el.innerHTML = bloco("Dólar", usd) +
    (usd && cad ? '<span class="sep"></span>' : "") +
    bloco("Dólar CAD", cad) +
    '<span class="sep"></span>' +
    '<span class="fonte"><a href="https://wise.com/br/currency-converter/usd-to-brl-rate" ' +
    'target="_blank" rel="noopener">Wise</a>' + (hora ? " " + hora : "") + '</span>';
  el.hidden = false;
}
async function buscaCambio(){
  try{
    const r = await fetch("wise.json?t=" + Date.now(), {cache: "no-store"});
    if (!r.ok) return;
    const w = await r.json();
    if (w && w.pares) pintaCambio(w);
  }catch(e){ /* HTML aberto de disco, ou rede fora: fica o valor embutido */ }
}

(function inicia(){
  document.querySelectorAll("a.d").forEach(function(b){
    b.addEventListener("click", function(ev){
      ev.preventDefault();
      selecionaDia(b.dataset.dia, "toque");
    });
  });
  document.querySelectorAll("button.reg").forEach(function(b){
    b.addEventListener("click", function(){ mostraRegiao(b.dataset.reg); });
  });
  document.querySelectorAll(".aba").forEach(function(b){
    b.addEventListener("click", function(){ abre(b.dataset.p); });
  });
  document.querySelectorAll("details.sec-grade").forEach(function(det){
    det.addEventListener("toggle", function(){ if (det.open) iniciaGrade(det.dataset.reg); });
  });
  /* mapa do trajeto: a imagem so e baixada quando alguem abre */
  document.querySelectorAll("details.mapa-dia").forEach(function(det){
    det.addEventListener("toggle", function(){
      const img = det.querySelector("img[data-src]");
      if (det.open && img){ img.src = img.dataset.src; img.removeAttribute("data-src"); }
    });
  });
  const bt = document.getElementById("bt-tema");
  if (bt) bt.addEventListener("click", tema);

  selecionaDia(diaDoEndereco() || diaPadrao(Date.now()), "inicio");
  window.addEventListener("hashchange", function(){
    const d = diaDoEndereco();
    if (d && d !== diaAtual) selecionaDia(d, "endereco");
  });
  /* aba reaberta de manha: sem dia escolhido na URL, volta para o dia de hoje */
  document.addEventListener("visibilitychange", function(){
    if (document.visibilityState !== "visible") return;
    contagem();
    if (!diaDoEndereco()){
      const d = diaPadrao(Date.now());
      if (d !== diaAtual) selecionaDia(d, "inicio");
    }
  });
  contagem();
  setInterval(contagem, 60000);

  pintaCambio(D.wise);
  buscaCambio();
})();
"""


VER = {
    "bom":     ("ok", "f-ok", "pode ir"),
    "atencao": ("at", "f-at", "com ressalva"),
    "ruim":    ("ru", "f-ru", "não vá"),
    "espera":  ("es", "f-es", "regra armada"),
}
DICA_VER = {"bom": ("pode ir", "podem ir"), "atencao": ("com ressalva", "com ressalva"),
            "ruim": ("não vá", "não vá"), "espera": ("regra armada", "regras armadas")}
NOME_REG = {"ca": "Golden Coast", "oahu": "Oʻahu", "bi": "Hawaiʻi"}
SLUG_REG = {"ca": "golden-coast", "oahu": "oahu", "bi": "hawaii"}
SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira",
          "sábado", "domingo"]
SEMANA_CURTA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
# Dias que so tem missa, sem etapa no roteiro: o titulo do cartao sai daqui.
TITULO_SEM_ETAPA = {"2026-12-20": "Embarque em Brasília", "2027-01-06": "Voo de volta"}

LEGENDA_VENTO = [("até 9", "#AADFF2"), ("12", "#82D2E9"), ("15", "#84D6A6"),
                 ("18", "#BBDE6B"), ("21", "#ECD84B"), ("25", "#F2A93B"),
                 ("30", "#E8703A"), ("35+", "#D8402C")]


def _e(t):
    return _h.escape(str(t))


def _br(dia):
    return dia[8:10] + "/" + dia[5:7]


def _gmaps_busca(q):
    from urllib.parse import quote
    return "https://www.google.com/maps/search/?api=1&query=" + quote(q)


def _link(href, texto, cls="bt-mapa", rotulo=""):
    return ('<a class="' + cls + '" href="' + _e(href) + '" target="_blank" rel="noopener"'
            + (' aria-label="' + _e(rotulo) + '"' if rotulo else "") + ">" + texto + "</a>")


# ---------------------------------------------------------------- dias

def _dias(d):
    """Lista de dias da viagem: uniao das datas das etapas e das missas.
    'reg' e onde o dia comeca (a regiao da missa, que e o mais importante do
    dia); 'reg2' e onde ele termina, que e onde o dia seguinte comeca."""
    etapa = {e["dia"]: e for e in d["etapas"]}
    missas = {}
    for m in d["missas"]:
        missas.setdefault(m["dia"], []).append(m)
    perna = {p["dia"]: p for p in d["roteiro"]}
    out = []
    for dia in sorted(set(etapa) | set(missas)):
        ms = missas.get(dia, [])
        prim = next((m for m in ms if m.get("badge") != "opcional"), ms[0] if ms else None)
        reg = prim["regiao"] if prim else etapa[dia]["regiao"]
        out.append({"dia": dia, "reg": reg, "etapa": etapa.get(dia), "missas": ms,
                    "prim": prim, "perna": perna.get(dia)})
    for i, x in enumerate(out):
        x["reg2"] = out[i + 1]["reg"] if i + 1 < len(out) else x["reg"]
    return out


def _faixa(dias):
    grupos = []
    for x in dias:
        if not grupos or grupos[-1][0] != x["reg"]:
            grupos.append((x["reg"], []))
        grupos[-1][1].append(x)
    h = []
    for reg, xs in grupos:
        h.append('<div class="grupo r-' + reg + '"><span class="g-nome">' + _e(NOME_REG[reg])
                 + '</span><div class="g-dias">')
        for x in xs:
            wd = date.fromisoformat(x["dia"]).weekday()
            rot = (SEMANA[wd] + ", " + _br(x["dia"]) + "/" + x["dia"][:4] + ", "
                   + NOME_REG[x["reg"]]
                   + ("" if x["reg2"] == x["reg"] else " a " + NOME_REG[x["reg2"]]))
            h.append('<a class="d" href="#dia-' + x["dia"] + '" data-dia="' + x["dia"]
                     + '" style="--c1:var(--r-' + x["reg"] + ');--c2:var(--r-' + x["reg2"] + ')"'
                     + ' aria-label="' + _e(rot) + '"><small data-sem="' + SEMANA_CURTA[wd] + '">'
                     + SEMANA_CURTA[wd] + "</small><b>" + x["dia"][8:10] + "</b></a>")
        h.append("</div></div>")
    return "".join(h)


# ---------------------------------------------------------------- cartao

def _horarios_igrejas(chaves, igrejas):
    usadas = []
    for k in chaves:
        if k not in usadas:
            usadas.append(k)
    if not usadas:
        return ""
    return ("<h4>Horários de cada igreja</h4><ul>"
            + "".join("<li><b>" + _e(igrejas[k]["nome"]) + ":</b> " + _e(igrejas[k]["horarios"])
                      + '. <a href="' + _e(igrejas[k]["fonte"]) + '" target="_blank" rel="noopener">'
                      "site da paróquia</a></li>" for k in usadas)
            + "</ul>")


def _op(hora, ig, nota=""):
    return ('<li class="op"><div class="op-txt"><span class="op-h">' + _e(hora) + "</span>"
            '<span class="op-n">' + _e(ig["nome"]) + '</span><span class="op-l">' + _e(ig["lugar"])
            + "</span>" + ('<span class="op-nota">' + _e(nota) + "</span>" if nota else "")
            + "</div>" + _link(_gmaps_busca(ig["busca"]), "Mapa", rotulo="Mapa: " + ig["nome"])
            + "</li>")


def _bloco_missa(x, igrejas):
    m = x["prim"]
    if not m:
        return ""
    extras = [o for o in x["missas"] if o is not m]
    tags = '<span class="lit">' + _e(m["liturgia"]) + "</span>"
    if m.get("preceito"):
        tags += '<span class="tag t-prec">preceito</span>'
    if m.get("badge"):
        tags += '<span class="tag">' + _e(m["badge"]) + "</span>"
    if m.get("confirmar"):
        tags += '<span class="tag">confirmar em dezembro</span>'
    h = ['<section class="bl bl-missa"><div class="rot-linha"><h3 class="rot">Missa</h3>'
         + tags + "</div>"]
    info = []
    chaves = []

    if m.get("rec"):
        r = m["rec"]
        ig = igrejas[r["igreja"]]
        chaves.append(r["igreja"])
        h.append('<div class="missa"><span class="hora">' + _e(r["hora"]) + '</span>'
                 '<div class="onde"><b>' + _e(ig["nome"]) + "</b><span>" + _e(ig["lugar"])
                 + "</span></div>" + _link(_gmaps_busca(ig["busca"]), "Mapa",
                                           rotulo="Mapa: " + ig["nome"]) + "</div>")
        if m.get("aviso"):
            h.append('<p class="sem aviso-missa">' + _e(m["aviso"]) + "</p>")
        info.append("<p>" + _e(r["dist"][:1].upper() + r["dist"][1:]) + ". " + _e(r["porque"]) + "</p>")
        if m.get("sem"):
            info.append("<p>" + _e(m["sem"]) + "</p>")
        if m.get("alts"):
            info.append('<h4>Outras possíveis</h4><ul class="opcoes">'
                        + "".join(_op(a["hora"], igrejas[a["igreja"]], a["nota"]) for a in m["alts"])
                        + "</ul>")
            chaves += [a["igreja"] for a in m["alts"]]
    else:
        if m.get("sem"):
            frase = m["sem"].split(". ")[0].rstrip(".") + "."
            h.append('<p class="sem">' + _e(frase) + "</p>")
            info.append("<p>" + _e(m["sem"]) + "</p>")
        if m.get("alts"):
            h.append('<ul class="opcoes">'
                     + "".join(_op(a["hora"], igrejas[a["igreja"]]) for a in m["alts"]) + "</ul>")
            info.append("<ul>" + "".join("<li><b>" + _e(a["hora"]) + ", "
                                         + _e(igrejas[a["igreja"]]["nome"]) + ":</b> " + _e(a["nota"])
                                         + "</li>" for a in m["alts"]) + "</ul>")
            chaves += [a["igreja"] for a in m["alts"]]
    if m.get("descartadas"):
        info.append('<p class="fraco">' + _e(m["descartadas"]) + "</p>")

    for o in extras:
        rot = (o.get("badge") or "também").capitalize() + ": " + o["liturgia"]
        h.append('<p class="extra-rot">' + _e(rot) + "</p>")
        itens = ([(o["rec"]["hora"], o["rec"]["igreja"], "")] if o.get("rec") else []) \
            + [(a["hora"], a["igreja"], "") for a in o.get("alts", [])]
        h.append('<ul class="opcoes">' + "".join(_op(hr, igrejas[k]) for hr, k, _ in itens) + "</ul>")
        info.append("<h4>" + _e(rot) + "</h4>")
        if o.get("sem"):
            info.append("<p>" + _e(o["sem"]) + "</p>")
        notas = [(a["hora"], a["igreja"], a["nota"]) for a in o.get("alts", [])]
        if notas:
            info.append("<ul>" + "".join("<li><b>" + _e(hr) + ", " + _e(igrejas[k]["nome"]) + ":</b> "
                                         + _e(n) + "</li>" for hr, k, n in notas) + "</ul>")
        chaves += [k for _, k, _ in itens]

    info.append(_horarios_igrejas(chaves, igrejas))
    resumo = ("Por que esta, e outras missas" if m.get("rec") and m.get("alts") else
              "Por que esta" if m.get("rec") else "Como escolher")
    h.append('<details class="mais-info"><summary>' + resumo + '</summary><div class="info">'
             + "".join(info) + "</div></details></section>")
    return "".join(h)


def _bloco_o_dia(x):
    p, e = x["perna"], x["etapa"]
    if p:
        h = ['<section class="bl bl-dia"><div class="rot-linha"><h3 class="rot">O dia</h3></div>',
             '<p class="dia-cab2">' + _e(p["cabecalho"][:1].upper() + p["cabecalho"][1:]) + "</p>",
             '<ol class="horas">']
        for hora, oque, _como, _dur in p["trechos"]:
            h.append('<li><span class="h">' + _e(hora) + "</span><span>" + _e(oque) + "</span></li>")
        h.append('</ol><details class="mais-info"><summary>Como ir e observações</summary>'
                 '<div class="info"><ol class="trechos">')
        for hora, oque, como, dur in p["trechos"]:
            dur_ok = dur.strip() not in ("", "—", "-")
            h.append('<li><span class="h">' + _e(hora) + "</span><div><b>" + _e(oque) + "</b>"
                     '<span class="como">' + _e(como) + "</span>"
                     + ('<span class="dur">' + _e(dur) + "</span>" if dur_ok else "") + "</div></li>")
        h.append("</ol>")
        if p.get("notas"):
            h.append("<h4>Observações</h4><ul>" + "".join("<li>" + _e(n) + "</li>" for n in p["notas"])
                     + "</ul>")
        h.append("</div></details></section>")
        return "".join(h)
    if e:
        return ('<section class="bl bl-dia"><div class="rot-linha"><h3 class="rot">O dia</h3></div>'
                '<p class="resumo">' + _e(e["resumo"]) + "</p></section>")
    return ""


def _bloco_tempo(x, d):
    e = x["etapa"]
    if not e:
        return ""
    ponto = d["por_id"].get(e["pontos"][-1])
    pv = d["prev_por_dia"].get(x["dia"])
    if pv:
        partes = ["máx <b>" + str(round(pv["tmax"])) + "°</b>",
                  "mín " + str(round(pv["tmin"])) + "°",
                  "chuva <b>" + str(round(pv["prob"])) + "%</b>"
                  + (" (" + f'{pv["mm"]:.1f}'.replace(".", ",") + " mm)" if pv["mm"] >= 0.1 else "")]
        if pv.get("rajada") and pv["rajada"] >= 25:
            partes.append("rajada " + str(round(pv["rajada"])) + " nós")
        sol = (pv.get("sol") or "").split(" / ")[-1]
        if sol:
            partes.append("pôr do sol " + _e(sol))
        selo = '<span class="selo s-prev">previsão</span>'
    elif ponto:
        n = ponto["normal"]
        partes = ["máx <b>" + str(round(n["tmax"])) + "°</b>",
                  "mín " + str(round(n["tmin"])) + "°",
                  "chuva em " + str(n["pct"]) + "% dos dias"]
        if ponto.get("por_do_sol"):
            partes.append("pôr do sol " + _e(ponto["por_do_sol"]))
        selo = '<span class="selo s-clim">climatologia</span>'
    else:
        return ""
    lugar = ('<span class="lit">' + _e(ponto["nome"]) + "</span>") if ponto else ""
    return ('<section class="bl bl-tempo"><div class="rot-linha"><h3 class="rot">Tempo</h3>'
            + lugar + selo + '</div><p class="tempo">'
            + "".join("<span>" + p + "</span>" for p in partes) + "</p></section>")


def _bloco_atencao(x, d):
    dia = x["dia"]
    regs = {x["reg"], x["reg2"]}
    if x["etapa"]:
        regs.add(x["etapa"]["regiao"])
    itens = []
    for dec in d["decisoes"]:
        if dec["dia"] == dia and dec["veredito"] in ("ruim", "atencao"):
            cls, faixa, rotulo = VER[dec["veredito"]]
            itens.append('<li class="v-' + cls + '"><span class="faixa ' + faixa + '">' + rotulo
                         + "</span><b>" + _e(dec["titulo"]) + ".</b> " + _e(dec["motivo"]) + "</li>")
    for a in d["alertas"]:
        fim = (a.get("fim") or "")[:10]
        if not regs & set(a.get("regioes", [])) or (fim and fim < dia):
            continue
        # o mapa diz em que dias o trajeto cruza a area ("em 22/12 e 24/12"): fora deles, nao e do dia
        datas = _re.findall(r"\b\d{2}/\d{2}\b(?!/)", a.get("efeito") or "")
        if datas and _br(dia) not in datas:
            continue
        grave = a.get("severidade") in ("Severe", "Extreme")
        itens.append('<li class="v-' + ("ru" if grave else "at") + '"><span class="faixa f-'
                     + ("ru" if grave else "at") + '">aviso</span><b>' + _e(a["evento"]) + ".</b> "
                     + _e(a.get("efeito") or a.get("onde") or "") + "</li>")
    if not itens:
        return ""
    return ('<section class="bl bl-atencao"><div class="rot-linha"><h3 class="rot">Atenção</h3></div>'
            '<ul class="atencao">' + "".join(itens) + "</ul></section>")


def _bloco_links(x):
    p = x["perna"]
    if not p or not (p.get("mapa_link") or p.get("mapa_url")):
        return ""
    h = ['<div class="bl links">']
    if p.get("mapa_link"):
        h.append(_link(p["mapa_link"], "Trajeto no Google Maps", cls="bt"))
    if p.get("mapa_url"):
        h.append('<details class="mapa-dia"><summary>Mapa</summary><img data-src="' + _e(p["mapa_url"])
                 + '" alt="Mapa do trajeto de ' + _br(x["dia"]) + '" width="1200" height="900"></details>')
    h.append("</div>")
    return "".join(h)


def _cartao_dia(x, d):
    dia = x["dia"]
    e = x["etapa"]
    titulo = e["titulo"] if e else TITULO_SEM_ETAPA.get(dia, "")
    wd = date.fromisoformat(dia).weekday()
    regs = NOME_REG[x["reg"]] + ("" if x["reg2"] == x["reg"] else " a " + NOME_REG[x["reg2"]])
    return ('<article class="dia" id="d-' + dia + '" data-dia="' + dia + '" data-reg="' + x["reg"] + '">'
            '<header><p class="dia-sup"><span class="rel"></span><span class="dia-data">'
            + SEMANA[wd] + ", " + _br(dia) + '</span><span class="dia-reg r-' + x["reg"] + '">'
            + _e(regs) + "</span></p>"
            + ("<h2>" + _e(titulo) + "</h2>" if titulo else "") + "</header>"
            + _bloco_missa(x, d["igrejas"])
            + _bloco_o_dia(x)
            + _bloco_tempo(x, d)
            + _bloco_atencao(x, d)
            + _bloco_links(x)
            + "</article>")


# ---------------------------------------------------------------- area secundaria

def _bloco_decisoes(decs):
    h = []
    for d in decs:
        cls, faixa, rotulo = VER[d["veredito"]]
        h.append('<article class="item ' + cls + '">'
                 '<div class="cab"><span class="via">'
                 + _br(d["dia"]) + " &middot; " + _e(d["titulo"]) + " &middot; " + _e(d["quando"])
                 + '</span><span class="faixa ' + faixa + '">' + rotulo + "</span></div>"
                 "<p><b>" + _e(d["motivo"]) + "</b></p>"
                 + ('<p class="num">' + _e(d["numeros"]) + "</p>" if d["numeros"] else "")
                 + '<p class="regra">Gatilho: ' + _e(d["regra"]) + "</p>"
                 '<p class="txt">' + _e(d["recomenda"]) + "</p></article>")
    return "".join(h)


def _bloco_mapa(url, link, efeito, alt):
    txt = ('<p class="efeito">' + _e(efeito) + "</p>") if efeito else ""
    if not url:
        return txt
    return (txt
            # no celular o mapa sai com ~320 px; o toque abre a imagem inteira para ampliar
            + '<a href="' + _e(url) + '" target="_blank" rel="noopener">'
            + '<img class="mapa" loading="lazy" src="' + _e(url) + '" alt="'
            + _e(alt) + '" width="1200" height="900"></a>'
            + (('<a class="gmaps" href="' + _e(link) + '" target="_blank" rel="noopener">'
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
                     + v["rodovia"] + " &middot; " + _e(i["area"].title())
                     + "</span>" + faixa + "</div><p>" + _e(i["texto"])
                     + "</p>" + _bloco_mapa(i.get("mapa_url"), i.get("mapa_link"),
                                            i.get("efeito", ""), "Mapa: " + i["texto"][:120])
                     + "</div>")
    return "".join(h)


def _bloco_avisos(alertas):
    h = []
    for a in alertas:
        grave = a["severidade"] in ("Severe", "Extreme")
        cls = "ru" if grave else "at"
        h.append('<div class="item ' + cls + '"><div class="cab"><span class="via">'
                 + _e(a["evento"]) + " &middot; "
                 + ", ".join(NOME_REG.get(r, r) for r in a["regioes"])
                 + '</span><span class="faixa f-' + cls + '">'
                 + _e(a["severidade"] or "aviso") + "</span></div><p>"
                 + _e(a["manchete"] or a["descricao"][:300]) + "</p>"
                 '<p class="num">' + _e(a["onde"]) + "</p>"
                 + _bloco_mapa(a.get("mapa_url"), a.get("mapa_link"), a.get("efeito", ""),
                               "Mapa do aviso " + a["evento"]) + "</div>")
    return "".join(h)


def _bloco_pacifico(e, k):
    h = []
    if e is None:
        pass
    elif e.get("status"):
        h.append('<div class="item at"><div class="cab">'
                 '<span class="via">El Niño &middot; Climate Prediction Center, NOAA</span>'
                 '<span class="faixa f-at">' + _e(e["status"]) + "</span></div>"
                 "<p>" + _e(e.get("sinopse") or "") + "</p>"
                 '<p class="num">Boletim de ' + _e(e.get("emitido") or "data não lida")
                 + ". O CPC concentra o sinal de chuva acima da média na costa da "
                   "California com pico entre janeiro e março de 2027, ou seja, "
                   "depois da viagem.</p></div>")
    else:
        h.append('<p class="vazio">Boletim ENSO indisponível nesta rodada.</p>')
    if k and k.get("cor"):
        ativo = k["cor"] in ("ORANGE", "RED")
        h.append('<div class="item ' + ("ru" if k["cor"] == "RED" else ("at" if ativo else "ok"))
                 + '"><div class="cab"><span class="via">Kilauea &middot; '
                   'Hawaiian Volcano Observatory, USGS</span>'
                   '<span class="faixa f-' + ("at" if ativo else "ok") + '">'
                 + _e(k["cor"] + " / " + k["nivel"]) + "</span></div><p>"
                 + ("Fonte de lava ativa ou episódio em curso. Vale a subida noturna "
                    "ao mirante da cratera." if ativo else
                    "Sem episódio ativo agora. A cratera vale de dia; o brilho "
                    "noturno só existe em erupção.")
                 + '</p></div>')
    if k is not None:
        # O monitor do Kilauea e um site completo (status, cameras ao vivo,
        # fotos e mapa das bocas) e se atualiza sozinho de 5 em 5 minutos.
        # Embutir a pagina inteira evita manter o mesmo conteudo em dois
        # projetos, que divergiriam. Mesma origem, sem X-Frame-Options.
        # O src so entra quando alguem abre a secao (ver JS: details.kil-full).
        h.append('<div class="kil-full">'
                 '<p class="leg">Abaixo vai o monitor do Kilauea inteiro, o mesmo de '
                 '<a href="../kilauea/" target="_blank" rel="noopener">/kilauea/</a>: '
                 'status e fase da erupção, câmeras ao vivo do USGS, fotos do último '
                 'episódio e o mapa das bocas, mirantes e estacionamentos. '
                 'Ele se atualiza sozinho de 5 em 5 minutos.</p>'
                 '<div class="kil-moldura">'
                 '<iframe data-src="../kilauea/" title="Monitor do Kilauea" '
                 'loading="lazy" referrerpolicy="same-origin"></iframe></div>'
                 '<p class="num">Se ficar apertado nesta janela, '
                 '<a href="../kilauea/" target="_blank" rel="noopener">abra em uma aba '
                 'separada</a>.</p></div>')
    return "".join(h)


LEG = {
    "grade": "De 3 em 3 horas, sete dias, hora local. Azul e verde é calmo, amarelo e laranja é "
             "vento, vermelho é tempestade; violeta na última linha é visibilidade baixa. As datas "
             "em azul são dias do roteiro.",
    "estrada_bi": "Não há boletim como o da Caltrans. A estrada que fecha é a Mauna Kea Access Road, "
                  "até o Mauna Kea Summit, e fecha por gelo: a regra do cume, em Ir ou não ir, "
                  "antecipa isso pelo nível de congelamento.",
    "hist": {
        "ca": "Médias de 21 a 24 de dezembro, 1995 a 2025, e o pôr do sol na semana do solstício.",
        "oahu": "Médias de 26/12 a 05/01, 2000 a 2025, e o pôr do sol.",
        "bi": "Médias de 26/12 a 05/01, 2000 a 2025, e o pôr do sol. O Mauna Kea Summit fica "
              "abaixo de zero à noite nesta janela.",
    },
}


def _plural(n, um, varios):
    return str(n) + " " + (um if n == 1 else varios)


def _painel(d, reg, aberto):
    secoes = []

    def sec(titulo, dica, corpo, extra_cls="", attrs=""):
        secoes.append('<details class="' + ("sec " + extra_cls).strip() + '"' + attrs + "><summary>" + titulo
                      + ('<span class="dica">' + dica + "</span>" if dica else "")
                      + '</summary><div class="sec-corpo">' + corpo + "</div></details>")

    meus = [p for p in d["pontos"] if p["regiao"] == reg]
    abas = "".join('<button class="aba" role="tab" aria-selected="false" data-p="' + p["id"]
                   + '" title="' + _e(p["papel"]) + '">' + _e(p["nome"]) + "</button>" for p in meus)
    leg_vento = "".join('<span><i style="background:' + c + '"></i>' + t + "</span>"
                        for t, c in LEGENDA_VENTO)
    sec("Previsão em grade", "7 dias",
        '<p class="leg">' + _e(LEG["grade"]) + "</p>"
        '<div class="abas" role="tablist" data-reg="' + reg + '">' + abas + "</div>"
        '<div class="rolagem" id="grade-' + reg + '"></div>'
        '<div class="legenda"><span>vento e rajada, em nós:</span>' + leg_vento + "</div>",
        "sec-grade", ' data-reg="' + reg + '"')

    if reg == "ca":
        fech = sum(1 for v in d["estradas"] for i in v["itens"]
                   if i["na_rota"] and i["fechado"] and not i.get("livre"))
        sec("Estrada, Caltrans", _plural(fech, "fechamento", "fechamentos") if fech
            else ("sem fechamento" if d["estradas"] else "indisponível"),
            _bloco_estradas(d["estradas"]))
    if reg == "bi":
        sec("Estrada", "Mauna Kea Access Road", '<p class="vazio">' + _e(LEG["estrada_bi"]) + "</p>")

    avisos = [a for a in d["alertas"] if reg in a.get("regioes", [])]
    sec("Avisos oficiais", _plural(len(avisos), "ativo", "ativos") if avisos else "nenhum",
        _bloco_avisos(avisos) if avisos else
        '<p class="vazio">Nenhum aviso ativo do National Weather Service nos pontos de '
        + _e(NOME_REG[reg]) + ".</p>")

    if reg == "ca":
        es = d.get("enso") or {}
        sec("El Niño", _e(es.get("status") or ""), _bloco_pacifico(es, None))
    if reg == "bi":
        k = d.get("kilauea") or {}
        sec("Kilauea", _e((k.get("cor", "") + " / " + k.get("nivel", "")) if k.get("cor") else ""),
            _bloco_pacifico(None, k), "kil-full")

    decs = [x for x in d["decisoes"] if x.get("regiao") == reg]
    if decs:
        cont = {}
        for x in decs:
            cont[x["veredito"]] = cont.get(x["veredito"], 0) + 1
        dica = ", ".join(str(cont[v]) + " " + (DICA_VER[v][0] if cont[v] == 1 else DICA_VER[v][1])
                         for v in ("ruim", "atencao", "bom", "espera") if cont.get(v))
        sec("Ir ou não ir", _e(dica), _bloco_decisoes(decs))

    linhas = []
    for p in meus:
        n = p["normal"]
        linhas.append("<tr><td>" + _e(p["nome"]) + "</td><td>" + f'{n["tmax"]:.1f}'
                      + "</td><td>" + f'{n["tmin"]:.1f}' + "</td><td>" + f'{n["mm"]:.1f}'
                      + "</td><td>" + str(n["pct"]) + "%</td><td>" + str(n["forte"])
                      + "%</td><td>" + (p.get("por_do_sol") or "-") + "</td></tr>")
    sec("Climatologia", "médias de 25 a 30 anos",
        '<p class="leg">' + _e(LEG["hist"][reg]) + "</p>"
        '<div class="tab-rola"><table class="hist"><thead><tr>'
        "<th>ponto</th><th>máx</th><th>mín</th><th>mm/dia</th><th>dias com chuva</th>"
        "<th>&gt;5 mm</th><th>pôr do sol</th></tr></thead><tbody>" + "".join(linhas)
        + "</tbody></table></div>")

    return ('<div class="painel r-' + reg + '" id="p-' + SLUG_REG[reg] + '" role="tabpanel" data-reg="'
            + reg + '" aria-labelledby="t-' + reg + '"' + ("" if aberto else " hidden") + ">"
            + "".join(secoes) + "</div>")


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


def _gerado(txt):
    """'13/09/2026T05:15' vira ('13/09', '05:15')."""
    data, _, hora = txt.partition("T")
    return data[:5], hora


def monta(d):
    """Devolve (html, js) para o monitor validar o JS antes de publicar."""
    dias = _dias(d)
    dados = {
        "gerado": d["gerado"], "viagem": d["viagem"], "dias_grade": d["dias_grade"],
        "dias_viagem": d["dias_viagem"],
        "dias": [{"dia": x["dia"], "reg": x["reg"], "reg2": x["reg2"]} for x in dias],
        "pontos": [{"id": p["id"], "nome": p["nome"], "regiao": p["regiao"],
                    "hourly": _enxuga(p["hourly"], d["dias_grade"])}
                   for p in d["pontos"]],
        "wise": d.get("wise") or {"pares": {}},
    }
    js = JS.replace("DADOS", _j.dumps(dados, ensure_ascii=False, separators=(",", ":")), 1)

    regs_nav = "".join(
        '<button class="reg r-' + r + '" role="tab" id="t-' + r + '" data-reg="' + r
        + '" aria-controls="p-' + SLUG_REG[r] + '" aria-selected="' + ("true" if r == "ca" else "false")
        + '">' + _e(NOME_REG[r]) + "</button>" for r in ("ca", "oahu", "bi"))
    paineis = "".join(_painel(d, r, r == "ca") for r in ("ca", "oahu", "bi"))
    cartoes = "".join(_cartao_dia(x, d) for x in dias)
    g_data, g_hora = _gerado(d["gerado"])
    b_data, b_hora = _gerado(d["gerado_brt"])

    return (HTML
            .replace("{{CSS}}", CSS)
            .replace("{{FAVICON}}", FAVICON)
            .replace("{{FAIXA}}", _faixa(dias))
            .replace("{{CARTOES}}", cartoes)
            .replace("{{REGS}}", regs_nav)
            .replace("{{PAINEIS}}", paineis)
            .replace("{{GERADO}}", g_data + " às " + g_hora)
            .replace("{{GERADO_BRT}}", (b_data + " " if b_data != g_data else "") + b_hora)
            .replace("{{JS}}", js)), js


HTML = """<!DOCTYPE html>
<html lang="pt-BR" data-tema="">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>Honeymoon &middot; Rafael e Ana Cecília</title>
<link rel="icon" href="{{FAVICON}}">
<script>document.documentElement.classList.add("js");try{var t=localStorage.getItem("cd-tema");if(t)document.documentElement.setAttribute("data-tema",t)}catch(e){}</script>
<style>{{CSS}}</style>
</head>
<body>
<header class="topo"><div class="env topo-in">
  <div class="marca">
    <div class="linha1"><h1>Honeymoon</h1><span class="contagem" id="contagem"></span></div>
    <p class="meta">atualizado {{GERADO}} na costa<span class="longo">, {{GERADO_BRT}} em Brasília</span></p>
  </div>
  <button class="tema" id="bt-tema" aria-label="Alternar tema claro ou escuro" title="tema">&#9680;</button>
</div></header>
<div class="cambio-faixa"><div class="env"><div class="cambio" id="cambio" hidden></div></div></div>
<nav class="datas" aria-label="Dias da viagem"><div class="faixa-rola" id="faixa">{{FAIXA}}</div></nav>

<main class="env">
<div class="cartoes">{{CARTOES}}</div>

<section class="detalhes" id="detalhes">
  <h2>Mais detalhes, por região</h2>
  <div class="regs" role="tablist" aria-label="Regiões">{{REGS}}</div>
  {{PAINEIS}}
</section>

<footer>
  <p>Rafael e Ana Cecília, 20/12/2026 a 06/01/2027. Golden Coast em PST
  <span class="nw">(UTC-8)</span>; Oʻahu e Hawaiʻi em HST <span class="nw">(UTC-10)</span>.</p>
  <p>Missas conferidas nos sites das paróquias e nos diretórios das dioceses de Los Angeles,
  Monterey e Honolulu em 13/09/2026. Tempo: <a href="https://open-meteo.com/">Open-Meteo</a>.
  Avisos: <a href="https://api.weather.gov/">National Weather Service</a>. Estradas:
  <a href="https://roads.dot.ca.gov/">Caltrans</a>. El Niño:
  <a href="https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml">CPC</a>.
  Vulcão: <a href="https://www.usgs.gov/observatories/hvo">USGS HVO</a>.</p>
</footer>
</main>
<script>{{JS}}</script>
</body>
</html>
"""


CSS += r"""
p.aviso-missa{margin:8px 0 0;padding:8px 10px;border-left:3px solid var(--laranja, #E8730F);
  background:color-mix(in srgb, #E8730F 9%, transparent);font-weight:600}
"""
