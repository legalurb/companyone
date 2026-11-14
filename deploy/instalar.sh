#!/bin/sh
# Company One: instala o site e o painel de visitas neste servidor.
# Pode rodar de novo quando quiser: ele só atualiza o que mudou e mantém o endereço do painel.
# Depois disso, cada mudança enviada ao GitHub entra no ar sozinha em até 2 minutos.
set -eu
REPO="https://github.com/legalurb/companyone.git"
DIR="/opt/caddy-sites/companyone"
CHAVE="/etc/companyone/painel.token"

[ "$(id -u)" = "0" ] || { echo "Rode como root."; exit 1; }
if ! command -v git >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  echo "Instalando o que falta (git e python3) ..."
  apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git python3 >/dev/null
fi

mkdir -p /opt/caddy-sites
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull -q --ff-only
else
  git clone -q "$REPO" "$DIR"
fi

install -m 755 "$DIR/deploy/sync.sh" /usr/local/sbin/companyone-sync
install -m 755 "$DIR/deploy/painel.py" /usr/local/sbin/companyone-painel

# Endereço secreto do painel: sorteado aqui, uma vez só, e guardado apenas neste servidor.
mkdir -p /etc/companyone
chmod 700 /etc/companyone
if [ ! -s "$CHAVE" ]; then
  ( umask 077; head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n' > "$CHAVE" )
fi
chmod 600 "$CHAVE"

printf '%s\n' \
  '*/2 * * * * root /usr/local/sbin/companyone-sync >> /var/log/companyone-site.log 2>&1' \
  '*/10 * * * * root /usr/local/sbin/companyone-painel > /dev/null 2>> /var/log/companyone-painel.log' \
  > /etc/cron.d/companyone-site
chmod 644 /etc/cron.d/companyone-site

/usr/local/sbin/companyone-sync || true
/usr/local/sbin/companyone-painel || echo "O painel ainda não pôde ser montado; o servidor tenta de novo em 10 minutos."

echo
echo "Pronto. Este servidor confere o GitHub a cada 2 minutos."
echo "Site: https://companyone.com.br"
echo
echo "Painel de visitas (guarde este endereço: quem tem o endereço vê os números):"
echo "  https://companyone.com.br/p-$(cat "$CHAVE")/"
echo
echo "Acompanhar o site: tail -f /var/log/companyone-site.log"
