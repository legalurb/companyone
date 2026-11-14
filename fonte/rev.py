# Tira retratos das três páginas (computador e celular) e monta folhas de revisão.
import sys, os, subprocess, time, json
from playwright.sync_api import sync_playwright
from PIL import Image
OUT='/tmp/site/shots'
PAGS=[('home','index.html'),('abrir','abrir/index.html'),('nome','nome/index.html'),('priv','privacidade.html')]
TAMS=[('d',1440,900),('n',1180,760),('c',390,800)]
srv=subprocess.Popen(['python3','/tmp/site/serve.py','/tmp/site/dist/site','8765'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1.0)
res={}
try:
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox','--disable-gpu'])
        for tag,W,H in TAMS:
            ctx=b.new_context(viewport={'width':W,'height':H},device_scale_factor=1,reduced_motion='reduce')
            for nome,url in PAGS:
                pg=ctx.new_page(); errs=[]
                pg.on('console',lambda m,errs=errs: errs.append(m.type+': '+m.text) if m.type in('error','warning') else None)
                pg.on('pageerror',lambda e,errs=errs: errs.append('pageerror: '+str(e)))
                pg.goto('http://127.0.0.1:8765/'+url,wait_until='networkidle'); pg.wait_for_timeout(500)
                info=pg.evaluate('''()=>{const de=document.documentElement;
                  const over=[...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.right>de.clientWidth+1||r.left<-1)}).slice(0,8).map(e=>e.tagName+'.'+(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)+' r='+Math.round(e.getBoundingClientRect().right));
                  return {h:de.scrollHeight,sw:de.scrollWidth,cw:de.clientWidth,over}}''')
                f=f'{OUT}/r_{tag}_{nome}.png'; pg.screenshot(path=f,full_page=True)
                res[f'{tag}_{nome}']=(info,errs[:5]); pg.close()
            ctx.close()
        b.close()
finally:
    srv.terminate()
for k,v in res.items(): print(k,json.dumps(v[0],ensure_ascii=False),v[1])
