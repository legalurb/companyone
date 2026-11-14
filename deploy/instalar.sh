#!/bin/sh
# Company One: instala o site neste servidor. Roda uma vez só.
# Depois disso, cada mudança enviada ao GitHub entra no ar sozinha em até 2 minutos.
set -eu
REPO="https://github.com/legalurb/companyone.git"
DIR="/opt/caddy-sites/companyone"

[ "$(id -u)" = "0" ] || { echo "Rode como root."; exit 1; }
if ! command -v git >/dev/null 2>&1; then
  echo "Instalando o git ..."
  apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git >/dev/null
fi

mkdir -p /opt/caddy-sites
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull -q --ff-only
else
  git clone -q "$REPO" "$DIR"
fi

install -m 755 "$DIR/deploy/sync.sh" /usr/local/sbin/companyone-sync
printf '%s\n' '*/2 * * * * root /usr/local/sbin/companyone-sync >> /var/log/companyone-site.log 2>&1' > /etc/cron.d/companyone-site
chmod 644 /etc/cron.d/companyone-site
/usr/local/sbin/companyone-sync || true

echo
echo "Pronto. Este servidor confere o GitHub a cada 2 minutos."
echo "https://companyone.com.br abre sozinho assim que o DNS apontar para cá."
echo "Acompanhar: tail -f /var/log/companyone-site.log"
