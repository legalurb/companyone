#!/usr/bin/env python3
"""Company One: painel de visitas do site.

O site avisa o servidor a cada visita e a cada clique importante (endereço /e, sem cookies).
Cada aviso vira uma linha no registro de acesso do Caddy. Este programa lê essas linhas,
soma por dia e escreve UMA página com os números, num endereço secreto que só o dono conhece.

Daqui só saem contagens. O endereço IP é usado na hora da soma, para não contar a mesma
pessoa duas vezes no dia, e não é gravado em lugar nenhum.

Instalado por deploy/instalar.sh em /usr/local/sbin/companyone-painel (o cron roda a cada 10 minutos).
Para testar fora do servidor:
    python3 painel.py --log acesso.log --saida painel.html
"""
import argparse, datetime, hashlib, html, json, os, re, subprocess, sys, urllib.parse

SITE = '/opt/caddy-sites/companyone/site'
TOKEN = '/etc/companyone/painel.token'
MAX_DIAS = 180            # o registro do servidor guarda seis meses
MAX_CHAVES = 60           # teto de nomes diferentes por lista (proteção contra lixo no registro)

try:
    from zoneinfo import ZoneInfo
    FUSO = ZoneInfo('America/Sao_Paulo')
except Exception:                                   # sem a base de fusos: Brasília é UTC-3 o ano todo
    FUSO = datetime.timezone(datetime.timedelta(hours=-3))

ROBO = re.compile(r'bot|crawl|spider|slurp|headless|lighthouse|pagespeed|facebookexternalhit|preview|monitor|curl|wget|python|playwright|puppeteer', re.I)
PAGINAS = {'/': 'inicio', '/index.html': 'inicio', '/abrir/': 'abrir', '/abrir/index.html': 'abrir',
           '/nome/': 'nome', '/nome/index.html': 'nome', '/privacidade.html': 'privacidade'}
BOTOES = {'abertura', 'menu', 'faixa', 'flutuante', 'plano-studio', 'plano-suite', 'plano-hq', 'lancamento', 'duvidas',
          'contato', 'rodape', 'abertura-abrir', 'duvidas-abrir', 'nome-fim', 'teste-nome', 'teste-nome-pagina'}
MARCAS = {'instagram': 'Instagram', 'ig': 'Instagram', 'facebook': 'Facebook', 'fb': 'Facebook', 'whatsapp': 'WhatsApp', 'wa': 'WhatsApp',
          'zap': 'WhatsApp', 'google': 'Google', 'bing': 'Bing', 'duckduckgo': 'DuckDuckGo', 'yahoo': 'Yahoo', 'youtube': 'YouTube',
          'tiktok': 'TikTok', 'linkedin': 'LinkedIn', 'twitter': 'X (Twitter)', 'telegram': 'Telegram', 'github': 'GitHub', 'email': 'E-mail'}
DOMINIOS = {'wa.me': 'WhatsApp', 't.co': 'X (Twitter)', 'x.com': 'X (Twitter)', 'youtu.be': 'YouTube', 'lnkd.in': 'LinkedIn',
            't.me': 'Telegram', 'linktr.ee': 'Linktree', 'claude.ai': 'Claude'}
HOST = re.compile(r'^[a-z0-9][a-z0-9.-]{1,58}[a-z0-9]$')
ETIQUETA = re.compile(r'^[a-z0-9][a-z0-9_.-]{0,29}$')


def um(q, k):
    v = q.get(k)
    return v[0] if v else ''


def origem_de(q):
    """De onde veio a visita: campanha marcada no link (utm_source), site que trouxe ou acesso direto."""
    campanha = um(q, 'us').strip().lower()
    r = um(q, 'r').strip().lower()
    if campanha and ETIQUETA.match(campanha):
        return MARCAS.get(campanha) or 'Campanha: ' + campanha
    if not r: return 'Direto'
    if not HOST.match(r): return 'Outros sites'
    for dominio, nome in DOMINIOS.items():
        if r == dominio or r.endswith('.' + dominio): return nome
    for pedaco in r.split('.'):
        if pedaco in MARCAS and pedaco not in ('ig', 'wa', 'zap', 'email'): return MARCAS[pedaco]
    return re.sub(r'^(www|m|l|lm)\.', '', r)


def linhas_do_caddy():
    """Lê o registro de dentro do contêiner do Caddy: o arquivo atual e os já fechados (compactados ou não)."""
    nomes = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True).stdout.split()
    caddy = next((n for n in nomes if 'caddy' in n.lower()), None)
    if not caddy: raise SystemExit('contêiner do Caddy não encontrado')
    cmd = ('for f in /data/logs/companyone-acesso-*.log.gz; do [ -f "$f" ] && gunzip -c "$f"; done; '
           'for f in /data/logs/companyone-acesso-*.log; do [ -f "$f" ] && cat "$f"; done; '
           'cat /data/logs/companyone-acesso.log 2>/dev/null; true')
    p = subprocess.Popen(['docker', 'exec', caddy, 'sh', '-c', cmd], stdout=subprocess.PIPE)
    for raw in p.stdout: yield raw
    p.wait()


def linhas_de(arquivos):
    for a in arquivos:
        with open(a, 'rb') as f:
            for raw in f: yield raw


