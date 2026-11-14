#!/bin/sh
# Company One: busca o que mudou no GitHub e mantém o endereço do site no Caddy.
# O cron roda este arquivo a cada 2 minutos (cópia instalada em /usr/local/sbin/companyone-sync).
set -u
DIR="/opt/caddy-sites/companyone"
ALVO="/opt/caddy-sites/companyone.caddy"
ORIGEM="$DIR/deploy/companyone.caddy"
DOMINIO="companyone.com.br"
IP_SERVIDOR="2.25.235.180"
AGORA() { date '+%F %T'; }

cd "$DIR" || exit 0
git pull -q --ff-only 2>/dev/null || true

# O endereço só entra no Caddy quando o DNS já aponta para este servidor;
# antes disso o certificado HTTPS falharia.
[ -f "$ORIGEM" ] || exit 0
if [ -f "$ALVO" ] && cmp -s "$ORIGEM" "$ALVO"; then exit 0; fi

IP_RAIZ=$(getent ahostsv4 "$DOMINIO" 2>/dev/null | awk 'NR==1{print $1}')
IP_WWW=$(getent ahostsv4 "www.$DOMINIO" 2>/dev/null | awk 'NR==1{print $1}')
if [ "$IP_RAIZ" != "$IP_SERVIDOR" ] || [ "$IP_WWW" != "$IP_SERVIDOR" ]; then
  echo "$(AGORA) aguardando o DNS: $DOMINIO -> ${IP_RAIZ:-sem resposta}, www -> ${IP_WWW:-sem resposta} (esperado $IP_SERVIDOR)"
  exit 0
fi

CADDY=$(docker ps --format '{{.Names}}' | grep -m1 -i caddy || true)
[ -n "$CADDY" ] || { echo "$(AGORA) contêiner do Caddy não encontrado"; exit 0; }

ANTES=""
if [ -f "$ALVO" ]; then ANTES=$(mktemp); cp "$ALVO" "$ANTES"; fi
cp "$ORIGEM" "$ALVO"
if docker exec "$CADDY" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/tmp/companyone-caddy.log 2>&1; then
  if docker exec "$CADDY" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile >>/tmp/companyone-caddy.log 2>&1; then
    echo "$(AGORA) endereço $DOMINIO ativo no Caddy"
  else
    echo "$(AGORA) o Caddy não recarregou; veja /tmp/companyone-caddy.log"
  fi
else
  if [ -n "$ANTES" ]; then cp "$ANTES" "$ALVO"; else rm -f "$ALVO"; fi
  echo "$(AGORA) a configuração nova do Caddy não validou; nada mudou"
  tail -3 /tmp/companyone-caddy.log
fi
[ -n "$ANTES" ] && rm -f "$ANTES"
exit 0
