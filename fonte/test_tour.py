import subprocess, time, json, sys
from playwright.sync_api import sync_playwright
srv=subprocess.Popen(['python3','/tmp/site/serve.py','/tmp/site/dist/site','8766'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(0.8)
ST='''()=>{const v=document.querySelector('.js-tour');return {paused:v.paused,t:+v.currentTime.toFixed(2),src:v.currentSrc.split('/').pop(),rs:v.readyState,dur:v.duration,controls:v.controls,
 cap:(document.querySelector('.tour__seg.is-on .tour__name')||{}).textContent,on:[...document.querySelectorAll('.tour__seg')].findIndex(b=>b.classList.contains('is-on')),
 fills:[...document.querySelectorAll('.tour__fill')].map(f=>f.style.transform.replace('scaleX(','').replace(')','')).join(' '),
 bt:document.querySelector('.js-tour-play-t').textContent,big:document.querySelector('.js-tour-big').hidden,w:v.videoWidth,h:v.videoHeight}}'''
try:
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox','--disable-gpu','--autoplay-policy=no-user-gesture-required'])
        for (W,H,dpr,tag) in [(1440,900,2,'desk'),(390,844,3,'cel')]:
            ctx=b.new_context(viewport={'width':W,'height':H},device_scale_factor=dpr,is_mobile=(tag=='cel'),has_touch=(tag=='cel'))
            pg=ctx.new_page(); errs=[]
            pg.on('console',lambda m: errs.append(m.type+': '+m.text) if m.type in('error','warning') else None)
            pg.on('pageerror',lambda e: errs.append('pageerror: '+str(e)))
            pg.goto('http://127.0.0.1:8766/index.html',wait_until='load')
            pg.wait_for_timeout(500)
            print(tag,'inicio',json.dumps(pg.evaluate(ST),ensure_ascii=False))
            pg.evaluate("document.querySelector('.tour__frame').scrollIntoView({block:'center'})")
            pg.wait_for_timeout(3500)
            print(tag,'na tela',json.dumps(pg.evaluate(ST),ensure_ascii=False))
            pg.screenshot(path=f'/tmp/site/shots/tour_{tag}_1.png')
            pg.wait_for_timeout(5000)
            print(tag,'+5s',json.dumps(pg.evaluate(ST),ensure_ascii=False))
            pg.click('.tour__li:nth-child(6) .tour__seg'); pg.wait_for_timeout(1800)
            print(tag,'parte 6',json.dumps(pg.evaluate(ST),ensure_ascii=False))
            pg.screenshot(path=f'/tmp/site/shots/tour_{tag}_2.png')
            pg.click('.js-tour-play'); pg.wait_for_timeout(400)
            print(tag,'pausa',json.dumps(pg.evaluate(ST),ensure_ascii=False))
            pg.evaluate("window.scrollTo(0,document.body.scrollHeight)"); pg.wait_for_timeout(600)
            pg.evaluate("document.querySelector('.tour__frame').scrollIntoView({block:'center'})"); pg.wait_for_timeout(900)
            print(tag,'voltou (pausado na mão)',json.dumps(pg.evaluate(ST),ensure_ascii=False))
            pg.click('.js-tour-play'); pg.wait_for_timeout(900)
            pg.evaluate("window.scrollTo(0,document.body.scrollHeight)"); pg.wait_for_timeout(700)
            print(tag,'fora da tela',json.dumps(pg.evaluate(ST),ensure_ascii=False))
            pg.evaluate("document.querySelector('.tour__frame').scrollIntoView({block:'center'})"); pg.wait_for_timeout(1200)
            print(tag,'voltou',json.dumps(pg.evaluate(ST),ensure_ascii=False))
            # fim do vídeo: volta ao começo
            pg.evaluate("document.querySelector('.js-tour').currentTime=56.2"); pg.wait_for_timeout(2200)
            print(tag,'depois do fim',json.dumps(pg.evaluate(ST),ensure_ascii=False))
            print(tag,'console',errs[:6])
            ctx.close()
        # sem movimento: não toca sozinho
        ctx=b.new_context(viewport={'width':1280,'height':800},reduced_motion='reduce'); pg=ctx.new_page()
        pg.goto('http://127.0.0.1:8766/index.html',wait_until='load')
        pg.evaluate("document.querySelector('.tour__frame').scrollIntoView({block:'center'})"); pg.wait_for_timeout(1500)
        print('sem movimento',json.dumps(pg.evaluate(ST),ensure_ascii=False))
        pg.screenshot(path='/tmp/site/shots/tour_rm.png')
        pg.click('.js-tour-big'); pg.wait_for_timeout(2500)
        print('sem movimento, clicou',json.dumps(pg.evaluate(ST),ensure_ascii=False))
        ctx.close(); b.close()
finally:
    srv.terminate()
