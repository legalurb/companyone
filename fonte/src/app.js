/* Company One — interações do site (companyone.com.br) */
(function () {
  'use strict';

  /* ------------------------------------------------------------------
     CONFIGURAÇÃO: é aqui que se liga o formulário de contato.
     whatsapp: número da empresa com DDI e DDD, só números. Ex.: '5511999999999'
     email:    caixa que recebe os contatos
     endpoint: opcional, endereço que recebe o formulário por POST (JSON)
     ------------------------------------------------------------------ */
  var CONFIG = {
    whatsapp: '%%WA%%',
    email: 'contato@companyone.com.br',
    endpoint: ''
  };
  // pasta onde o site está (as páginas internas ficam um nível abaixo)
  var BASE = ((document.currentScript && document.currentScript.src) || '').replace(/assets\/js\/[^/]*$/, '');

  function $(s, c) { return (c || document).querySelector(s); }
  function $$(s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); }
  function norm(s) { return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
  function dois(n) { return ('0' + n).slice(-2); }
  var semMovimento = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  /* ---------- medição: só contagens, sem cookies e sem identificar ninguém ----------
     Cada chamada vira uma linha no registro do próprio servidor (endereço /e).
     Quem pede ao navegador para não ser rastreado não entra na conta. */
  var NO_SITE = /(^|\.)companyone\.com\.br$/.test(location.hostname);
  var FORA_DA_CONTA = false;   // o dono pode tirar o próprio aparelho da conta, pelo painel
  try { FORA_DA_CONTA = localStorage.getItem('co-sem-contagem') === '1'; } catch (err) { /* sem acesso ao armazenamento: conta normalmente */ }
  function mede(tipo, dados) {
    if (!NO_SITE || FORA_DA_CONTA || navigator.doNotTrack === '1' || navigator.globalPrivacyControl) return;
    var q = 't=' + encodeURIComponent(tipo) + '&p=' + encodeURIComponent(location.pathname);
    if (dados) Object.keys(dados).forEach(function (k) {
      if (dados[k] !== '' && dados[k] !== null && dados[k] !== undefined) q += '&' + k + '=' + encodeURIComponent(String(dados[k]).slice(0, 60));
    });
    try { if (navigator.sendBeacon && navigator.sendBeacon('/e?' + q)) return; } catch (err) { /* cai no pedido de imagem */ }
    new Image().src = '/e?' + q;
  }
  (function () {
    var origem = '', par = null;
    try {
      if (document.referrer) {
        var h = new URL(document.referrer).hostname;
        if (h && h.indexOf('companyone.com.br') < 0) origem = h;
      }
      par = new URLSearchParams(location.search);
    } catch (err) { /* navegador antigo: conta a visita sem a origem */ }
    var larg = window.innerWidth || 0;
    mede('pv', {
      r: origem, us: par && par.get('utm_source'), um: par && par.get('utm_medium'), uc: par && par.get('utm_campaign'),
      w: larg < 700 ? 'cel' : larg < 1100 ? 'tab' : 'pc'
    });
    // até onde a pessoa rolou a página: 25, 50, 75 e 100%
    var marcas = [25, 50, 75, 100], vistas = {}, esperando = false;
    window.addEventListener('scroll', function () {
      if (esperando) return;
      esperando = true;
      setTimeout(function () {
        esperando = false;
        var de = document.documentElement, total = de.scrollHeight - window.innerHeight;
        var pct = total > 0 ? (window.scrollY || de.scrollTop) / total * 100 : 100;
        marcas.forEach(function (m) { if (pct >= m - 1 && !vistas[m]) { vistas[m] = true; mede('rolou', { d: m }); } });
      }, 400);
    }, { passive: true });
  })();

  /* ---------- WhatsApp da empresa: todo botão abre a conversa já com a mensagem ---------- */
  var MSG_PADRAO = 'Olá! Vim pelo site da Company One e quero conhecer.';
  function linkWa(texto) { return 'https://wa.me/' + CONFIG.whatsapp + '?text=' + encodeURIComponent(texto || MSG_PADRAO); }
  if (CONFIG.whatsapp) {
    $$('.js-wa').forEach(function (a) {
      a.href = linkWa(a.getAttribute('data-wa'));
      a.addEventListener('click', function () { mede('wa', { o: a.getAttribute('data-origem') || '' }); });
    });
  }

  /* ---------- botão flutuante do WhatsApp ----------
     Na abertura já existem dois botões de WhatsApp; o flutuante entra depois da primeira tela
     e sai de cena no contato e no rodapé, onde o botão já está à mão. */
  var boia = $('.wa-float');
  if (boia) {
    var noFim = {}, passou = false;
    var mostraBoia = function () {
      var some = false;
      Object.keys(noFim).forEach(function (k) { if (noFim[k]) some = true; });
      boia.classList.toggle('is-on', passou && !some);
    };
    var rolouBoia = function () {
      var agora = (window.scrollY || document.documentElement.scrollTop) > window.innerHeight * 0.6;
      if (agora !== passou) { passou = agora; mostraBoia(); }
    };
    window.addEventListener('scroll', rolouBoia, { passive: true });
    rolouBoia();
    if ('IntersectionObserver' in window) {
      var meio = new IntersectionObserver(function (es) {
        es.forEach(function (e) { noFim[e.target.id || e.target.className] = e.isIntersecting; });
        mostraBoia();
      }, { rootMargin: '-49% 0px -49% 0px' });
      [$('#contato'), $('.foot')].forEach(function (el) { if (el) meio.observe(el); });
    }
  }

  /* ---------- menu no celular ---------- */
  var toggle = $('.nav__toggle'), menu = $('#menu');
  function fechaMenu() {
    menu.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.textContent = 'Menu';
  }
  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      var aberto = menu.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', aberto ? 'true' : 'false');
      toggle.textContent = aberto ? 'Fechar' : 'Menu';
    });
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) fechaMenu(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fechaMenu(); });
  }

  /* ---------- relógio e atividades da abertura ---------- */
  var relogio = $('.js-clock'), feed = $('.js-feed');
  function marcaHora() {
    var d = new Date();
    relogio.textContent = 'Agora, ' + dois(d.getHours()) + ':' + dois(d.getMinutes());
  }
  if (relogio) { marcaHora(); setInterval(marcaHora, 20000); }

  var ATIVIDADES = [
    ['Financeiro', 'conciliou os recebimentos do dia'],
    ['Comercial', 'respondeu 3 pedidos de orçamento'],
    ['Marketing', 'deixou o post de amanhã pronto para aprovar'],
    ['Estoque', 'avisou: embalagens no nível mínimo'],
    ['Administrativo', 'organizou a agenda de segunda'],
    ['RH', 'separou os documentos da admissão'],
    ['Contábil', 'reuniu as notas do mês para o contador'],
    ['Comercial', 'retomou 5 clientes que não responderam'],
    ['Financeiro', 'enviou os lembretes de cobrança']
  ];
  if (feed && !semMovimento) {
    var proxima = 3;
    setInterval(function () {
      if (document.hidden) return;
      var a = ATIVIDADES[proxima % ATIVIDADES.length];
      proxima += 1;
      var li = document.createElement('li');
      li.className = 'feed__item is-new';
      var quem = document.createElement('span');
      quem.className = 'feed__who';
      quem.textContent = a[0];
      var oque = document.createElement('span');
      oque.textContent = a[1];
      li.appendChild(quem);
      li.appendChild(oque);
      feed.insertBefore(li, feed.firstChild);
      while (feed.children.length > 3) feed.removeChild(feed.lastChild);
    }, 3800);
  }

  /* ---------- linha do dia: marca o horário mais próximo de agora ---------- */
  var horarios = $$('.day__i');
  if (horarios.length) {
    var agoraMin = new Date().getHours() * 60 + new Date().getMinutes(), atual = horarios[horarios.length - 1];
    horarios.forEach(function (li) {
      var t = $('.day__h', li).firstChild.textContent.split(':');
      if (parseInt(t[0], 10) * 60 + parseInt(t[1], 10) <= agoraMin) atual = li;
    });
    atual.classList.add('is-now');
  }

  /* ---------- teste de nome: consulta ao vivo no Registro.br ---------- */
  var teste = { nome: '', slug: '', status: '' };
  var formNome = $('.js-nome-form'), campoNome = $('#nome-teste');
  var elDom = $('.js-dom'), elDomS = $('.js-dom-s'), elIg = $('.js-ig');
  var elNomeMsg = $('.js-nome-msg'), elNomeCta = $('.js-nome-cta');

  var NO_AR = /(^|\.)companyone\.com\.br$/.test(location.hostname) || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  function slugDe(nome) { return norm(nome).replace(/&/g, 'e').replace(/[^a-z0-9]+/g, ''); }

  // 200 = já registrado; 404 = não consta no Registro.br; qualquer outra coisa = não deu para consultar
  function consultaDominio(slug) {
    if (!window.fetch) return Promise.resolve('unknown');
    var ctrl = window.AbortController ? new AbortController() : null;
    var relogioLimite = setTimeout(function () { if (ctrl) ctrl.abort(); }, 8000);
    return fetch('https://rdap.registro.br/domain/' + slug + '.com.br', {
      headers: { 'Accept': 'application/rdap+json' },
      signal: ctrl ? ctrl.signal : undefined
    }).then(function (r) {
      clearTimeout(relogioLimite);
      if (r.status === 200) return 'taken';
      if (r.status === 404) return 'free';
      return 'unknown';
    }).catch(function () {
      clearTimeout(relogioLimite);
      return 'unknown';
    });
  }

  function situacaoDominio(status, slug) {
    elDomS.className = 'row__s js-dom-s';
    if (status === 'free') {
      elDomS.textContent = 'aparece livre';
      elDomS.classList.add('is-ok');
      elNomeMsg.textContent = 'Boa notícia: ' + slug + '.com.br aparece livre no Registro.br agora. Falta conferir o Instagram e a marca no INPI, e isso a equipe faz para você.';
    } else if (status === 'taken') {
      elDomS.textContent = 'já registrado';
      elDomS.classList.add('is-no');
      elNomeMsg.textContent = slug + '.com.br já tem dono. Na plataforma, a equipe sugere variações livres sem perder a ideia do nome.';
    } else {
      elDomS.textContent = NO_AR ? 'consulta indisponível' : 'no site publicado';
      elNomeMsg.textContent = NO_AR
        ? 'Não consegui consultar o Registro.br agora. Na verificação completa, a equipe confere o domínio, o Instagram e o INPI.'
        : 'Nesta prévia a consulta ao vivo fica desligada. No site publicado, o resultado do Registro.br aparece aqui na hora.';
    }
  }

  if (formNome) {
    formNome.addEventListener('submit', function (e) {
      e.preventDefault();
      var nome = campoNome.value.trim();
      var slug = slugDe(nome).slice(0, 26);
      if (slug.length < 2) {
        elNomeMsg.textContent = 'Escreva o nome que você imagina para a empresa.';
        campoNome.focus();
        return;
      }
      if (/^[0-9]+$/.test(slug)) {
        elNomeMsg.textContent = 'Um domínio .com.br precisa ter pelo menos uma letra.';
        campoNome.focus();
        return;
      }
      teste = { nome: nome, slug: slug, status: 'checking' };
      elDom.textContent = slug + '.com.br';
      elIg.textContent = '@' + slug;
      elDomS.className = 'row__s js-dom-s';
      elDomS.textContent = 'consultando...';
      elNomeMsg.textContent = 'Consultando o Registro.br...';
      consultaDominio(slug).then(function (status) {
        if (teste.slug !== slug) return;
        teste.status = status;
        situacaoDominio(status, slug);
        mede('nome', { s: status });
        if (CONFIG.whatsapp) {
          var achado = status === 'free' ? ' O domínio ' + slug + '.com.br aparece livre.' : status === 'taken' ? ' O domínio ' + slug + '.com.br já tem dono.' : '';
          elNomeCta.setAttribute('data-wa', 'Olá! Testei o nome "' + nome + '" no site da Company One.' + achado + ' Quero a verificação completa, com Instagram e INPI.');
          elNomeCta.href = linkWa(elNomeCta.getAttribute('data-wa'));
        }
        elNomeCta.hidden = false;
        var campoEmpresa = $('.js-form [name=empresa]');
        if (campoEmpresa && !campoEmpresa.value) campoEmpresa.value = nome;
        if (ultimaAtividade) geraTexto(ultimaAtividade);
      });
    });
  }

  /* ---------- CNAE e texto pronto para o contador ----------
     Códigos e descrições da tabela CNAE do IBGE (subclasses 2.3).
     É uma sugestão inicial para os negócios mais comuns: a definição é do contador. */
  var CNAE = {
    '1091-1/02': 'Fabricação de produtos de padaria e confeitaria com predominância de produção própria',
    '1412-6/02': 'Confecção, sob medida, de peças do vestuário, exceto roupas íntimas',
    '4321-5/00': 'Instalação e manutenção elétrica',
    '4322-3/01': 'Instalações hidráulicas, sanitárias e de gás',
    '4330-4/04': 'Serviços de pintura de edifícios em geral',
    '4399-1/03': 'Obras de alvenaria',
    '4520-0/01': 'Serviços de manutenção e reparação mecânica de veículos automotores',
    '4520-0/05': 'Serviços de lavagem, lubrificação e polimento de veículos automotores',
    '4530-7/03': 'Comércio a varejo de peças e acessórios novos para veículos automotores',
    '4712-1/00': 'Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - minimercados, mercearias e armazéns',
    '4721-1/02': 'Padaria e confeitaria com predominância de revenda',
    '4722-9/01': 'Comércio varejista de carnes - açougues',
    '4723-7/00': 'Comércio varejista de bebidas',
    '4724-5/00': 'Comércio varejista de hortifrutigranjeiros',
    '4744-0/99': 'Comércio varejista de materiais de construção em geral',
    '4751-2/01': 'Comércio varejista especializado de equipamentos e suprimentos de informática',
    '4752-1/00': 'Comércio varejista especializado de equipamentos de telefonia e comunicação',
    '4754-7/01': 'Comércio varejista de móveis',
    '4761-0/03': 'Comércio varejista de artigos de papelaria',
    '4763-6/02': 'Comércio varejista de artigos esportivos',
    '4772-5/00': 'Comércio varejista de cosméticos, produtos de perfumaria e de higiene pessoal',
    '4774-1/00': 'Comércio varejista de artigos de óptica',
    '4781-4/00': 'Comércio varejista de artigos do vestuário e acessórios',
    '4782-2/01': 'Comércio varejista de calçados',
    '4789-0/02': 'Comércio varejista de plantas e flores naturais',
    '4789-0/04': 'Comércio varejista de animais vivos e de artigos e alimentos para animais de estimação',
    '4930-2/01': 'Transporte rodoviário de carga, exceto produtos perigosos e mudanças, municipal',
    '4930-2/02': 'Transporte rodoviário de carga, exceto produtos perigosos e mudanças, intermunicipal, interestadual e internacional',
    '5320-2/02': 'Serviços de entrega rápida',
    '5611-2/01': 'Restaurantes e similares',
    '5611-2/03': 'Lanchonetes, casas de chá, de sucos e similares',
    '5611-2/04': 'Bares e outros estabelecimentos especializados em servir bebidas, sem entretenimento',
    '5612-1/00': 'Serviços ambulantes de alimentação',
    '5620-1/02': 'Serviços de alimentação para eventos e recepções - bufê',
    '5620-1/04': 'Fornecimento de alimentos preparados preponderantemente para consumo domiciliar',
    '6201-5/01': 'Desenvolvimento de programas de computador sob encomenda',
    '6201-5/02': 'Web design',
    '6202-3/00': 'Desenvolvimento e licenciamento de programas de computador customizáveis',
    '7020-4/00': 'Atividades de consultoria em gestão empresarial, exceto consultoria técnica específica',
    '7311-4/00': 'Agências de publicidade',
    '7319-0/03': 'Marketing direto',
    '7420-0/01': 'Atividades de produção de fotografias, exceto aérea e submarina',
    '8219-9/99': 'Preparação de documentos e serviços especializados de apoio administrativo não especificados anteriormente',
    '8230-0/01': 'Serviços de organização de feiras, congressos, exposições e festas',
    '8593-7/00': 'Ensino de idiomas',
    '8599-6/04': 'Treinamento em desenvolvimento profissional e gerencial',
    '9313-1/00': 'Atividades de condicionamento físico',
    '9511-8/00': 'Reparação e manutenção de computadores e de equipamentos periféricos',
    '9512-6/00': 'Reparação e manutenção de equipamentos de comunicação',
    '9529-1/02': 'Chaveiros',
    '9602-5/01': 'Cabeleireiros, manicure e pedicure',
    '9602-5/02': 'Atividades de estética e outros serviços de cuidados com a beleza',
    '9609-2/08': 'Higiene e embelezamento de animais domésticos'
  };

  var PONTOS = {
    alim: 'alvará de funcionamento e licença sanitária do município',
    com: 'inscrição estadual e emissão de nota fiscal de venda',
    serv: 'inscrição municipal e nota fiscal de serviço (ISS)',
    beleza: 'alvará de funcionamento e licença sanitária do município',
    fit: 'inscrição municipal, nota fiscal de serviço e responsável técnico registrado no CREF',
    obra: 'inscrição municipal, nota fiscal de serviço e retenções de ISS e INSS em obras',
    transp: 'inscrição estadual ou municipal conforme o trajeto e registro na ANTT (RNTRC), quando exigido'
  };

  // k: palavras que identificam o negócio (sem acento) | p: CNAE principal | s: secundários | c: tipo | o: objeto social
  var NEGOCIOS = [
    { k: ['hamburguer', 'lanchonete', 'lanche', 'lanches', 'pastel', 'pastelaria', 'acai', 'cafeteria', 'cafe', 'sorvete', 'sorveteria', 'salgado', 'salgados', 'crepe', 'tapioca', 'suco', 'sucos', 'cachorro quente', 'hot dog', 'sanduiche', 'fast food', 'esfiha', 'esfirra'], p: '5611-2/03', s: [], c: 'alim', o: 'lanchonete, com preparo e venda de lanches, porções e bebidas para consumo no local' },
    { k: ['restaurante', 'self service', 'pizzaria', 'pizza', 'churrascaria', 'sushi', 'japones', 'comida', 'cozinha', 'bistro', 'cantina', 'galeteria', 'hamburgueria gourmet com mesas'], p: '5611-2/01', s: [], c: 'alim', o: 'restaurante, com preparo e venda de refeições e bebidas para consumo no local' },
    { k: ['marmita', 'marmitas', 'marmitex', 'marmitaria', 'dark kitchen', 'cozinha fantasma', 'comida congelada', 'congelados', 'so delivery', 'apenas delivery'], p: '5620-1/04', s: [], c: 'alim', o: 'preparo de refeições e alimentos para entrega em domicílio e retirada, sem consumo no local' },
    { k: ['bar', 'boteco', 'pub', 'choperia', 'chopp', 'petiscaria'], p: '5611-2/04', s: [], c: 'alim', o: 'bar, com venda de bebidas e porções para consumo no local' },
    { k: ['padaria', 'panificadora', 'confeitaria', 'bolo', 'bolos', 'doceria', 'doces', 'brigadeiro', 'paes'], p: '1091-1/02', s: ['4721-1/02'], c: 'alim', o: 'padaria e confeitaria, com fabricação própria e venda de pães, bolos, doces e salgados' },
    { k: ['food truck', 'foodtruck', 'trailer', 'ambulante', 'carrinho', 'barraca'], p: '5612-1/00', s: [], c: 'alim', o: 'serviço ambulante de alimentação, com preparo e venda de alimentos e bebidas' },
    { k: ['buffet', 'bufe', 'coffee break', 'catering'], p: '5620-1/02', s: ['8230-0/01'], c: 'alim', o: 'serviços de alimentação para eventos e recepções (bufê)' },
    { k: ['roupa', 'roupas', 'moda', 'boutique', 'brecho', 'vestuario', 'camiseta', 'camisetas', 'lingerie', 'biquini', 'jeans'], p: '4781-4/00', s: [], c: 'com', o: 'comércio varejista de artigos do vestuário e acessórios' },
    { k: ['calcado', 'calcados', 'sapato', 'sapatos', 'tenis', 'sandalia', 'chinelo'], p: '4782-2/01', s: ['4781-4/00'], c: 'com', o: 'comércio varejista de calçados e acessórios' },
    { k: ['mercadinho', 'minimercado', 'mini mercado', 'mercearia', 'mercado', 'emporio', 'conveniencia'], p: '4712-1/00', s: [], c: 'com', o: 'comércio varejista de mercadorias em geral, com predominância de produtos alimentícios (minimercado)' },
    { k: ['acougue', 'carnes', 'casa de carnes'], p: '4722-9/01', s: [], c: 'com', o: 'comércio varejista de carnes (açougue)' },
    { k: ['adega', 'bebidas', 'distribuidora de bebidas', 'deposito de bebidas', 'vinhos'], p: '4723-7/00', s: [], c: 'com', o: 'comércio varejista de bebidas' },
    { k: ['hortifruti', 'sacolao', 'frutas', 'verduras', 'quitanda'], p: '4724-5/00', s: [], c: 'com', o: 'comércio varejista de frutas, verduras e legumes (hortifrúti)' },
    { k: ['cosmetico', 'cosmeticos', 'perfumaria', 'perfume', 'perfumes', 'maquiagem'], p: '4772-5/00', s: [], c: 'com', o: 'comércio varejista de cosméticos, produtos de perfumaria e de higiene pessoal' },
    { k: ['pet shop', 'petshop', 'pet', 'racao', 'racoes'], p: '4789-0/04', s: ['9609-2/08'], c: 'com', o: 'comércio varejista de artigos e alimentos para animais de estimação, com serviços de banho e tosa' },
    { k: ['banho e tosa', 'banho pet', 'tosador'], p: '9609-2/08', s: ['4789-0/04'], c: 'serv', o: 'serviços de higiene e embelezamento de animais domésticos (banho e tosa)' },
    { k: ['material de construcao', 'materiais de construcao', 'deposito de construcao', 'ferragens', 'ferragem'], p: '4744-0/99', s: [], c: 'com', o: 'comércio varejista de materiais de construção em geral' },
    { k: ['assistencia tecnica de celular', 'assistencia de celular', 'conserto de celular', 'conserto de celulares', 'manutencao de celular'], p: '9512-6/00', s: ['4752-1/00'], c: 'serv', o: 'reparação e manutenção de aparelhos celulares, com venda de acessórios' },
    { k: ['celular', 'celulares', 'capinha', 'capinhas', 'smartphone', 'smartphones'], p: '4752-1/00', s: ['9512-6/00'], c: 'com', o: 'comércio varejista de aparelhos celulares e acessórios, com assistência técnica' },
    { k: ['moveis', 'movel', 'planejados'], p: '4754-7/01', s: [], c: 'com', o: 'comércio varejista de móveis' },
    { k: ['papelaria', 'material escolar'], p: '4761-0/03', s: [], c: 'com', o: 'comércio varejista de artigos de papelaria' },
    { k: ['otica', 'oculos'], p: '4774-1/00', s: [], c: 'com', o: 'comércio varejista de artigos de óptica' },
    { k: ['floricultura', 'flores', 'plantas'], p: '4789-0/02', s: [], c: 'com', o: 'comércio varejista de plantas e flores naturais' },
    { k: ['autopecas', 'auto pecas', 'pecas automotivas'], p: '4530-7/03', s: [], c: 'com', o: 'comércio varejista de peças e acessórios novos para veículos automotores' },
    { k: ['artigos esportivos', 'loja de esportes', 'material esportivo'], p: '4763-6/02', s: [], c: 'com', o: 'comércio varejista de artigos esportivos' },
    { k: ['assistencia tecnica de computador', 'conserto de computador', 'conserto de computadores', 'manutencao de computadores', 'tecnico de informatica'], p: '9511-8/00', s: ['4751-2/01'], c: 'serv', o: 'reparação e manutenção de computadores e de equipamentos periféricos' },
    { k: ['informatica', 'computadores', 'loja de informatica'], p: '4751-2/01', s: ['9511-8/00'], c: 'com', o: 'comércio varejista de equipamentos e suprimentos de informática' },
    { k: ['barbearia', 'barbeiro', 'salao', 'cabeleireiro', 'cabeleireira', 'cabelo', 'manicure', 'pedicure', 'unhas', 'nail', 'esmalteria', 'trancista'], p: '9602-5/01', s: [], c: 'beleza', o: 'serviços de cabeleireiro, barbearia, manicure e pedicure' },
    { k: ['estetica automotiva', 'lava jato', 'lavajato', 'lava rapido', 'lavagem de carros', 'polimento'], p: '4520-0/05', s: [], c: 'serv', o: 'serviços de lavagem, lubrificação e polimento de veículos automotores' },
    { k: ['estetica', 'depilacao', 'sobrancelha', 'sobrancelhas', 'cilios', 'massagem', 'spa', 'limpeza de pele'], p: '9602-5/02', s: ['9602-5/01'], c: 'beleza', o: 'serviços de estética e cuidados com a beleza' },
    { k: ['oficina', 'mecanica', 'mecanico', 'auto center', 'autocenter'], p: '4520-0/01', s: ['4530-7/03'], c: 'serv', o: 'serviços de manutenção e reparação mecânica de veículos automotores, com venda de peças' },
    { k: ['academia', 'crossfit', 'pilates', 'funcional', 'musculacao', 'personal'], p: '9313-1/00', s: [], c: 'fit', o: 'atividades de condicionamento físico' },
    { k: ['marketing', 'agencia de marketing', 'agencia de publicidade', 'social media', 'trafego pago', 'publicidade', 'propaganda', 'midias sociais', 'redes sociais'], p: '7311-4/00', s: ['7319-0/03'], c: 'serv', o: 'agência de publicidade e marketing, com criação de campanhas, gestão de mídia e de redes sociais' },
    { k: ['site', 'sites', 'web design', 'webdesign', 'criacao de sites', 'landing page'], p: '6201-5/02', s: ['6201-5/01'], c: 'serv', o: 'criação de sites e interfaces para a internet (web design)' },
    { k: ['software', 'sistema', 'sistemas', 'aplicativo', 'aplicativos', 'app', 'saas', 'programacao', 'programador', 'desenvolvedor', 'startup'], p: '6201-5/01', s: ['6202-3/00'], c: 'serv', o: 'desenvolvimento de programas de computador sob encomenda e licenciamento de programas customizáveis' },
    { k: ['consultoria', 'consultor', 'consultora', 'assessoria empresarial', 'gestao empresarial'], p: '7020-4/00', s: [], c: 'serv', o: 'consultoria em gestão empresarial' },
    { k: ['fotografia', 'fotografo', 'fotografa', 'foto', 'fotos', 'ensaio fotografico'], p: '7420-0/01', s: [], c: 'serv', o: 'produção de fotografias para eventos, ensaios e publicidade' },
    { k: ['costura', 'costureira', 'atelie', 'alfaiataria', 'alfaiate', 'roupas sob medida', 'sob medida'], p: '1412-6/02', s: [], c: 'serv', o: 'confecção, sob medida, de peças do vestuário' },
    { k: ['construcao', 'reforma', 'reformas', 'pedreiro', 'obra', 'obras', 'empreiteira', 'alvenaria'], p: '4399-1/03', s: ['4330-4/04'], c: 'obra', o: 'execução de obras de alvenaria, reformas e acabamentos' },
    { k: ['pintor', 'pintura'], p: '4330-4/04', s: [], c: 'obra', o: 'serviços de pintura de edifícios em geral' },
    { k: ['eletricista', 'eletrica', 'instalacao eletrica'], p: '4321-5/00', s: [], c: 'obra', o: 'instalação e manutenção elétrica' },
    { k: ['encanador', 'hidraulica', 'bombeiro hidraulico'], p: '4322-3/01', s: [], c: 'obra', o: 'instalações hidráulicas, sanitárias e de gás' },
    { k: ['frete', 'fretes', 'transporte de carga', 'transporte de cargas', 'transportadora', 'caminhao', 'carreto'], p: '4930-2/01', s: ['4930-2/02'], c: 'transp', o: 'transporte rodoviário de cargas, municipal e intermunicipal' },
    { k: ['motoboy', 'entregas', 'entrega rapida', 'entregador', 'motofrete', 'moto frete'], p: '5320-2/02', s: [], c: 'serv', o: 'serviços de entrega rápida' },
    { k: ['idiomas', 'ingles', 'espanhol', 'escola de idiomas'], p: '8593-7/00', s: [], c: 'serv', o: 'ensino de idiomas' },
    { k: ['curso', 'cursos', 'treinamento', 'treinamentos', 'capacitacao', 'palestra', 'palestras', 'mentoria'], p: '8599-6/04', s: [], c: 'serv', o: 'treinamento em desenvolvimento profissional e gerencial, com cursos e capacitações' },
    { k: ['eventos', 'cerimonial', 'organizacao de eventos', 'festas', 'casamento', 'casamentos', 'formatura'], p: '8230-0/01', s: [], c: 'serv', o: 'organização de feiras, congressos, exposições e festas' },
    { k: ['chaveiro', 'chaves'], p: '9529-1/02', s: [], c: 'serv', o: 'serviços de chaveiro' },
    { k: ['secretariado', 'assistente virtual', 'servicos administrativos', 'apoio administrativo', 'digitacao'], p: '8219-9/99', s: [], c: 'serv', o: 'preparação de documentos e serviços de apoio administrativo' }
  ];

  var REGULADAS = ['clinica', 'medic', 'dentista', 'odontolog', 'psicolog', 'fisioterap', 'nutricionista', 'advoca', 'advogad', 'contabil', 'contador', 'farmacia', 'drogaria', 'engenhari', 'arquitet', 'corretor', 'imobiliaria', 'veterinari', 'laboratorio', 'creche', 'vigilancia', 'seguranca', 'despachante', 'seguros'];
  var FORA_DA_TABELA = ['viagem', 'viagens', 'turismo', 'hotel', 'pousada', 'hospedagem', 'fabrica', 'fabricacao', 'industria', 'atacado', 'atacadista', 'importacao', 'exportacao', 'banco', 'financeira', 'cripto'];
  var PALAVRAS_ENTREGA = ['delivery', 'entrega em domicilio', 'entrega a domicilio', 'ifood', 'tele entrega', 'teleentrega'];
  var PALAVRAS_ONLINE = ['online', 'on line', 'internet', 'e commerce', 'ecommerce', 'loja virtual', 'instagram', 'marketplace'];

  function contem(texto, palavra) {
    // palavras curtas valem só inteiras ("bar" não pode casar com "barbearia"); as maiores valem pelo começo
    var fim = palavra.length <= 4 ? '(?![a-z0-9])' : '';
    return new RegExp('(^|[^a-z0-9])' + palavra.replace(/ /g, '\\s+') + fim).test(texto);
  }
  function algum(texto, lista) {
    for (var i = 0; i < lista.length; i++) if (contem(texto, lista[i])) return true;
    return false;
  }

  function identifica(descricao) {
    var t = norm(descricao).replace(/[^a-z0-9]+/g, ' ').trim();
    if (!t) return { tipo: 'vazio' };
    if (algum(t, REGULADAS)) return { tipo: 'regulada' };
    if (algum(t, FORA_DA_TABELA)) return { tipo: 'desconhecida' };
    var melhor = null, pontos = 0;
    NEGOCIOS.forEach(function (n) {
      var soma = 0;
      n.k.forEach(function (k) { if (contem(t, k)) soma += 2 + k.split(' ').length; });
      if (soma > pontos) { pontos = soma; melhor = n; }
    });
    if (!melhor) return { tipo: 'desconhecida' };
    var entrega = algum(t, PALAVRAS_ENTREGA), online = algum(t, PALAVRAS_ONLINE);
    var sec = melhor.s.slice(), objeto = melhor.o;
    if (melhor.c === 'alim' && entrega && melhor.p !== '5620-1/04') {
      if (sec.indexOf('5620-1/04') < 0) sec.push('5620-1/04');
      objeto += ', retirada e entrega em domicílio';
    }
    if (melhor.c === 'com' && online) objeto += ', inclusive com vendas pela internet';
    return { tipo: 'ok', descricao: descricao.trim().replace(/[.\s]+$/, ''), p: melhor.p, s: sec, objeto: objeto, pontos: PONTOS[melhor.c] };
  }

  var formCnae = $('.js-cnae-form'), campoAtiv = $('#atividade');
  var elLista = $('.js-cnae-list'), elTxt = $('.js-cnae-txt'), elCopiar = $('.js-copy'), elWa = $('.js-cnae-wa');
  var elNota = $('.cnae__note'), elAcoes = $('.cnae__actions');
  var ultimaAtividade = null;

  function linhaCnae(codigo, papel) {
    var li = document.createElement('li');
    li.className = 'cnae__item';
    var c = document.createElement('span'); c.className = 'cnae__code'; c.textContent = codigo;
    var d = document.createElement('span'); d.className = 'cnae__desc'; d.textContent = CNAE[codigo];
    var t = document.createElement('span'); t.className = 'cnae__tag label'; t.textContent = papel;
    li.appendChild(c); li.appendChild(d); li.appendChild(t);
    return li;
  }

  function hoje() {
    var d = new Date();
    return dois(d.getDate()) + '/' + dois(d.getMonth() + 1) + '/' + d.getFullYear();
  }

  function geraTexto(r) {
    var linhas = ['Olá! Vou abrir uma empresa e preciso da sua orientação para o registro.', ''];
    linhas.push('Atividade: ' + r.descricao + '.');
    if (teste.slug && (teste.status === 'free' || teste.status === 'taken')) {
      linhas.push('Nome pretendido: ' + teste.nome + ' (domínio ' + teste.slug + '.com.br ' + (teste.status === 'free' ? 'aparece livre' : 'já registrado') + ' no Registro.br em ' + hoje() + ').');
    } else if (teste.nome) {
      linhas.push('Nome pretendido: ' + teste.nome + '.');
    }
    linhas.push('Objeto social sugerido: ' + r.objeto + '.');
    linhas.push('CNAE principal sugerido: ' + r.p + ', ' + CNAE[r.p] + '.');
    r.s.forEach(function (codigo) { linhas.push('CNAE secundário sugerido: ' + codigo + ', ' + CNAE[codigo] + '.'); });
    linhas.push('Para validar com você: enquadramento (MEI, ME ou EPP) e regime tributário; ' + r.pontos + '.');
    linhas.push('');
    linhas.push('Texto preparado com a Company One, companyone.com.br');
    var texto = linhas.join('\n');
    elTxt.textContent = texto;
    elWa.href = 'https://wa.me/?text=' + encodeURIComponent(texto);
    return texto;
  }

  function mostraAtividade(descricao) {
    var r = identifica(descricao);
    if (r.tipo === 'vazio') { campoAtiv.focus(); return; }
    elLista.textContent = '';
    mede('cnae', { g: r.tipo === 'ok' ? r.p : r.tipo });
    if (r.tipo === 'ok') {
      ultimaAtividade = r;
      elLista.appendChild(linhaCnae(r.p, 'principal'));
      r.s.forEach(function (codigo) { elLista.appendChild(linhaCnae(codigo, 'secundário')); });
      geraTexto(r);
      elAcoes.hidden = false;
      elNota.textContent = 'Sugestão inicial para os negócios mais comuns, com códigos da tabela CNAE do IBGE. A definição final é sempre do seu contador.';
      return;
    }
    ultimaAtividade = null;
    elAcoes.hidden = true;
    if (r.tipo === 'regulada') {
      elTxt.textContent = 'Essa é uma atividade regulamentada: além do CNAE, costuma exigir registro em conselho profissional ou licença específica. Na plataforma, a equipe monta o caso completo para o seu contador.';
    } else {
      elTxt.textContent = 'Essa atividade não está na demonstração, que cobre os negócios mais comuns. Na plataforma, a equipe analisa a sua descrição, indica os CNAEs e monta o texto para o contador.';
    }
    elNota.textContent = 'Conte o que você vai fazer no formulário no fim da página e receba o seu caso analisado.';
    var campoSobre = $('.js-form [name=sobre]');
    if (campoSobre && !campoSobre.value) campoSobre.value = descricao.trim();
  }

  if (formCnae) {
    elWa.href = 'https://wa.me/?text=' + encodeURIComponent(elTxt.textContent);
    ultimaAtividade = identifica('hamburgueria com delivery');
    formCnae.addEventListener('submit', function (e) { e.preventDefault(); mostraAtividade(campoAtiv.value); });
    $$('.js-ex').forEach(function (b) {
      b.addEventListener('click', function () { campoAtiv.value = b.textContent; mostraAtividade(b.textContent); });
    });
  }

  function copia(texto, botao) {
    var original = botao.textContent;
    function ok() { botao.textContent = 'Copiado'; setTimeout(function () { botao.textContent = original; }, 1800); }
    function manual() {
      var area = document.createElement('textarea');
      area.value = texto;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      try { if (document.execCommand('copy')) ok(); } catch (err) { /* sem cópia automática: o texto continua visível para selecionar */ }
      document.body.removeChild(area);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(texto).then(ok, manual);
    else manual();
  }
  if (elCopiar) elCopiar.addEventListener('click', function () { copia(elTxt.textContent, elCopiar); });

  /* ---------- formulário de contato ---------- */
  var form = $('.js-form'), feito = $('.js-done'), erro = $('.js-form-err');
  var elMsgPronta = $('.js-done-txt'), btWa = $('.js-done-wa'), btMail = $('.js-done-mail');
  var btCopia = $('.js-done-copy'), btVolta = $('.js-done-back'), elMail = $('.js-mail-txt');

  function falha(msg, campo) {
    erro.textContent = msg;
    erro.hidden = false;
    if (campo) campo.focus();
  }

  if (form) {
    if (elMail) elMail.textContent = CONFIG.email;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      erro.hidden = true;
      var f = form.elements;
      var nome = f.nome.value.trim(), whats = f.whats.value.trim(), sobre = f.sobre.value.trim();
      var empresa = f.empresa.value.trim(), fase = f.fase.value;
      if (nome.length < 2) return falha('Diga o seu nome para a gente saber com quem fala.', f.nome);
      if (whats.replace(/\D/g, '').length < 10) return falha('Confira o WhatsApp: precisa do DDD e do número.', f.whats);
      if (sobre.length < 5) return falha('Conte em uma ou duas linhas o que a empresa faz ou vai fazer.', f.sobre);

      var linhas = ['Olá! Quero minha equipe na Company One.', '', 'Nome: ' + nome, 'WhatsApp: ' + whats, 'Situação: ' + fase];
      if (empresa) linhas.push('Empresa: ' + empresa);
      linhas.push('O que faz: ' + sobre);
      if (teste.slug && (teste.status === 'free' || teste.status === 'taken')) {
        linhas.push('Domínio testado no site: ' + teste.slug + '.com.br (' + (teste.status === 'free' ? 'aparece livre' : 'já registrado') + ')');
      }
      var mensagem = linhas.join('\n');

      function mostraPronta() {
        elMsgPronta.textContent = mensagem;
        mede('form', { f: fase === 'Já tenho empresa' ? 'tem' : 'abrir' });
        if (CONFIG.whatsapp) {
          btWa.href = linkWa(mensagem);
          btWa.hidden = false;
          // abre a conversa na hora; se o navegador segurar a janela, o botão continua na tela
          try { window.open(btWa.href, '_blank', 'noopener'); } catch (err) { /* segue com o botão */ }
        }
        btMail.href = 'mailto:' + CONFIG.email + '?subject=' + encodeURIComponent('Quero minha equipe Company One') + '&body=' + encodeURIComponent(mensagem);
        form.hidden = true;
        feito.hidden = false;
        feito.scrollIntoView({ block: 'nearest', behavior: semMovimento ? 'auto' : 'smooth' });
      }

      if (CONFIG.endpoint && window.fetch) {
        var botao = form.querySelector('button[type=submit]');
        botao.disabled = true;
        fetch(CONFIG.endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nome: nome, whatsapp: whats, fase: fase, empresa: empresa, sobre: sobre, dominio: teste.slug ? teste.slug + '.com.br' : '', situacao_dominio: teste.status, origem: 'companyone.com.br' })
        }).then(function (r) {
          botao.disabled = false;
          if (!r.ok) throw new Error('resposta ' + r.status);
          $('.done .h3').textContent = 'Recebido. A gente fala com você pelo WhatsApp.';
          elMsgPronta.textContent = mensagem;
          $('.done__acts').hidden = true;
          form.hidden = true;
          feito.hidden = false;
        }).catch(function () {
          botao.disabled = false;
          mostraPronta();
        });
      } else {
        mostraPronta();
      }
    });
    btCopia.addEventListener('click', function () { copia(elMsgPronta.textContent, btCopia); });
    btVolta.addEventListener('click', function () { feito.hidden = true; form.hidden = false; });
  }

  /* ---------- plataforma: passeio em vídeo, em partes ---------- */
  var tour = $('.js-tour');
  if (tour) {
    var segs = $$('.tour__seg'), fills = $$('.tour__fill');
    var capBox = $('.js-tour-cap'), capT = $('.js-tour-t'), capD = $('.js-tour-d');
    var btPlay = $('.js-tour-play'), btPlayT = $('.js-tour-play-t');
    var icoPause = $('.js-tour-ico-pause'), icoPlay = $('.js-tour-ico-play');
    var btFull = $('.js-tour-full'), btBig = $('.js-tour-big');
    // paisagem (tela inteira da gravação) e celular (recorte quadrado, mesmo tempo de cada parte)
    var VIDEOS = {
      grande: BASE + 'assets/video/tour-1920.mp4', medio: BASE + 'assets/video/tour-1280.mp4',
      celular: BASE + 'assets/video/tour-m1080.mp4', celularLeve: BASE + 'assets/video/tour-m720.mp4'
    };
    var telaCel = window.matchMedia ? window.matchMedia('(max-width: 700px)') : null;
    var inicios = segs.map(function (b) { return parseFloat(b.getAttribute('data-t')); });
    var duracao = parseFloat(tour.getAttribute('data-dur')) || 57;
    var rede = navigator.connection || {};
    var poupaDados = !!rede.saveData;
    var redeLenta = poupaDados || /2g|3g/.test(rede.effectiveType || '');
    var semAuto = semMovimento || poupaDados;
    var carregado = false, parouNaMao = false, naTela = false, parte = 0, girando = false, pulo = null, noAr = '';

    // com o script ligado, os controles são os da página; sem ele, ficam os do navegador
    tour.controls = false;
    tour.muted = true;

    var arquivo = function () {
      if (telaCel && telaCel.matches) return redeLenta ? VIDEOS.celularLeve : VIDEOS.celular;
      var pontos = Math.max(document.documentElement.clientWidth, window.innerWidth || 0) * Math.min(window.devicePixelRatio || 1, 2.5);
      return pontos >= 1500 && !redeLenta ? VIDEOS.grande : VIDEOS.medio;
    };
    var carrega = function () {
      if (carregado) return;
      carregado = true;
      noAr = arquivo();
      tour.src = noAr;
    };
    var emTelaCheia = function () { return (document.fullscreenElement || document.webkitFullscreenElement) === tour; };

    var contou = {};
    var mostraParte = function (i, anima) {
      parte = i;
      if (anima && !tour.paused && !contou[i]) { contou[i] = true; mede('video', { a: 'parte', n: i + 1 }); }
      segs.forEach(function (b, k) {
        if (k === i) { b.classList.add('is-on'); b.setAttribute('aria-current', 'true'); }
        else { b.classList.remove('is-on'); b.removeAttribute('aria-current'); }
      });
      capT.textContent = $('.tour__name', segs[i]).textContent;
      capD.textContent = $('.tour__desc-t', segs[i]).textContent;
      if (anima && !semMovimento) {
        capBox.classList.remove('is-in');
        void capBox.offsetWidth;
        capBox.classList.add('is-in');
      }
    };
    var pinta = function () {
      var t = pulo !== null ? pulo : (tour.currentTime || 0), n = inicios.length, atual = 0, i;
      for (i = 0; i < n; i++) if (t >= inicios[i] - 0.02) atual = i;
      for (i = 0; i < n; i++) {
        var fim = i + 1 < n ? inicios[i + 1] : duracao;
        var p = i < atual ? 1 : i > atual ? 0 : Math.max(0, Math.min(1, (t - inicios[i]) / (fim - inicios[i])));
        fills[i].style.transform = 'scaleX(' + p.toFixed(4) + ')';
      }
      if (atual !== parte) mostraParte(atual, true);
    };
    var gira = function () {
      pinta();
      if (tour.paused || tour.ended) { girando = false; return; }
      girando = true;
      window.requestAnimationFrame(gira);
    };
    var botao = function (tocando) {
      btPlayT.textContent = tocando ? 'Pausar' : 'Tocar';
      btPlay.setAttribute('aria-label', tocando ? 'Pausar o vídeo' : 'Tocar o vídeo');
      if (tocando) { icoPause.removeAttribute('hidden'); icoPlay.setAttribute('hidden', ''); }
      else { icoPlay.removeAttribute('hidden'); icoPause.setAttribute('hidden', ''); }
    };
    var toca = function () {
      carrega();
      btBig.hidden = true;
      var p = tour.play();
      if (p && p.then) p.then(null, function () { if (tour.paused) { btBig.hidden = false; botao(false); } });
    };
    var vaiPara = function (i) {
      var t = inicios[i] + 0.03;
      parouNaMao = false;
      if (tour.readyState >= 1) { try { tour.currentTime = t; } catch (err) { pulo = t; } }
      else pulo = t;
      mostraParte(i, true);
      pinta();
      toca();
    };

    tour.addEventListener('loadedmetadata', function () {
      if (tour.duration && isFinite(tour.duration)) duracao = tour.duration;
      if (pulo !== null) { tour.currentTime = pulo; pulo = null; }
    });
    tour.addEventListener('play', function () {
      botao(true);
      if (!girando) gira();
      if (!contou.inicio) { contou.inicio = true; mede('video', { a: 'inicio', c: telaCel && telaCel.matches ? 'cel' : 'pc' }); }
    });
    tour.addEventListener('pause', function () { botao(false); pinta(); });
    tour.addEventListener('seeked', pinta);
    tour.addEventListener('click', function () {
      if (tour.controls) return;
      if (tour.paused) { parouNaMao = false; toca(); }
      else { parouNaMao = true; tour.pause(); }
    });
    segs.forEach(function (b, i) { b.addEventListener('click', function () { vaiPara(i); }); });
    btPlay.addEventListener('click', function () {
      if (tour.paused) { parouNaMao = false; toca(); }
      else { parouNaMao = true; tour.pause(); }
    });
    btBig.addEventListener('click', function () { parouNaMao = false; toca(); });

    btFull.addEventListener('click', function () {
      carrega();
      try {
        if (tour.requestFullscreen) tour.requestFullscreen();
        else if (tour.webkitRequestFullscreen) tour.webkitRequestFullscreen();
        else if (tour.webkitEnterFullscreen) {
          if (tour.readyState >= 1) tour.webkitEnterFullscreen();
          else toca();
        }
      } catch (err) { /* navegador sem tela cheia: o vídeo segue na página */ }
    });
    var aoMudarTela = function () { tour.controls = emTelaCheia(); };
    document.addEventListener('fullscreenchange', aoMudarTela);
    document.addEventListener('webkitfullscreenchange', aoMudarTela);
    tour.addEventListener('webkitbeginfullscreen', function () { tour.controls = true; });
    tour.addEventListener('webkitendfullscreen', function () {
      tour.controls = false;
      if (!parouNaMao && naTela && !semAuto) toca();
    });

    // virou o celular ou mudou o tamanho da janela: troca o corte e segue do mesmo ponto
    var trocaCorte = function () {
      if (!carregado || arquivo() === noAr) return;
      var tocando = !tour.paused;
      pulo = tour.currentTime || 0;
      noAr = arquivo();
      tour.src = noAr;
      if (tocando) toca(); else tour.load();
    };
    if (telaCel) {
      if (telaCel.addEventListener) telaCel.addEventListener('change', trocaCorte);
      else if (telaCel.addListener) telaCel.addListener(trocaCorte);
    }

    botao(false);
    mostraParte(0, false);
    if (semAuto || !('IntersectionObserver' in window)) {
      btBig.hidden = false;
    } else {
      // começa a baixar um pouco antes de entrar na tela e toca só enquanto está à vista
      var perto = new IntersectionObserver(function (es) {
        if (!es[0].isIntersecting) return;
        carrega();
        tour.preload = 'auto';
        perto.disconnect();
      }, { rootMargin: '700px 0px' });
      perto.observe(tour);
      new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          naTela = e.isIntersecting && e.intersectionRatio >= 0.45;
          if (naTela) { if (!parouNaMao && tour.paused && !document.hidden) toca(); }
          else if (!tour.paused && !emTelaCheia()) tour.pause();
        });
      }, { threshold: [0, 0.2, 0.45, 0.7, 1] }).observe(tour);
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) { if (!tour.paused) tour.pause(); }
        else if (naTela && !parouNaMao) toca();
      });
    }
  }

})();
