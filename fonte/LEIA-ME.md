# Fonte do site

Aqui fica o que gera a pasta `site/`: as páginas e as partes (`src/`), o estilo e o comportamento
(`src/styles.css`, `src/app.js`), as fontes e imagens (`assets/`), o montador (`build.py`) e os testes.

## Para mexer no site

    sh fonte/restaurar.sh            # monta a bancada em /tmp/site
    python3 /tmp/site/build.py       # gera /tmp/site/dist/site
    python3 /tmp/site/test_all.py    # confere links, WhatsApp, formulário, ferramentas, celular e contagem
    python3 /tmp/site/test_tour.py   # confere o vídeo

Depois de testar: copiar `/tmp/site/dist/site` para `site/`, copiar o que mudou de `/tmp/site` de volta
para `fonte/`, e enviar para a branch `main`. O servidor publica sozinho em até 2 minutos.

Os testes precisam do Python com Playwright e do Google Chrome em `/usr/bin/google-chrome`.

## Onde fica cada coisa

- Número do WhatsApp dos botões: `build.py`, linha `WA=`.
- Preços e planos: `src/partes/planos.html` e a resposta "Quanto custa?" em `build.py`.
- Faixa de lançamento no topo: `src/partes/aviso.html`.
- Dúvidas frequentes: lista `FAQ` em `build.py`.
- Imagem que aparece quando o link é enviado: `assets/img/capa.jpg`, desenhada em `og/capa.html`.
- Vídeo: os arquivos prontos ficam em `site/assets/video/`. `video/tour.py` guarda como o primeiro corte foi feito.