def soma(linhas, hoje):
    primeiro = hoje - datetime.timedelta(days=MAX_DIAS - 1)
    dia = {}                         # métrica -> {data: quantidade}
    dim = {}                         # lista -> {nome -> {data: quantidade}}
    gente = {}                       # data -> conjunto de pessoas (só na memória)
    lidas = 0

    def mais(metrica, d):
        m = dia.setdefault(metrica, {}); m[d] = m.get(d, 0) + 1

    def mais_dim(lista, nome, d):
        l = dim.setdefault(lista, {})
        if nome not in l and len(l) >= MAX_CHAVES: nome = 'Outros'
        m = l.setdefault(nome, {}); m[d] = m.get(d, 0) + 1

    for raw in linhas:
        if b'/e?' not in raw: continue
        try: reg = json.loads(raw)
        except Exception: continue
        req = reg.get('request') or {}
        uri = req.get('uri') or ''
        if not uri.startswith('/e?') or len(uri) > 600: continue
        ua = ((req.get('headers') or {}).get('User-Agent') or [''])[0]
        if not ua or ROBO.search(ua): continue
        try:
            q = urllib.parse.parse_qs(uri[3:], max_num_fields=12)
            d = datetime.datetime.fromtimestamp(float(reg.get('ts') or 0), FUSO).date()
        except Exception: continue
        if d < primeiro or d > hoje: continue
        t = um(q, 't')
        pag = PAGINAS.get(um(q, 'p'), 'outra')
        lidas += 1
        if t == 'pv':
            mais('pv', d); mais_dim('pagina', pag, d); mais_dim('origem', origem_de(q), d)
            mais_dim('aparelho', {'cel': 'cel', 'tab': 'tab', 'pc': 'pc'}.get(um(q, 'w'), 'pc'), d)
            ip = req.get('client_ip') or req.get('remote_ip') or ''
            gente.setdefault(d, set()).add(hashlib.blake2b((ip + '|' + ua).encode('utf-8', 'replace'), digest_size=8).digest())
        elif t == 'rolou':
            m = um(q, 'd')
            if m in ('25', '50', '75', '100'): mais_dim('rolou', pag + '|' + m, d)
        elif t == 'wa':
            o = um(q, 'o')
            mais('wa', d); mais_dim('botao', o if o in BOTOES else 'outro', d)
        elif t == 'video':
            a = um(q, 'a'); n = um(q, 'n')
            if a == 'inicio': mais('video', d)
            elif a == 'parte' and n in ('1', '2', '3', '4', '5', '6', '7', '8', '9'): mais_dim('parte', n, d)
        elif t == 'nome':
            s = um(q, 's')
            mais('nome', d); mais_dim('nome_s', {'free': 'livre', 'taken': 'ocupado'}.get(s, 'sem_resposta'), d)
        elif t == 'cnae':
            g = um(q, 'g')
            mais('cnae', d); mais_dim('cnae_g', 'gerado' if re.match(r'^\d{4}-\d/\d{2}$', g) else 'sem_texto', d)
        elif t == 'form':
            mais('form', d); mais_dim('form_f', 'tem' if um(q, 'f') == 'tem' else 'abrir', d)
        else:
            lidas -= 1

    datas = sorted(set(x for m in dia.values() for x in m) | set(x for l in dim.values() for m in l.values() for x in m))
    inicio = min(datas[0], hoje - datetime.timedelta(days=13)) if datas else hoje - datetime.timedelta(days=13)
    dias = [inicio + datetime.timedelta(days=i) for i in range((hoje - inicio).days + 1)]
    pos = {d: i for i, d in enumerate(dias)}
    esparso = lambda m: {str(pos[d]): n for d, n in sorted(m.items())}

    def pessoas(n, recuo=0):          # pessoas diferentes nos n dias que terminam "recuo" dias atrás
        fim = hoje - datetime.timedelta(days=recuo)
        juntas = set()
        for i in range(n if n else len(dias)):
            juntas |= gente.get(fim - datetime.timedelta(days=i), set())
        return len(juntas)

    return {
        'gerado': datetime.datetime.now(FUSO).strftime('%d/%m/%Y às %H:%M'),
        'hoje': hoje.isoformat(),
        'dias': [d.isoformat() for d in dias],
        'primeira': datas[0].isoformat() if datas else None,
        'eventos': lidas,
        'dia': {k: esparso(m) for k, m in dia.items()},
        'dim': {l: {nome: esparso(m) for nome, m in itens.items()} for l, itens in dim.items()},
        'pessoas': {str(n): [pessoas(n), pessoas(n, n) if n else 0] for n in (1, 7, 30, 0)},
    }


