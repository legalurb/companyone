"""Conferência completa do site montado (dist/site), como se estivesse em https://companyone.com.br.
Abre as páginas num navegador de verdade, clica, rola, preenche e confere o que saiu.
Uso: python3 test_all.py            (testa a pasta local, servida no endereço do site)
"""
import os, re, sys, json, mimetypes, urllib.parse
from html.parser import HTMLParser
from playwright.sync_api import sync_playwright

RAIZ = '/tmp/site/dist/site'
SITE = 'https://companyone.com.br'
WA = '5527999836371'
falhas = []; avisos = []
def ok(cond, msg):
    print(('  ok   ' if cond else '  FALHA ') + msg)
    if not cond: falhas.append(msg)

# ---------------------------------------------------------------- 1) links e âncoras (sem navegador)
class Coleta(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs = []; self.ids = set()
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get('id'): self.ids.add(d['id'])
        for k in ('href', 'src', 'poster'):
            if d.get(k): self.refs.append((tag, k, d[k]))
paginas = {}
for d, _, fs in os.walk(RAIZ):
    for f in fs:
        if f.endswith('.html'):
            p = os.path.join(d, f); c = Coleta(); c.feed(open(p, encoding='utf-8').read())
            paginas[os.path.relpath(p, RAIZ)] = c
def arquivo_de(url_path):
    p = os.path.normpath(os.path.join(RAIZ, url_path.lstrip('/')))
    if os.path.isdir(p): p = os.path.join(p, 'index.html')
    return p
print('1) links internos e âncoras')
externos = set(); quebrados = []
for nome, c in paginas.items():
    base = '/' + (os.path.dirname(nome) + '/' if os.path.dirname(nome) else '')
    for tag, k, v in c.refs:
        if v.startswith(('http://', 'https://', 'mailto:', 'tel:', 'data:')):
            externos.add(v.split('?')[0]); continue
        alvo, _, ancora = v.partition('#')
        alvo = alvo.split('?')[0]
        caminho = urllib.parse.urljoin(base, alvo) if alvo else '/' + nome
        arq = arquivo_de(caminho)
        if not os.path.isfile(arq): quebrados.append((nome, v, 'arquivo não existe')); continue
        if ancora and arq.endswith('.html'):
            ids = paginas[os.path.relpath(arq, RAIZ)].ids
            if ancora not in ids: quebrados.append((nome, v, 'âncora não existe'))
ok(not quebrados, f'nenhum link interno quebrado em {len(paginas)} páginas' + (': ' + json.dumps(quebrados[:8], ensure_ascii=False) if quebrados else ''))
print('     externos:', sorted(externos))
tudo = ''.join(open(os.path.join(RAIZ, n), encoding='utf-8').read() for n in paginas)
ok('%%' not in tudo, 'nenhum marcador %% sobrando')
ok(not re.search(r'50 primeiras|uma das 50|fundadora', tudo), 'nenhuma menção às 50 vagas')
ok(tudo.count('wa.me/' + WA) > 20 and not re.search(r'wa\.me/(?!' + WA + r')\d', tudo), 'todo link de WhatsApp aponta para o número configurado')

# ---------------------------------------------------------------- navegador: o site local responde no endereço de verdade
eventos = []
def atende(route):
    u = urllib.parse.urlsplit(route.request.url)
    if u.path == '/e':
        eventos.append(dict(urllib.parse.parse_qsl(u.query))); route.fulfill(status=204, body=''); return
    arq = arquivo_de(u.path)
    if not os.path.isfile(arq):
        route.fulfill(status=404, body=open(RAIZ + '/404.html', 'rb').read(), content_type='text/html; charset=utf-8'); return
    tipo = mimetypes.guess_type(arq)[0] or 'application/octet-stream'
    if tipo.startswith('text/') or tipo.endswith(('javascript', 'json')): tipo += '; charset=utf-8'
    dados = open(arq, 'rb').read(); h = {'Accept-Ranges': 'bytes'}
    rng = route.request.headers.get('range')
    if rng:
        m = re.match(r'bytes=(\d*)-(\d*)', rng); a = int(m.group(1) or 0); b = int(m.group(2)) if m.group(2) else len(dados) - 1
        b = min(b, len(dados) - 1); h['Content-Range'] = f'bytes {a}-{b}/{len(dados)}'
        route.fulfill(status=206, body=dados[a:b + 1], content_type=tipo, headers=h); return
    route.fulfill(status=200, body=dados, content_type=tipo, headers=h)
def rdap(route):
    u = route.request.url
    if 'padariaaurora' in u: route.fulfill(status=404, body='', headers={'access-control-allow-origin': '*'})
    else: route.fulfill(status=200, body='{}', headers={'access-control-allow-origin': '*', 'content-type': 'application/rdap+json'})

def nova(b, W, H, cel=False, **kw):
    ctx = b.new_context(viewport={'width': W, 'height': H}, is_mobile=cel, has_touch=cel, device_scale_factor=2 if cel else 1, **kw)
    ctx.route(SITE + '/**', atende); ctx.route('https://rdap.registro.br/**', rdap)
    ctx.route(re.compile(r'^https://(wa\.me|www\.instagram\.com|api\.whatsapp\.com)/'), lambda r: r.fulfill(status=200, body='<title>fora</title>', content_type='text/html'))
    pg = ctx.new_page(); pg.erros = []
    # ficam de fora dois avisos esperados: a consulta do Registro.br responde 404 quando o domínio está livre,
    # e a página que não existe responde 404 de propósito
    def console(m):
        if m.type not in ('error', 'warning'): return
        onde = (m.location or {}).get('url', '')
        if 'rdap.registro.br' in onde or 'nao-existe' in onde: return
        pg.erros.append(m.type + ': ' + m.text + ' [' + onde + ']')
    pg.on('console', console)
    pg.on('pageerror', lambda e: pg.erros.append('pageerror: ' + str(e)))
    return ctx, pg
def texto_wa(href):
    return urllib.parse.parse_qs(urllib.parse.urlsplit(href).query).get('text', [''])[0]
def espera_evento(pg, cond, ms=2500):
    for _ in range(ms // 100):
        if any(cond(e) for e in eventos): return True
        pg.wait_for_timeout(100)
    return False

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox', '--disable-gpu', '--autoplay-policy=no-user-gesture-required'])

    # ------------------------------------------------------------ 2) botões de WhatsApp em todas as páginas
    print('2) botões de WhatsApp')
    ctx, pg = nova(b, 1440, 900)
    for url, minimo in [('/', 11), ('/abrir/', 10), ('/nome/', 4), ('/privacidade.html', 0), ('/pagina-que-nao-existe', 0)]:
        eventos.clear()
        r = pg.goto(SITE + url, wait_until='load'); pg.wait_for_timeout(300)
        links = pg.eval_on_selector_all('.js-wa', 'els=>els.map(a=>({h:a.href,o:a.dataset.origem||"",t:a.target,rel:a.rel,vis:a.offsetParent!==null||getComputedStyle(a).position==="fixed"}))')
        ruins = [l for l in links if not l['h'].startswith(f'https://wa.me/{WA}?text=') or len(texto_wa(l['h'])) < 20 or not l['o'] or l['t'] != '_blank' or 'noopener' not in l['rel']]
        ok(len(links) >= minimo and not ruins, f'{url}: {len(links)} botões, todos com número, mensagem e origem' + (' ' + json.dumps(ruins[:3], ensure_ascii=False) if ruins else ''))
        ok(r.status == (404 if 'nao-existe' in url else 200), f'{url}: resposta {r.status}')
        ok(espera_evento(pg, lambda e: e.get('t') == 'pv' and e.get('p') == url), f'{url}: visita contada (pv)')
        ok(not pg.erros, f'{url}: sem erros no console' + (' ' + str(pg.erros[:3]) if pg.erros else '')); pg.erros.clear()
    # mensagens por origem, na página inicial
    pg.goto(SITE + '/', wait_until='load'); pg.wait_for_timeout(300)
    msgs = pg.eval_on_selector_all('.js-wa', 'els=>els.map(a=>[a.dataset.origem,decodeURIComponent(a.href.split("text=")[1])])')
    for o, m in msgs: print(f'     {o:16} {m}')
    ok(len({o for o, _ in msgs}) == len(msgs), 'cada botão da página inicial tem uma origem diferente (dá para medir qual converte)')
    # clique conta
    eventos.clear()
    with ctx.expect_page() as nv: pg.click('.hero .js-wa')
    nv.value.close()
    ok(espera_evento(pg, lambda e: e.get('t') == 'wa' and e.get('o') == 'abertura'), 'clique no WhatsApp da abertura contado (wa, origem abertura)')
    # rolagem conta
    eventos.clear()
    pg.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)'); pg.wait_for_timeout(900)
    ok(espera_evento(pg, lambda e: e.get('t') == 'rolou' and e.get('d') == '100'), 'rolagem até o fim contada (rolou 100)')
    ok(all('@' not in json.dumps(e) for e in eventos), 'nenhum evento leva dado pessoal')

    # ------------------------------------------------------------ 3) botão flutuante
    print('3) botão flutuante do WhatsApp')
    pg.goto(SITE + '/', wait_until='load'); pg.wait_for_timeout(400)
    vis = lambda: pg.evaluate("(()=>{const e=document.querySelector('.wa-float');const s=getComputedStyle(e);return s.visibility==='visible'&&+s.opacity>0.9})()")
    ok(not vis(), 'escondido na primeira tela')
    pg.evaluate("document.querySelector('#equipe').scrollIntoView()"); pg.wait_for_timeout(1800)
    ok(vis(), 'aparece no meio da página')
    pg.evaluate("document.querySelector('#contato').scrollIntoView()"); pg.wait_for_timeout(1800)
    ok(not vis(), 'sai de cena no contato')
    pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(1800)
    ok(not vis(), 'volta a esconder no topo')

    pg.evaluate("document.querySelector('#planos').scrollIntoView()"); pg.wait_for_timeout(1800)
    g = pg.evaluate("(()=>{const n=document.querySelector('.nav__in').getBoundingClientRect(),h=document.querySelector('#planos .h2').getBoundingClientRect();return {nt:Math.round(n.top),nb:Math.round(n.bottom),ht:Math.round(h.top)}})()")
    ok(g['nt'] == 12 and g['ht'] > g['nb'], f'barra do topo acompanha a rolagem e não cobre o título da seção (barra {g["nt"]}-{g["nb"]}, título em {g["ht"]})')
    pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(1500)

    # ------------------------------------------------------------ 4) formulário
    print('4) formulário de contato')
    ok(pg.is_checked('.js-form [name=fase][value="Já tenho empresa"]'), 'página inicial: "Já tenho" vem marcado')
    pg.click('.js-form button[type=submit]')
    ok('nome' in pg.inner_text('.js-form-err').lower(), 'sem nome: mostra o erro em vez de enviar')
    pg.fill('.js-form [name=nome]', 'Maria Teste'); pg.fill('.js-form [name=whats]', '(11) 98888-7777')
    pg.fill('.js-form [name=empresa]', 'Oficina Central'); pg.fill('.js-form [name=sobre]', 'Oficina mecânica com 4 funcionários.')
    eventos.clear()
    with ctx.expect_page() as nv: pg.click('.js-form button[type=submit]')
    destino = nv.value.url; nv.value.close()
    msg = texto_wa(destino)
    ok(destino.startswith(f'https://wa.me/{WA}?text=') and 'Maria Teste' in msg and 'Já tenho empresa' in msg and 'Oficina Central' in msg and 'Oficina mecânica' in msg, 'enviar abre o WhatsApp da empresa com a mensagem montada')
    print('     ' + msg.replace('\n', ' | '))
    ok(pg.is_visible('.js-done') and not pg.eval_on_selector('.js-done-wa', 'e=>e.hidden'), 'tela "Mensagem pronta" aparece com o botão de reenviar')
    ok(espera_evento(pg, lambda e: e.get('t') == 'form' and e.get('f') == 'tem'), 'envio contado (form, tem)')
    ok(all('Maria' not in json.dumps(e) and '98888' not in json.dumps(e) for e in eventos), 'a contagem não leva nome nem telefone')
    pg.click('.js-done-back'); ok(pg.is_visible('.js-form') and pg.input_value('.js-form [name=nome]') == 'Maria Teste', '"Editar mensagem" volta ao formulário preenchido')
    ok(not pg.erros, 'sem erros no console' + (' ' + str(pg.erros[:3]) if pg.erros else '')); pg.erros.clear()

    # ------------------------------------------------------------ 5) abrir empresa: teste de nome e texto do contador
    print('5) página "Vou abrir empresa"')
    pg.goto(SITE + '/abrir/', wait_until='load'); pg.wait_for_timeout(300)
    ok(pg.is_checked('.js-form [name=fase][value="Vou abrir minha empresa"]'), '"Vou abrir" vem marcado')
    ok(pg.get_attribute('.nav__link--alt', 'aria-current') == 'page', 'menu marca a página atual')
    eventos.clear()
    pg.fill('#nome-teste', 'Padaria Aurora'); pg.click('.js-nome-form button'); pg.wait_for_timeout(700)
    ok(pg.inner_text('.js-dom') == 'padariaaurora.com.br' and 'livre' in pg.inner_text('.js-dom-s').lower(), 'nome livre: mostra o domínio como livre')
    cta = pg.get_attribute('.js-nome-cta', 'href')
    ok(pg.is_visible('.js-nome-cta') and cta.startswith(f'https://wa.me/{WA}?text=') and 'Padaria Aurora' in texto_wa(cta), 'botão "verificação completa" leva o nome testado para o WhatsApp')
    ok(espera_evento(pg, lambda e: e.get('t') == 'nome') and all('aurora' not in json.dumps(e).lower() for e in eventos), 'teste contado sem enviar o nome digitado')
    pg.fill('#nome-teste', 'Google'); pg.click('.js-nome-form button'); pg.wait_for_timeout(700)
    ok('registrado' in pg.inner_text('.js-dom-s').lower() or 'ocupado' in pg.inner_text('.js-dom-s').lower() or 'dono' in pg.inner_text('.js-nome-msg').lower(), 'nome ocupado: avisa que já tem dono (' + pg.inner_text('.js-dom-s') + ')')
    eventos.clear()
    pg.fill('#atividade', 'pizzaria delivery'); pg.click('.js-cnae-form button[type=submit]'); pg.wait_for_timeout(200)
    cod = pg.eval_on_selector_all('.js-cnae-list .cnae__code', 'els=>els.map(e=>e.textContent)')
    ok(cod[:1] == ['5611-2/01'], f'pizzaria delivery -> CNAE {cod}')
    ok(pg.get_attribute('.js-cnae-wa', 'href').startswith('https://wa.me/?text='), 'texto do contador abre o WhatsApp para a pessoa escolher o contador (sem número fixo)')
    ok(espera_evento(pg, lambda e: e.get('t') == 'cnae') and all('pizzaria' not in json.dumps(e).lower() for e in eventos), 'geração contada sem enviar o texto digitado')
    ok(pg.get_attribute('.porta-video', 'href') == '../#plataforma', 'porta para o vídeo aponta para a plataforma na página inicial')
    ok(not pg.erros, 'sem erros no console' + (' ' + str(pg.erros[:3]) if pg.erros else '')); pg.erros.clear()

    # ------------------------------------------------------------ 6) página do teste de nome
    print('6) página do teste de nome')
    pg.goto(SITE + '/nome/', wait_until='load'); pg.wait_for_timeout(300)
    pg.fill('#nome-teste', 'Padaria Aurora'); pg.keyboard.press('Enter'); pg.wait_for_timeout(700)
    ok('livre' in pg.inner_text('.js-dom-s').lower() and pg.is_visible('.js-nome-cta'), 'teste funciona sozinho nesta página')
    r = pg.evaluate("(()=>{const a=document.querySelector('.ferr__txt').getBoundingClientRect(),b=document.querySelector('.ferr__tool').getBoundingClientRect();const t=[...document.querySelectorAll('.ferr__txt .line')].map(e=>e.getBoundingClientRect().right);return {txt:Math.max(...t),tool:b.left}})()")
    ok(r['txt'] <= r['tool'], f'título não invade o cartão ({r["txt"]:.0f} <= {r["tool"]:.0f})')
    ok(not pg.erros, 'sem erros no console' + (' ' + str(pg.erros[:3]) if pg.erros else '')); pg.erros.clear()
    ctx.close()

    # ------------------------------------------------------------ 7) celular
    print('7) celular (390 px)')
    ctx, pg = nova(b, 390, 844, cel=True)
    for url in ['/', '/abrir/', '/nome/', '/privacidade.html']:
        pg.goto(SITE + url, wait_until='load'); pg.wait_for_timeout(300)
        d = pg.evaluate('({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})')
        ok(d['sw'] <= d['cw'], f'{url}: nada vaza para o lado ({d["sw"]} <= {d["cw"]})')
    pg.goto(SITE + '/', wait_until='load'); pg.wait_for_timeout(300)
    ok(not pg.is_visible('#menu .nav__link'), 'menu começa fechado')
    pg.click('.nav__toggle'); pg.wait_for_timeout(250)
    ok(pg.is_visible('#menu .nav__link') and pg.get_attribute('.nav__toggle', 'aria-expanded') == 'true', 'menu abre')
    pg.click('#menu a[href="#planos"]'); pg.wait_for_timeout(2200)
    y = pg.evaluate("document.querySelector('#planos').getBoundingClientRect().top")
    ok(not pg.is_visible('#menu .nav__link') and 60 < y < 140, f'tocar em "Planos" fecha o menu e leva aos planos (topo em {y:.0f}px)')
    alvos = pg.evaluate("[...document.querySelectorAll('a.btn,button.btn,.nav__toggle,.wa-float')].filter(e=>e.offsetParent!==null).map(e=>Math.round(e.getBoundingClientRect().height)).filter(h=>h<44)")
    ok(not alvos, 'botões com pelo menos 44 px de altura para o dedo' + (' ' + str(alvos) if alvos else ''))
    ok(not pg.erros, 'sem erros no console' + (' ' + str(pg.erros[:3]) if pg.erros else '')); pg.erros.clear()
    ctx.close()

    # ------------------------------------------------------------ 8) quem pede para não ser rastreado não entra na conta
    print('8) respeito ao "não rastrear"')
    ctx, pg = nova(b, 1280, 800)
    pg.add_init_script("Object.defineProperty(navigator,'globalPrivacyControl',{get:()=>true})")
    eventos.clear(); pg.goto(SITE + '/', wait_until='load'); pg.wait_for_timeout(900)
    ok(not eventos, 'com o pedido de privacidade do navegador ligado, nada é contado')
    ctx.close()
    b.close()

print()
print('RESULTADO:', 'TUDO CERTO' if not falhas else f'{len(falhas)} FALHA(S)')
for f in falhas: print('  -', f)
sys.exit(1 if falhas else 0)
