#!/usr/bin/env python3
"""Monta o passeio (trechos da gravação) num único arquivo por versão.

uso: tour.py NOME LARGURA ALTURA CRF MAXRATE_K [paisagem|celular]

paisagem: quadro inteiro da gravação.
celular:  quadrado, com um recorte escolhido para cada trecho (x, y, lado na gravação de 2550x1456).
As duas versões têm exatamente os mesmos tempos; os capítulos saem em chapters.json.
"""
import json, os, subprocess, sys, time

SRC = '/tmp/video/src.mp4'
FPS = 30
# capítulo, início na gravação (s), quadros, recorte para o celular (x, y, lado)
SHOTS = [
    ('escritorio', 0.4, 210, (460, 0, 1456)),
    ('equipe', 7.4, 108, (460, 0, 1456)),
    ('equipe', 11.0, 90, (1750, 0, 800)),
    ('caixa', 24.4, 150, (340, 0, 1456)),
    ('turnos', 39.5, 93, (400, 0, 1456)),
    ('turnos', 42.6, 71, (1700, 150, 850)),
    ('relatorio', 115.8, 75, (560, 0, 1456)),
    ('relatorio', 118.3, 75, (1730, 0, 820)),
    ('decisoes', 100.6, 72, (585, 0, 1456)),
    ('decisoes', 103.0, 90, (1024, 236, 1220)),
    ('celular', 64.1, 84, (1650, 290, 900)),
    ('celular', 78.3, 150, (1650, 290, 900)),
    ('recepcao', 187.4, 84, (300, 0, 1456)),
    ('recepcao', 190.2, 51, (1740, 0, 810)),
    ('montagem', 174.3, 279, (703, 0, 1456)),
    ('montagem', 183.6, 30, (880, 756, 700)),
]


def chapters():
    out, f, seen = [], 0, set()
    for name, _, n, _ in SHOTS:
        if name not in seen:
            seen.add(name)
            out.append({'id': name, 't': round(f / FPS, 3)})
        f += n
    return out, round(f / FPS, 3)


def main():
    name, w, h, crf, maxk = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], int(sys.argv[5])
    modo = sys.argv[6] if len(sys.argv) > 6 else 'paisagem'
    ch, total = chapters()
    json.dump({'chapters': ch, 'duration': total}, open('/tmp/video/chapters.json', 'w'), indent=1)
    cmd = ['ffmpeg', '-hide_banner', '-nostats', '-y']
    partes = []
    if modo == 'paisagem':
        # trechos vizinhos na gravação viram uma entrada só (sem corte)
        for _, s, n, _ in SHOTS:
            if partes and abs(partes[-1][0] + partes[-1][1] / FPS - s) < 1e-6:
                partes[-1][1] += n
            else:
                partes.append([s, n, None])
    else:
        partes = [[s, n, c] for _, s, n, c in SHOTS]
    for s, n, _ in partes:
        cmd += ['-ss', f'{s:.4f}', '-t', f'{n / FPS:.4f}', '-i', SRC]
    g = ''
    for i, (_, n, c) in enumerate(partes):
        corte = f'crop={c[2]}:{c[2]}:{c[0]}:{c[1]},' if c else ''
        g += f'[{i}:v]{corte}scale={w}:{h}:flags=lanczos,setsar=1,fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS[v{i}];'
    g += ''.join(f'[v{i}]' for i in range(len(partes))) + f'concat=n={len(partes)}:v=1:a=0,format=yuv420p[v]'
    cmd += ['-filter_complex', g, '-map', '[v]', '-an']
    keys = ','.join(f"{c['t']:.3f}" for c in ch)
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-maxrate', f'{maxk}k', '-bufsize', f'{2 * maxk}k',
            '-profile:v', 'high', '-g', '150', '-keyint_min', '30', '-force_key_frames', keys,
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart']
    out = f'/tmp/video/out/{name}.mp4'
    cmd.append(out)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-3000:])
        raise SystemExit(r.returncode)
    sz = os.path.getsize(out)
    nf = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=nb_frames,width,height,sample_aspect_ratio',
                         '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip()
    print(f'{name}: {sz / 1e6:.2f} MB, {sz * 8 / total / 1e6:.2f} Mbps, {time.time() - t0:.0f} s de codificação, duração {total} s, [{nf}]')


if __name__ == '__main__':
    main()
