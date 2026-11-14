"""Monta o site da Company One em dist/site a partir de src/ (páginas e partes) e assets/."""
import re, os, shutil, hashlib, json, math, html as htmlmod
SRC='/tmp/site/src'; A='/tmp/site/assets'; OUT='/tmp/site/dist/site'
WA='5527999836371'   # WhatsApp que recebe os contatos (provisório: trocar pelo número da empresa)

def rd(p): return open(p,encoding='utf-8').read()
def wr(p,s):
    os.makedirs(os.path.dirname(p),exist_ok=True); open(p,'w',encoding='utf-8').write(s)

logo=rd(A+'/img/logo.svg')
mark=json.load(open('/tmp/gen/v6.json'))['light']
MARK_ESCURO=('<path d="M91.82,91.82 A45,45 0 1,1 103.47,48.35" fill="none" stroke="#F6F1E7" stroke-width="9.6" stroke-linecap="round"/>'
             '<circle cx="103.47" cy="71.65" r="9.6" fill="#DB5740"/>'
             '<path d="M32.04,61.47 A28,28 0 1,1 56.59,87.79" fill="none" stroke="#F6F1E7" stroke-width="9.6" stroke-linecap="round"/>'
             '<circle cx="39.52" cy="79.10" r="6.8" fill="#F6F1E7"/>')
nomes=['Comercial','Financeiro','Contábil','RH','Marketing','Administrativo','Estoque']
chips=''
for k,n in enumerate(nomes):
    a=math.radians(-90+k*360/len(nomes))
    chips+=f'<span class="chip" style="left:{50+44*math.cos(a):.2f}%;top:{50+44*math.sin(a):.2f}%"><span class="chip__in"><span class="chip__dot"></span>{n}</span></span>'

PRECOS='São três planos, por mês: Studio, R$ 490, com até 3 funcionários de IA; Suíte, R$ 1.290, com até 7; e HQ, R$ 2.890, com até 15. Dá para começar pequeno e mudar de plano quando a empresa crescer.'
TEC='Não. Você pede por texto ou por áudio, do jeito que falaria com alguém da sua equipe.'
CIDADE=('Vocês atendem na minha cidade?','Atendemos. A Company One funciona pela internet e atende empresas de qualquer cidade do Brasil. Você usa a plataforma no computador e no celular.')
FAQ={
 'index.html':[
  ('Quanto custa?',PRECOS),
  ('Preciso entender de tecnologia?',TEC),
  CIDADE,
  ('Funciona só pelo WhatsApp?','Não. O centro é a plataforma Company One, o escritório onde ficam a equipe, as tarefas e o histórico. O WhatsApp é um atalho para pedir e aprovar de qualquer lugar.'),
  ('A IA faz as coisas sem me perguntar?','Você define o que anda sozinho e o que precisa da sua aprovação. Por padrão, tudo que fala em nome da sua empresa ou envolve dinheiro passa por você.'),
  ('E se a IA errar?','Antes de qualquer coisa sair, você vê a prévia exata e o motivo. Pagamento e contrato pedem confirmação forte. Cada funcionário de IA tem limite de gasto por dia, e um botão pausa a equipe inteira na hora.'),
  ('Vai substituir meu contador ou as pessoas da minha empresa?','O contador continua responsável pela contabilidade: a equipe organiza e entrega tudo para ele. E as pessoas da empresa ficam livres do trabalho repetitivo para cuidar de cliente, venda e decisão.'),
  ('Ainda não tenho empresa. Posso começar?','Pode. A Company One ajuda desde o nome, a marca e o domínio até o texto pronto para o contador abrir o CNPJ. Veja em <a href="abrir/">Vou abrir empresa</a>.'),
 ],
 'abrir/index.html':[
  ('A Company One abre o meu CNPJ?','Não. A abertura formal é feita pelo seu contador. A Company One cuida do que vem antes (nome, marca, domínio, logo, objeto social e sugestão de CNAE) e entrega o texto pronto para ele registrar.'),
  ('O teste de nome é de graça?','É. A consulta do domínio é feita na hora, direto no Registro.br, sem cadastro.'),
  ('A busca no INPI garante o registro da marca?','Não. É uma busca prévia, que mostra se já existe marca igual ou parecida na classe do seu negócio. O registro depende do pedido e do exame do INPI.'),
  ('Quanto custa?',PRECOS),
  ('Preciso entender de tecnologia?',TEC),
  CIDADE,
  ('Depois que a empresa abrir, o que muda?','A mesma equipe passa a tocar o dia a dia: comercial, financeiro, marketing e administrativo, com você aprovando o que importa.'),
 ],
}
def faq_html(itens):
    ico='<span class="faq__ico"><span class="faq__bar"></span><span class="faq__bar faq__bar--v"></span></span>'
    return '\n'.join(f'        <details class="faq__q"><summary class="faq__s">{q}{ico}</summary><p class="faq__a">{a}</p></details>' for q,a in itens)
