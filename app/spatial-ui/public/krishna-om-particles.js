(() => {
  if(window.__KRISHNA_OM_PARTICLES__)return;
  window.__KRISHNA_OM_PARTICLES__=true;
  const shell=document.querySelector('#home .kb-core-shell');
  const button=document.getElementById('assistantOm');
  if(!shell||!button)return;
  const canvas=document.createElement('canvas');
  canvas.className='ai-om-particles';canvas.setAttribute('aria-hidden','true');
  shell.prepend(canvas);shell.dataset.aiParticles='1';
  const ctx=canvas.getContext('2d');if(!ctx)return;
  const sample=document.createElement('canvas');sample.width=320;sample.height=320;
  const glyph=sample.getContext('2d');glyph.fillStyle='#fff';glyph.textAlign='center';glyph.textBaseline='middle';
  glyph.font='240px "Nirmala UI", "Segoe UI", sans-serif';glyph.fillText('ॐ',160,172);
  const pixels=glyph.getImageData(0,0,320,320).data,points=[];
  for(let y=18;y<302;y+=4)for(let x=18;x<302;x+=4)if(pixels[(y*320+x)*4+3]>128)points.push({x:(x-160)/320,y:(y-160)/320});
  const count=Math.min(points.length,1250),particles=[];
  for(let i=0;i<count;i++){
    const target=points[Math.floor(i*points.length/count)];const angle=i*2.39996323;
    const vertical=1-2*(i+.5)/count;const r=Math.sqrt(1-vertical*vertical);
    particles.push({tx:target.x,ty:target.y,a:angle,x:Math.cos(angle)*r*.47,y:vertical*.47,z:Math.sin(angle)*r*.47,seed:(i*37%101)/101});
  }
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  let last=0,elapsed=0,raf=0,width=0,height=0;
  const ease=t=>t*t*(3-2*t);
  function draw(timestamp){
    raf=requestAnimationFrame(draw);
    if(document.hidden||document.body.dataset.view&&document.body.dataset.view!=='home'){last=timestamp;return;}
    if(timestamp-last<32)return;
    const delta=last?Math.min(timestamp-last,100):0;last=timestamp;elapsed+=delta;
    const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);
    if(!rect.width||!rect.height)return;
    const w=Math.round(rect.width*dpr),h=Math.round(rect.height*dpr);
    if(w!==width||h!==height){canvas.width=width=w;canvas.height=height=h;}
    ctx.clearRect(0,0,width,height);
    const time=elapsed/1000,phase=time%32;
    const assembly=reduced?1:phase<8?ease(phase/8):phase<24?1:1-ease((phase-24)/8);
    const scale=Math.min(width,height),cx=width/2,cy=height/2,spin=time*.12;
    const halo=ctx.createRadialGradient(cx,cy,0,cx,cy,scale*.49);halo.addColorStop(0,'rgba(143,132,235,.12)');halo.addColorStop(1,'rgba(143,132,235,0)');ctx.fillStyle=halo;ctx.fillRect(0,0,width,height);
    for(let ring=0;ring<3;ring++){
      ctx.beginPath();
      const tilt=[.29,.66,1.09][ring],radius=scale*(.39+ring*.037),rotation=spin*(ring%2?-1:1)+ring*.9;
      for(let i=0;i<=140;i++){
        const a=i/140*Math.PI*2,x=Math.cos(a)*radius,y=Math.sin(a)*radius*Math.cos(tilt),z=Math.sin(a)*Math.sin(tilt);
        const xr=x*Math.cos(rotation)-y*Math.sin(rotation),yr=x*Math.sin(rotation)+y*Math.cos(rotation);
        const p=1/(1+z*.12);i?ctx.lineTo(cx+xr*p,cy+yr*p):ctx.moveTo(cx+xr*p,cy+yr*p);
      }
      ctx.strokeStyle=['rgba(102,117,245,.18)','rgba(156,108,235,.17)','rgba(54,185,199,.2)'][ring];ctx.lineWidth=dpr*.65;ctx.stroke();
      for(let n=0;n<7;n++){
        const a=spin*(1+ring*.2)+n*Math.PI*2/7;
        const x=Math.cos(a)*radius,y=Math.sin(a)*radius*Math.cos(tilt),xr=x*Math.cos(rotation)-y*Math.sin(rotation),yr=x*Math.sin(rotation)+y*Math.cos(rotation);
        ctx.fillStyle=['#7887DD','#A886D2','#63B9C9'][ring];ctx.beginPath();ctx.arc(cx+xr,cy+yr,dpr*(n===0?2.4:1.2),0,Math.PI*2);ctx.fill();
      }
    }
    for(const p of particles){
      const angle=p.a+spin,c=Math.cos(angle-p.a),s=Math.sin(angle-p.a);
      const cloudX=p.x*c-p.z*s,cloudZ=p.x*s+p.z*c;
      const wave=reduced?0:Math.sin(time*1.1+p.seed*6.28)*.004;
      const x=cloudX*(1-assembly)+p.tx*.91*assembly;
      const y=p.y*(1-assembly)+(p.ty*.91+wave)*assembly;
      const z=cloudZ*(1-assembly)+(p.seed-.5)*.025*assembly;
      const perspective=1/(1+z*.8),px=cx+x*scale*perspective,py=cy+y*scale*perspective;
      const alpha=.38+assembly*.43+Math.max(0,-z)*.1;
      ctx.fillStyle=p.seed<.32?`rgba(81,98,196,${alpha})`:p.seed<.74?`rgba(143,104,193,${alpha})`:`rgba(42,158,177,${alpha})`;
      ctx.beginPath();ctx.arc(px,py,dpr*(assembly>.9?1.05:1.15)*perspective,0,Math.PI*2);ctx.fill();
    }
    const status=document.getElementById('aiParticlePhase');
    if(status){const label=reduced?'ॐ · STILLNESS':assembly>.98?'ॐ · IN HARMONY':phase<8?'PARTICLES · BECOMING ॐ':'ॐ · INTO THE UNIVERSE';if(status.textContent!==label)status.textContent=label;}
    if(reduced){cancelAnimationFrame(raf);raf=0;}
  }
  const caption=document.createElement('div');caption.id='aiParticlePhase';caption.className='ai-particle-phase';caption.textContent='PARTICLES · BECOMING ॐ';shell.appendChild(caption);
  raf=requestAnimationFrame(draw);
  window.addEventListener('beforeunload',()=>cancelAnimationFrame(raf),{once:true});
})();
