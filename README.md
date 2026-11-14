# Company One

Site da Company One: https://companyone.com.br

- `site/`: o que vai ao ar (HTML, CSS, fontes, imagens e o vídeo da plataforma em `site/assets/video/`).
  Três páginas: a inicial (para quem já tem empresa), `abrir/` (para quem vai abrir) e `nome/` (teste de nome).
- `deploy/`: instalação no servidor, atualização automática e painel de visitas.

Cada mudança enviada à branch `main` entra no ar sozinha em até 2 minutos.

## Contagem de visitas

O site não usa cookies. A cada visita e a cada clique importante (WhatsApp, vídeo, ferramentas), o navegador
avisa o servidor no endereço `/e`, e isso vira uma linha no registro de acesso. `deploy/painel.py` soma essas
linhas e escreve o painel num endereço secreto, sorteado na instalação e guardado só no servidor.

Para instalar ou atualizar os programas do servidor (o endereço do painel aparece no fim):

    ssh root@SERVIDOR "curl -fsSL https://raw.githubusercontent.com/legalurb/companyone/main/deploy/instalar.sh | sh"

## WhatsApp dos botões

O número que recebe os contatos está em `site/assets/js/app.js` (`CONFIG.whatsapp`) e nos links `wa.me` das páginas.