def faq_jsonld(itens):
    limpa=lambda s: htmlmod.unescape(re.sub(r'<[^>]+>','',s))
    d={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":limpa(a)}} for q,a in itens]}
    return '<script type="application/ld+json">'+json.dumps(d,ensure_ascii=False)+'</script>'

css=rd(SRC+'/styles.css'); js=rd(SRC+'/app.js').replace('%%WA%%',WA)
# vídeos: o nome leva um pedaço do conteúdo, para o navegador nunca usar versão antiga guardada
VID={}
for f in sorted(os.listdir(A+'/video')):
    stem,ext=os.path.splitext(f)
    VID[f]=f"{stem}.{hashlib.md5(open(f'{A}/video/{f}','rb').read()).hexdigest()[:8]}{ext}"
def troca(s):
    for a,n in VID.items(): s=s.replace('video/'+a,'video/'+n)
    return s
css=troca(css); js=troca(js)
# imagem que aparece quando o link é enviado (WhatsApp, Instagram): o nome também muda quando a imagem muda
CAPA='capa.'+hashlib.md5(open(A+'/img/capa.jpg','rb').read()).hexdigest()[:8]+'.jpg'
vcss=hashlib.md5(css.encode()).hexdigest()[:8]; vjs=hashlib.md5(js.encode()).hexdigest()[:8]

# página -> (prefixo dos arquivos, início, raiz para âncoras, link de "vou abrir", link do teste de nome, situação marcada no formulário)
PAGINAS={
 'index.html':       dict(B='',    HOME='#topo', RAIZ='',    ABRIR='abrir/',    NOME='nome/',    FASE='tem'),
 'abrir/index.html': dict(B='../', HOME='../',   RAIZ='../', ABRIR='#topo',     NOME='../nome/', FASE='abrir'),
 'nome/index.html':  dict(B='../', HOME='../',   RAIZ='../', ABRIR='../abrir/', NOME='#topo',    FASE='abrir'),
 'privacidade.html': dict(B='',    HOME='./',    RAIZ='./',  ABRIR='abrir/',    NOME='nome/',    FASE='tem'),
 '404.html':         dict(B='/',   HOME='/',     RAIZ='/',   ABRIR='/abrir/',   NOME='/nome/',   FASE='tem'),
}
def render(name):
    cfg=PAGINAS[name]
    h=rd(f'{SRC}/{name}')
    for _ in range(4):   # partes dentro de partes
        h=re.sub(r'%%PARTE:([a-z0-9_]+)%%',lambda m: rd(f'{SRC}/partes/{m.group(1)}.html').rstrip('\n'),h)
    form=rd(f'{SRC}/partes/_form.html').rstrip('\n'); done=rd(f'{SRC}/partes/_done.html').rstrip('\n')
    if cfg['FASE']=='tem':
        a='value="Vou abrir minha empresa" checked'; b='value="Já tenho empresa"'
        assert a in form and b in form
        form=form.replace(a,'value="Vou abrir minha empresa"').replace(b,'value="Já tenho empresa" checked')
    h=h.replace('%%FORM%%',form).replace('%%DONE%%',done)
    itens=FAQ.get(name,[])
    h=h.replace('%%FAQ%%',faq_html(itens)).replace('%%FAQ_JSONLD%%',faq_jsonld(itens) if itens else '')
    h=h.replace('%%ABRIR_ATUAL%%',' aria-current="page"' if name=='abrir/index.html' else '')
    for k in ('HOME','RAIZ','ABRIR','NOME','B'): h=h.replace(f'%%{k}%%',cfg[k])
    h=(h.replace('%%LOGO%%',logo).replace('%%CHIPS%%',chips).replace('%%MARK%%',mark).replace('%%MARK_ESCURO%%',MARK_ESCURO)
        .replace('%%HERO_FAR%%',rd(SRC+'/hero_bg.svg')).replace('%%WA%%',WA))
    b=cfg['B']
    # dentro das partes os caminhos são escritos a partir da raiz do site
    if b: h=re.sub(r'(src|href)="assets/',lambda m: f'{m.group(1)}="{b}assets/',h)
    h=h.replace('assets/css/styles.css"',f'assets/css/styles.css?v={vcss}"').replace('assets/js/app.js"',f'assets/js/app.js?v={vjs}"')
    assert '%%' not in h, (name, re.findall(r'%%[^%]{0,30}%%',h)[:5])
    return troca(h).replace('img/capa.jpg','img/'+CAPA)

if os.path.isdir(OUT): shutil.rmtree(OUT)
for n in PAGINAS: wr(f'{OUT}/{n}',render(n))
wr(f'{OUT}/assets/css/styles.css',css); wr(f'{OUT}/assets/js/app.js',js)
os.makedirs(f'{OUT}/assets/fonts',exist_ok=True); os.makedirs(f'{OUT}/assets/img',exist_ok=True)
for f in ['archivo-800.woff2','archivo-900-italic.woff2','barlow-condensed-600.woff2','inter-400.woff2','inter-600.woff2']:
    shutil.copy(f'{A}/fonts/{f}',f'{OUT}/assets/fonts/{f}')
for f in os.listdir(A+'/img'): shutil.copy(f'{A}/img/{f}',f'{OUT}/assets/img/'+(CAPA if f=='capa.jpg' else f))
os.makedirs(f'{OUT}/assets/video',exist_ok=True)
for f,n in VID.items(): shutil.copy(f'{A}/video/{f}',f'{OUT}/assets/video/{n}')
wr(f'{OUT}/robots.txt','User-agent: *\nAllow: /\nDisallow: /e\n\nSitemap: https://companyone.com.br/sitemap.xml\n')
urls=['','abrir/','nome/','privacidade.html']
wr(f'{OUT}/sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>https://companyone.com.br/{u}</loc></url>\n' for u in urls)+'</urlset>\n')
wr(f'{OUT}/site.webmanifest',json.dumps({"name":"Company One","short_name":"Company One","start_url":"/","display":"browser","background_color":"#F6F1E7","theme_color":"#0D1729","icons":[{"src":"/assets/img/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/assets/img/icon-512.png","sizes":"512x512","type":"image/png"}]},ensure_ascii=False,indent=2))
tot=sum(os.path.getsize(os.path.join(d,f)) for d,_,fs in os.walk(OUT) for f in fs)
print('build ok', vcss, vjs, 'bytes', tot)
