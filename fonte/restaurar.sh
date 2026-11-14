#!/bin/sh
# Remonta a bancada de trabalho do site em /tmp/site a partir deste repositório.
# Uso (na raiz do repositório):  sh fonte/restaurar.sh  &&  python3 /tmp/site/build.py
# O resultado sai em /tmp/site/dist/site e tem que ficar idêntico à pasta site/.
set -eu
AQUI=$(cd "$(dirname "$0")" && pwd)
RAIZ=$(dirname "$AQUI")
[ ! -e /tmp/site ] || { echo "/tmp/site já existe; tire do caminho antes."; exit 1; }
mkdir -p /tmp/site /tmp/gen
cp -r "$AQUI/src" "$AQUI/assets" "$AQUI/og" /tmp/site/
cp "$AQUI"/*.py /tmp/site/
cp "$AQUI/marca.json" /tmp/gen/v6.json
# os vídeos e as capas ficam só em site/assets/video, com um pedaço do conteúdo no nome; aqui voltam ao nome simples
mkdir -p /tmp/site/assets/video
for f in "$RAIZ"/site/assets/video/*; do
  cp "$f" "/tmp/site/assets/video/$(basename "$f" | sed -E 's/\.[0-9a-f]{8}\././')"
done
echo "Bancada pronta em /tmp/site. Agora: python3 /tmp/site/build.py"