def pagina(dados):
    blob = json.dumps(dados, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return MODELO.replace('/*DADOS*/', blob).replace('<!--GERADO-->', html.escape(dados['gerado']))


MODELO = r'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="referrer" content="no-referrer">
<meta http-equiv="refresh" content="600">
<title>Painel do site — Company One</title>
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<style>
@font-face{font-family:"Archivo";src:url("/assets/fonts/archivo-800.woff2") format("woff2");font-weight:800;font-display:swap}
@font-face{font-family:"Inter";src:url("/assets/fonts/inter-400.woff2") format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"Inter";src:url("/assets/fonts/inter-600.woff2") format("woff2");font-weight:600;font-display:swap}
.viz-root{
  color-scheme:light;
  --plano:#F6F1E7;            /* fundo da página */
  --surface-1:#FFFCF5;        /* fundo dos quadros e dos gráficos */
  --text-primary:#13213A;
  --text-secondary:#4A4F5C;
  --text-muted:#6B7180;
  --linha:#E4DACA;            /* grades e divisórias */
  --series-1:#3A62A4;         /* visitas */
  --series-1-trilho:#DCE5F4;
  --series-2:#C0432F;         /* cliques no WhatsApp */
  --series-2-trilho:#F5DDD6;
  --contexto:#C9C2B3;         /* dias fora do período escolhido */
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:#F6F1E7}
.viz-root{min-height:100vh;background:var(--plano);color:var(--text-primary);font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}
h1,h2,h3,p,ul,ol,dl,dd,figure,table{margin:0}
ul,ol{padding:0;list-style:none}
button{font:inherit;color:inherit}
:focus-visible{outline:3px solid var(--series-1);outline-offset:2px}

.topo{background:#13213A;color:#F6F1E7}
.topo__in{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px 24px;padding-top:18px;padding-bottom:18px}
.topo__t{font-family:Archivo,sans-serif;font-weight:800;font-size:1.25rem;letter-spacing:-.015em}
.topo__s{color:#CBD3E0;font-size:.9rem}
.topo a{color:#F6F1E7;font-weight:600;text-underline-offset:3px}

.filtros{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding-top:22px}
.filtros__l{margin-right:6px;color:var(--text-secondary);font-size:.92rem}
.per{min-height:40px;padding:0 16px;border:1px solid var(--linha);border-radius:999px;background:var(--surface-1);font-weight:600;font-size:.92rem;cursor:pointer}
.per:hover{border-color:var(--text-muted)}
.per[aria-pressed="true"]{border-color:#13213A;background:#13213A;color:#F6F1E7}

.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-top:18px}
.tile{padding:18px 20px 16px;border:1px solid var(--linha);border-radius:14px;background:var(--surface-1)}
.tile__l{display:flex;align-items:center;gap:8px;color:var(--text-secondary);font-size:.9rem}
.chave{flex:none;width:10px;height:10px;border-radius:3px;background:var(--series-1)}
.chave--2{background:var(--series-2)}
.tile__v{margin-top:6px;font-weight:600;font-size:2.3rem;line-height:1.1;letter-spacing:-.02em}
.tile__d{margin-top:6px;color:var(--text-muted);font-size:.84rem}

.grade{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:14px}
.quadro{min-width:0;padding:20px 20px 18px;border:1px solid var(--linha);border-radius:14px;background:var(--surface-1)}
.quadro--largo{grid-column:1/-1}
.quadro__t{font-family:Archivo,sans-serif;font-weight:800;font-size:1.06rem;letter-spacing:-.012em}
.quadro__s{margin-top:2px;color:var(--text-muted);font-size:.86rem}
.vazio{margin-top:14px;color:var(--text-muted);font-size:.92rem}

.plot{position:relative;margin-top:14px}
.plot svg{display:block;width:100%;height:auto;overflow:visible}
.eixo{fill:var(--text-muted);font-size:11px;font-variant-numeric:tabular-nums}
.rotulo{fill:var(--text-primary);font-size:11px;font-weight:600}
.barra{cursor:default;outline:none}
.barra:hover .barra__f,.barra:focus-visible .barra__f{opacity:.72}
.barra:focus-visible .barra__alvo{stroke:var(--series-1);stroke-width:2}
.dica{position:absolute;z-index:5;pointer-events:none;padding:7px 10px;border-radius:8px;background:#13213A;color:#F6F1E7;font-size:.84rem;line-height:1.3;white-space:nowrap;transform:translate(-50%,-100%);box-shadow:0 8px 20px rgba(19,33,58,.25)}
.dica b{display:block;font-weight:600;font-size:.95rem}
.dica span{color:#CBD3E0}
details.tab{margin-top:10px;font-size:.88rem}
details.tab summary{display:inline-block;color:var(--text-secondary);font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:3px}
.tabela{width:100%;max-width:420px;margin-top:8px;border-collapse:collapse;font-variant-numeric:tabular-nums}
.tabela th,.tabela td{padding:5px 8px 5px 0;border-bottom:1px solid var(--linha);text-align:left;font-weight:400}
.tabela th{color:var(--text-muted);font-size:.8rem}
.tabela td:last-child,.tabela th:last-child{text-align:right}
.rolagem{max-height:260px;overflow:auto}

.lista{margin-top:12px}
.lin{display:grid;grid-template-columns:minmax(0,12.5rem) minmax(40px,1fr) auto;align-items:center;gap:12px;padding:8px 0;border-top:1px solid var(--linha)}
.lin:first-child{border-top:0}
.lin__n{font-size:.92rem;line-height:1.3;overflow-wrap:anywhere}
.lin__c{min-width:0}
.lin__b{height:10px;border-radius:0 4px 4px 0;background:var(--series-1)}
.lin__b--2{background:var(--series-2)}
.lin__t{height:10px;border-radius:5px;background:var(--series-1-trilho);overflow:hidden}
.lin__t>i{display:block;height:100%;border-radius:5px;background:var(--series-1)}
.lin__v{min-width:3.2rem;font-weight:600;font-size:.92rem;font-variant-numeric:tabular-nums;text-align:right}
.lin__v small{display:block;color:var(--text-muted);font-weight:400;font-size:.76rem}

.fatos{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:14px}
.fato__v{margin-top:4px;font-weight:600;font-size:1.7rem;line-height:1.15;letter-spacing:-.015em}
.fato__d{margin-top:4px;color:var(--text-muted);font-size:.86rem}

.rodape{margin-top:26px;padding-top:20px;padding-bottom:44px;border-top:1px solid var(--linha);color:var(--text-secondary);font-size:.9rem}
.rodape p+p{margin-top:8px}
.chavear{margin-top:14px;min-height:44px;padding:0 18px;border:1px solid #13213A;border-radius:999px;background:transparent;font-weight:600;cursor:pointer}
.chavear[aria-pressed="true"]{background:#13213A;color:#F6F1E7}

@media (max-width:860px){
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
  .grade,.fatos{grid-template-columns:minmax(0,1fr)}
}
@media (max-width:480px){
  .tile{padding:14px 14px 12px}
  .tile__v{font-size:1.8rem}
  .lin{grid-template-columns:minmax(0,1fr) auto;row-gap:5px}
  .lin__c,.lin__t{grid-column:1/-1;grid-row:2}
}
</style>
</head>
<body>
<div class="viz-root">
<header class="topo">
  <div class="wrap topo__in">
    <div>
      <h1 class="topo__t">Company One · Painel do site</h1>
      <p class="topo__s">Atualizado em <!--GERADO-->. Atualiza sozinho a cada 10 minutos.</p>
    </div>
    <a href="/">Abrir o site</a>
  </div>
</header>
<main class="wrap">
  <div class="filtros" role="group" aria-label="Período">
    <span class="filtros__l">Período</span>
    <button class="per" type="button" data-n="1">Hoje</button>
    <button class="per" type="button" data-n="7">7 dias</button>
    <button class="per" type="button" data-n="30">30 dias</button>
    <button class="per" type="button" data-n="0">Tudo</button>
  </div>

  <section class="kpis" aria-label="Resumo">
    <div class="tile"><p class="tile__l"><span class="chave"></span>Visitas</p><p class="tile__v" id="k-pv">0</p><p class="tile__d" id="k-pv-d"></p></div>
    <div class="tile"><p class="tile__l">Pessoas diferentes (aprox.)</p><p class="tile__v" id="k-gente">0</p><p class="tile__d" id="k-gente-d"></p></div>
    <div class="tile"><p class="tile__l"><span class="chave chave--2"></span>Cliques no WhatsApp</p><p class="tile__v" id="k-wa">0</p><p class="tile__d" id="k-wa-d"></p></div>
    <div class="tile"><p class="tile__l">Visitas que viraram clique</p><p class="tile__v" id="k-taxa">0%</p><p class="tile__d" id="k-taxa-d"></p></div>
  </section>

  <div class="grade">
    <figure class="quadro">
      <h2 class="quadro__t">Visitas por dia</h2>
      <p class="quadro__s" id="g-pv-s"></p>
      <div class="plot" id="g-pv"></div>
      <details class="tab"><summary>Ver os números</summary><div class="rolagem"><table class="tabela" id="t-pv"></table></div></details>
    </figure>
    <figure class="quadro">
      <h2 class="quadro__t">Cliques no WhatsApp por dia</h2>
      <p class="quadro__s" id="g-wa-s"></p>
      <div class="plot" id="g-wa"></div>
      <details class="tab"><summary>Ver os números</summary><div class="rolagem"><table class="tabela" id="t-wa"></table></div></details>
    </figure>

    <section class="quadro">
      <h2 class="quadro__t">De onde vieram as visitas</h2>
      <p class="quadro__s">"Direto" é quem tocou num link recebido pelo WhatsApp ou digitou o endereço.</p>
      <ul class="lista" id="l-origem"></ul>
    </section>
    <section class="quadro">
      <h2 class="quadro__t">Qual botão de WhatsApp foi clicado</h2>
      <p class="quadro__s">Mostra em que ponto da página a pessoa decide chamar.</p>
      <ul class="lista" id="l-botao"></ul>
    </section>

    <section class="quadro">
      <h2 class="quadro__t">Páginas abertas</h2>
      <p class="quadro__s">Visitas em cada página do site.</p>
      <ul class="lista" id="l-pagina"></ul>
    </section>
    <section class="quadro">
      <h2 class="quadro__t">Aparelho</h2>
      <p class="quadro__s">Onde o site foi aberto.</p>
      <ul class="lista" id="l-aparelho"></ul>
    </section>

    <section class="quadro">
      <h2 class="quadro__t">Até onde rolaram a página inicial</h2>
      <p class="quadro__s" id="l-rolou-s"></p>
      <ul class="lista" id="l-rolou"></ul>
    </section>
    <section class="quadro">
      <h2 class="quadro__t">Vídeo do escritório: até onde assistiram</h2>
      <p class="quadro__s" id="l-video-s"></p>
      <ul class="lista" id="l-video"></ul>
    </section>
  </div>

  <section class="fatos" aria-label="Ferramentas e formulário">
    <div class="quadro"><h2 class="quadro__t">Teste de nome</h2><p class="fato__v" id="f-nome">0</p><p class="fato__d" id="f-nome-d"></p></div>
    <div class="quadro"><h2 class="quadro__t">Texto para o contador</h2><p class="fato__v" id="f-cnae">0</p><p class="fato__d" id="f-cnae-d"></p></div>
    <div class="quadro"><h2 class="quadro__t">Formulário enviado</h2><p class="fato__v" id="f-form">0</p><p class="fato__d" id="f-form-d"></p></div>
  </section>

  <footer class="rodape">
    <p><b>Como ler.</b> "Visita" é cada vez que uma página do site é aberta. "Pessoas diferentes" é uma aproximação: o mesmo aparelho na mesma rede conta uma vez por dia. Clique no WhatsApp é a pessoa abrindo a conversa; se ela mandou a mensagem, quem sabe é o WhatsApp.</p>
    <p>A contagem não usa cookies e não guarda nome, telefone nem o que a pessoa digita. Robôs e quem pede ao navegador para não ser rastreado ficam de fora.</p>
    <p id="primeira"></p>
    <button class="chavear" type="button" id="eu" aria-pressed="false">Não contar as visitas deste aparelho</button>
    <p id="eu-d" role="status"></p>
  </footer>
</main>
</div>
<script type="application/json" id="dados">/*DADOS*/</script>
<script>
(function () {
  'use strict';
  var D = JSON.parse(document.getElementById('dados').textContent);
  var N = D.dias.length;
  var $ = function (id) { return document.getElementById(id); };
  var num = function (n) { return Number(n).toLocaleString('pt-BR'); };
  var NS = 'http://www.w3.org/2000/svg';
  var SEMANA = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];
  function partes(iso) { var p = iso.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function curta(iso) { var p = iso.split('-'); return p[2] + '/' + p[1]; }
  function longa(iso) { return SEMANA[partes(iso).getDay()] + ', ' + curta(iso); }

  var NOMES = {
    pagina: { inicio: 'Página inicial', abrir: 'Vou abrir empresa', nome: 'Teste de nome', privacidade: 'Privacidade', outra: 'Endereço que não existe' },
    aparelho: { cel: 'Celular', tab: 'Tablet', pc: 'Computador' },
    botao: { abertura: 'Abertura da página inicial', menu: 'Barra do topo', faixa: 'Faixa de lançamento', flutuante: 'Botão flutuante',
      'plano-studio': 'Plano Studio', 'plano-suite': 'Plano Suíte', 'plano-hq': 'Plano HQ', lancamento: 'Destaque do lançamento',
      duvidas: 'Dúvidas', contato: 'Contato, no fim da página', rodape: 'Rodapé', 'abertura-abrir': 'Abertura de "Vou abrir empresa"',
      'duvidas-abrir': 'Dúvidas de "Vou abrir empresa"', 'nome-fim': 'Fim da página do teste de nome',
      'teste-nome': 'Depois de testar um nome', 'teste-nome-pagina': 'Depois de testar um nome (página do teste)', outro: 'Outro botão' }
  };
  var PARTES = ['O escritório', 'A equipe', 'O caixa', 'Os turnos', 'O relatório', 'As decisões', 'No celular', 'A recepção', 'A montagem'];

  // soma de uma série (guardada só nos dias em que houve algo) entre dois dias, inclusive
  function soma(m, a, b) { var s = 0; if (!m) return 0; for (var k in m) { var i = +k; if (i >= a && i <= b) s += m[k]; } return s; }
  function serie(m, a, b) { var v = []; for (var i = a; i <= b; i++) v.push((m && m[i]) || 0); return v; }
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt !== undefined) e.textContent = txt; return e; }
  function svg(tag, attrs) { var e = document.createElementNS(NS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); return e; }

  var periodo = 7;
  try { var salvo = localStorage.getItem('co-painel-periodo'); if (salvo !== null && /^(0|1|7|30)$/.test(salvo)) periodo = +salvo; } catch (e) {}

  function faixa() {
    var n = periodo ? Math.min(periodo, N) : N;
    return { a: N - n, b: N - 1, n: n, pa: N - 2 * n, pb: N - n - 1, temAnterior: periodo > 0 && N - 2 * n >= 0 };
  }
  function nomePeriodo() {
    return periodo === 1 ? 'hoje' : periodo === 0 ? 'desde o começo' : 'nos últimos ' + periodo + ' dias';
  }
  function variacao(agora, antes, f) {
    if (!f.temAnterior) return periodo === 0 ? 'Desde a primeira visita contada.' : '';
    var ontem = periodo === 1, antesTxt = ontem ? 'ontem' : periodo + ' dias anteriores';
    if (ontem) return 'Ontem, no dia inteiro: ' + num(antes) + '.';
    if (!antes) return agora ? 'Nada contado nos ' + antesTxt + ' para comparar.' : '';
    var p = Math.round((agora - antes) / antes * 100);
    if (p === 0) return 'Igual ' + (ontem ? 'a ontem' : 'aos ' + antesTxt) + '.';
    return (p > 0 ? '▲ ' : '▼ ') + Math.abs(p) + '% ' + (p > 0 ? 'acima ' : 'abaixo ') + (ontem ? 'de ontem' : 'dos ' + antesTxt) + ' (' + num(antes) + ').';
  }

  /* ---------- colunas por dia: o período escolhido na cor, os dias em volta em cinza ---------- */
  var dica = null;
  function mostraDica(plot, x, y, valor, quando) {
    if (!dica) { dica = el('div', 'dica'); dica.appendChild(el('b')); dica.appendChild(el('span')); }
    dica.firstChild.textContent = valor; dica.lastChild.textContent = quando;
    plot.appendChild(dica);
    var w = plot.clientWidth, meio = Math.min(Math.max(x, 70), w - 70);
    dica.style.left = meio + 'px'; dica.style.top = Math.max(y - 8, 30) + 'px';
  }
  function escondeDica() { if (dica && dica.parentNode) dica.parentNode.removeChild(dica); }

  function passoBom(max) {            // degraus redondos para o eixo: 1, 2, 5, 10, 20, 50...
    var alvo = max / 3, base = Math.pow(10, Math.floor(Math.log(Math.max(alvo, 1)) / Math.LN10)), r = alvo / base;
    return Math.max(1, (r <= 1 ? 1 : r <= 2 ? 2 : r <= 5 ? 5 : 10) * base);
  }

  function colunas(idPlot, idTab, m, cor, unidade, f) {
    var plot = $(idPlot); plot.textContent = '';
    var a = Math.max(0, Math.min(f.a, N - 14)), b = N - 1, v = serie(m, a, b), n = v.length;
    var W = Math.max(plot.clientWidth, 280), H = 190, esq = 34, dir = 8, topo = 18, base = H - 24;
    var max = Math.max.apply(null, v), passo = passoBom(max || 1), teto = Math.max(passo, Math.ceil(max / passo) * passo);
    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': unidade.plural + ' por dia, de ' + curta(D.dias[a]) + ' a ' + curta(D.dias[b]) });
    for (var g = 0; g <= teto; g += passo) {
      var gy = base - (base - topo) * g / teto;
      s.appendChild(svg('line', { x1: esq, x2: W - dir, y1: gy, y2: gy, stroke: 'var(--linha)', 'stroke-width': 1 }));
      var tk = svg('text', { x: esq - 8, y: gy + 4, 'text-anchor': 'end', 'class': 'eixo' }); tk.textContent = num(g); s.appendChild(tk);
    }
    var vao = (W - esq - dir) / n, larg = Math.max(2, Math.min(24, vao - 2));
    var pico = v.indexOf(max), cabe = Math.ceil(44 / vao), cada = [1, 2, 3, 5, 7, 10, 14, 30, 60].filter(function (p) { return p >= cabe; })[0] || 90;
    v.forEach(function (q, i) {
      var idx = a + i, dentro = idx >= f.a, x = esq + vao * i + (vao - larg) / 2, h = teto ? (base - topo) * q / teto : 0, y = base - h, r = Math.min(4, larg / 2, h);
      var grupo = svg('g', { 'class': 'barra' });
      if (n <= 31) { grupo.setAttribute('tabindex', '0'); grupo.setAttribute('role', 'img'); }
      grupo.setAttribute('aria-label', longa(D.dias[idx]) + ': ' + num(q) + ' ' + (q === 1 ? unidade.singular : unidade.plural));
      grupo.appendChild(svg('rect', { 'class': 'barra__alvo', x: esq + vao * i, y: topo - 6, width: vao, height: base - topo + 6, fill: 'transparent' }));
      if (q > 0) grupo.appendChild(svg('path', { 'class': 'barra__f', fill: dentro ? cor : 'var(--contexto)',
        d: 'M' + x + ',' + base + 'V' + (y + r) + 'Q' + x + ',' + y + ' ' + (x + r) + ',' + y + 'H' + (x + larg - r) + 'Q' + (x + larg) + ',' + y + ' ' + (x + larg) + ',' + (y + r) + 'V' + base + 'Z' }));
      var entra = function () { mostraDica(plot, (x + larg / 2) / W * plot.clientWidth, y / H * plot.clientHeight, num(q) + ' ' + (q === 1 ? unidade.singular : unidade.plural), longa(D.dias[idx])); };
      grupo.addEventListener('pointerenter', entra); grupo.addEventListener('focus', entra);
      grupo.addEventListener('pointerleave', escondeDica); grupo.addEventListener('blur', escondeDica);
      s.appendChild(grupo);
      // rótulos escolhidos: o pico e o dia de hoje; o resto fica no eixo, na dica e na tabela
      if (q > 0 && (i === pico || i === n - 1) && vao >= 9) { var rt = svg('text', { x: x + larg / 2, y: y - 5, 'text-anchor': 'middle', 'class': 'rotulo' }); rt.textContent = num(q); s.appendChild(rt); }
      if (i === n - 1 || ((n - 1 - i) % cada === 0 && (n - 1 - i) * vao >= 44)) {
        var dt = svg('text', { x: Math.min(x + larg / 2, W - dir - 14), y: H - 6, 'text-anchor': 'middle', 'class': 'eixo' }); dt.textContent = i === n - 1 ? 'hoje' : curta(D.dias[idx]); s.appendChild(dt);
      }
    });
    s.appendChild(svg('line', { x1: esq, x2: W - dir, y1: base, y2: base, stroke: 'var(--text-muted)', 'stroke-width': 1 }));
    plot.appendChild(s);
    // a mesma coisa em tabela
    var t = $(idTab); t.textContent = '';
    var cab = el('tr'); cab.appendChild(el('th', '', 'Dia')); cab.appendChild(el('th', '', unidade.titulo)); t.appendChild(cab);
    for (var i = n - 1; i >= 0; i--) { var tr = el('tr'); tr.appendChild(el('td', '', longa(D.dias[a + i]))); tr.appendChild(el('td', '', num(v[i]))); t.appendChild(tr); }
  }

  /* ---------- listas: um nome, uma barra e um número por linha ---------- */
  function ranking(id, lista, nomes, f, serie2, ordem) {
    var alvo = $(id); alvo.textContent = '';
    var itens = [], grupo = D.dim[lista] || {};
    Object.keys(grupo).forEach(function (k) { var q = soma(grupo[k], f.a, f.b); if (q > 0) itens.push({ k: k, nome: (nomes && nomes[k]) || k, q: q }); });
    if (ordem) itens.sort(function (x, y) { return ordem.indexOf(x.k) - ordem.indexOf(y.k); }); else itens.sort(function (x, y) { return y.q - x.q; });
    if (!itens.length) { alvo.appendChild(el('li', 'vazio', 'Nada contado ' + nomePeriodo() + '.')); return; }
    if (itens.length > 9) { var resto = itens.splice(8); itens.push({ nome: 'Outros (' + resto.length + ')', q: resto.reduce(function (s, x) { return s + x.q; }, 0) }); }
    var max = Math.max.apply(null, itens.map(function (x) { return x.q; })), total = itens.reduce(function (s, x) { return s + x.q; }, 0);
    itens.forEach(function (x) {
      var li = el('li', 'lin'); li.appendChild(el('span', 'lin__n', x.nome));
      var caixa = el('span', 'lin__c'); var barra = el('span', 'lin__b' + (serie2 ? ' lin__b--2' : '')); barra.style.display = 'block'; barra.style.width = Math.max(2, x.q / max * 100) + '%'; caixa.appendChild(barra); li.appendChild(caixa);
      var v = el('span', 'lin__v', num(x.q)); v.appendChild(el('small', '', Math.round(x.q / total * 100) + '%')); li.appendChild(v);
      alvo.appendChild(li);
    });
  }
  function medidores(id, linhas, base) {
    var alvo = $(id); alvo.textContent = '';
    if (!base) { alvo.appendChild(el('li', 'vazio', 'Nada contado ' + nomePeriodo() + '.')); return; }
    linhas.forEach(function (x) {
      var p = Math.min(100, Math.round(x.q / base * 100));
      var li = el('li', 'lin'); li.appendChild(el('span', 'lin__n', x.nome));
      var trilho = el('span', 'lin__t'); var cheio = el('i'); cheio.style.width = p + '%'; trilho.appendChild(cheio); li.appendChild(trilho);
      trilho.setAttribute('role', 'img'); trilho.setAttribute('aria-label', x.nome + ': ' + p + '%');
      var v = el('span', 'lin__v', p + '%'); v.appendChild(el('small', '', num(Math.min(x.q, base)) + ' de ' + num(base))); li.appendChild(v);
      alvo.appendChild(li);
    });
  }

  function desenha() {
    var f = faixa(), dia = D.dia, dim = D.dim;
    [].forEach.call(document.querySelectorAll('.per'), function (b) { b.setAttribute('aria-pressed', String(+b.getAttribute('data-n') === periodo)); });
    var pv = soma(dia.pv, f.a, f.b), wa = soma(dia.wa, f.a, f.b);
    var pvAntes = f.temAnterior ? soma(dia.pv, f.pa, f.pb) : 0, waAntes = f.temAnterior ? soma(dia.wa, f.pa, f.pb) : 0;
    var gente = D.pessoas[String(periodo)] || [0, 0];
    $('k-pv').textContent = num(pv); $('k-pv-d').textContent = variacao(pv, pvAntes, f);
    $('k-gente').textContent = num(gente[0]); $('k-gente-d').textContent = variacao(gente[0], gente[1], f);
    $('k-wa').textContent = num(wa); $('k-wa-d').textContent = variacao(wa, waAntes, f);
    $('k-taxa').textContent = pv ? (wa / pv * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + '%' : '0%';
    $('k-taxa-d').textContent = pv ? (wa ? 'Um clique a cada ' + num(Math.max(1, Math.round(pv / wa))) + ' visitas.' : 'Ainda sem cliques ' + nomePeriodo() + '.') : '';

    var legenda = periodo === 0 ? 'Todos os dias contados.' : periodo >= 14 ? 'Últimos ' + Math.min(periodo, N) + ' dias.' : 'Em cor, ' + (periodo === 1 ? 'hoje' : 'os últimos ' + periodo + ' dias') + '. Em cinza, os dias anteriores.';
    $('g-pv-s').textContent = legenda; $('g-wa-s').textContent = legenda;
    colunas('g-pv', 't-pv', dia.pv, 'var(--series-1)', { singular: 'visita', plural: 'visitas', titulo: 'Visitas' }, f);
    colunas('g-wa', 't-wa', dia.wa, 'var(--series-2)', { singular: 'clique', plural: 'cliques', titulo: 'Cliques' }, f);

    ranking('l-origem', 'origem', null, f, false);
    ranking('l-botao', 'botao', NOMES.botao, f, true);
    ranking('l-pagina', 'pagina', NOMES.pagina, f, false);
    ranking('l-aparelho', 'aparelho', NOMES.aparelho, f, false, ['cel', 'pc', 'tab']);

    var inicio = soma((dim.pagina || {}).inicio, f.a, f.b), rol = dim.rolou || {};
    $('l-rolou-s').textContent = inicio ? 'De ' + num(inicio) + ' visitas à página inicial, quantas chegaram a cada ponto.' : '';
    medidores('l-rolou', [['25', 'Um quarto (o vídeo)'], ['50', 'Metade'], ['75', 'Três quartos'], ['100', 'Até o fim (contato)']].map(function (x) {
      return { nome: x[1], q: soma(rol['inicio|' + x[0]], f.a, f.b) }; }), inicio);

    var comecos = soma(dia.video, f.a, f.b), par = dim.parte || {};
    $('l-video-s').textContent = comecos ? num(comecos) + (comecos === 1 ? ' pessoa começou' : ' pessoas começaram') + ' o vídeo' + (inicio ? ' (' + Math.round(comecos / inicio * 100) + '% das visitas à página inicial)' : '') + '.' : '';
    medidores('l-video', PARTES.map(function (nome, i) { return { nome: (i + 1) + '. ' + nome, q: soma(par[String(i + 1)], f.a, f.b) }; }), comecos);

    var nomeT = soma(dia.nome, f.a, f.b), ns = dim.nome_s || {};
    $('f-nome').textContent = num(nomeT);
    $('f-nome-d').textContent = nomeT ? num(soma(ns.livre, f.a, f.b)) + ' com domínio livre, ' + num(soma(ns.ocupado, f.a, f.b)) + ' já com dono.' : 'Nenhum nome testado ' + nomePeriodo() + '.';
    var cnae = soma(dia.cnae, f.a, f.b), cg = dim.cnae_g || {};
    $('f-cnae').textContent = num(cnae);
    $('f-cnae-d').textContent = cnae ? num(soma(cg.gerado, f.a, f.b)) + ' com texto gerado; o resto era atividade fora da lista.' : 'Nenhum texto gerado ' + nomePeriodo() + '.';
    var form = soma(dia.form, f.a, f.b), ff = dim.form_f || {};
    $('f-form').textContent = num(form);
    $('f-form-d').textContent = form ? num(soma(ff.tem, f.a, f.b)) + ' de quem já tem empresa, ' + num(soma(ff.abrir, f.a, f.b)) + ' de quem vai abrir.' : 'Nenhum envio ' + nomePeriodo() + '.';
  }

  [].forEach.call(document.querySelectorAll('.per'), function (b) {
    b.addEventListener('click', function () { periodo = +b.getAttribute('data-n'); try { localStorage.setItem('co-painel-periodo', String(periodo)); } catch (e) {} desenha(); });
  });
  var espera = null;
  window.addEventListener('resize', function () { clearTimeout(espera); espera = setTimeout(desenha, 150); });
  $('primeira').textContent = D.primeira ? 'Primeira visita contada em ' + curta(D.primeira) + '/' + D.primeira.slice(0, 4) + '.' : 'Ainda não há visitas contadas. Os números aparecem em até 10 minutos depois da primeira visita.';

  // o dono pode tirar as próprias visitas da conta, aparelho por aparelho
  var eu = $('eu'), euD = $('eu-d'), fora = false;
  try { fora = localStorage.getItem('co-sem-contagem') === '1'; } catch (e) { eu.hidden = true; }
  function pintaEu() {
    eu.setAttribute('aria-pressed', String(fora));
    eu.textContent = fora ? 'Voltar a contar as visitas deste aparelho' : 'Não contar as visitas deste aparelho';
    euD.textContent = fora ? 'As visitas feitas neste aparelho, neste navegador, não entram mais na conta.' : '';
  }
  eu.addEventListener('click', function () {
    fora = !fora;
    try { if (fora) localStorage.setItem('co-sem-contagem', '1'); else localStorage.removeItem('co-sem-contagem'); } catch (e) {}
    pintaEu();
  });
  pintaEu();
  desenha();
})();
</script>
</body>
</html>
'''


def main():
    ap = argparse.ArgumentParser(description='Gera o painel de visitas do site da Company One.')
    ap.add_argument('--log', action='append', help='arquivo de registro do Caddy (pode repetir); sem isso, lê do contêiner')
    ap.add_argument('--saida', help='onde escrever a página; sem isso, usa o endereço secreto dentro do site')
    ap.add_argument('--hoje', help='AAAA-MM-DD, para testes')
    a = ap.parse_args()
    hoje = datetime.date.fromisoformat(a.hoje) if a.hoje else datetime.datetime.now(FUSO).date()
    saida = a.saida
    if not saida:
        try: token = open(TOKEN, encoding='ascii').read().strip()
        except OSError: raise SystemExit('falta o arquivo ' + TOKEN + ' (rode deploy/instalar.sh)')
        if not re.match(r'^[a-f0-9]{32}$', token): raise SystemExit('o conteúdo de ' + TOKEN + ' não é um endereço válido')
        saida = os.path.join(SITE, 'p-' + token, 'index.html')
    dados = soma(linhas_de(a.log) if a.log else linhas_do_caddy(), hoje)
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    tmp = saida + '.novo'
    with open(tmp, 'w', encoding='utf-8') as f: f.write(pagina(dados))
    os.chmod(tmp, 0o644)
    os.replace(tmp, saida)
    print(datetime.datetime.now(FUSO).strftime('%F %T'), 'painel atualizado:', dados['eventos'], 'eventos em', len(dados['dias']), 'dias')


if __name__ == '__main__':
    main()
