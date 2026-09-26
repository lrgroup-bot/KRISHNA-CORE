import * as THREE from './three/three.module.js';
import { GLTFLoader } from './three/GLTFLoader.js';

const STATE_CLIP={
  FLUTE:['flute','idle'], IDLE:['idle'], LISTENING:['listen','idle'],
  THINKING:['think','dhyan','idle'], SPEAKING:['talk','idle'],
  WISDOM:['wisdom','talk','idle'], PLAYFUL:['playful','smile','idle'],
  PROTECTION:['protection','idle'], DHYAN:['dhyan','idle'],
  SLEEPING:['sleep','idle'], WAKING:['wake','idle'], WORKING:['work','idle']
};

class KrishnaMobileAvatar {
  constructor(root){
    this.root=root;this.scene=null;this.camera=null;this.renderer=null;this.mixer=null;
    this.model=null;this.actions=new Map();this.active=null;this.state='FLUTE';this.clock=new THREE.Clock();
    this.frame=0;this.ready=false;
  }
  async start(){
    if(!this.root||!window.Krishna)return this.fail('avatar root unavailable');
    window.showKrishnaFallback?.('Loading trusted KRISHNA avatar in background');
    window.reportKrishnaUiReady?.('animated-fallback');
    window.onKrishnaAvatarSync=(raw)=>this.acceptSync(raw);
    try{
      if(Krishna.avatarSyncAsync){Krishna.avatarSyncAsync();return true;}
    }catch(e){}
    return this.fail('background avatar sync unavailable');
  }
  async acceptSync(raw){
    let sync={};
    try{sync=JSON.parse(String(raw||'{}'));}catch(e){return this.fail('avatar sync response invalid');}
    if(sync.error)return this.fail(sync.error);
    if(!sync.available||!sync.production_ready)return this.fail(sync.reason||'production GLB unavailable');
    try{
      this.scene=new THREE.Scene();
      this.camera=new THREE.PerspectiveCamera(28,1,.01,100);
      this.renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'high-performance'});
      this.renderer.setPixelRatio(Math.min(2,window.devicePixelRatio||1));
      this.renderer.outputColorSpace=THREE.SRGBColorSpace;
      this.root.replaceChildren(this.renderer.domElement);
      this.scene.add(new THREE.HemisphereLight(0xfff4d2,0x17314a,2.6));
      const key=new THREE.DirectionalLight(0xffe4ad,4.2);key.position.set(2.5,4,4);this.scene.add(key);
      const rim=new THREE.DirectionalLight(0x63dffa,2.0);rim.position.set(-3,2,-2);this.scene.add(rim);
      const loader=new GLTFLoader();
      const gltf=await new Promise((resolve,reject)=>loader.load(
        'https://krishna.local/avatar/krishna.glb?v='+encodeURIComponent(sync.sha256||Date.now()),
        resolve,undefined,reject
      ));
      this.model=gltf.scene;this.scene.add(this.model);
      this.mixer=new THREE.AnimationMixer(this.model);
      for(const clip of gltf.animations||[]){
        const name=String(clip.name||'').trim().toLowerCase();
        if(name)this.actions.set(name,this.mixer.clipAction(clip));
      }
      this.fit();
      window.hideKrishnaFallback?.();
      this.root.hidden=false;this.root.dataset.engine='three-glb';
      this.ready=true;this.resize();this.setState(this.state);this.animate();
      window.addEventListener('resize',()=>this.resize(),{passive:true});
      window.reportKrishnaUiReady?.('three-glb');
      return true;
    }catch(e){return this.fail('GLB render failed: '+String(e?.message||e));}
  }
  fail(reason){
    this.root?.setAttribute('hidden','');
    window.showKrishnaFallback?.(reason);
    window.reportKrishnaUiReady?.('animated-fallback');
    return false;
  }
  fit(){
    const box=new THREE.Box3().setFromObject(this.model,true);
    if(box.isEmpty()){this.camera.position.set(0,1.2,5);return;}
    const size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());
    this.model.position.sub(center);
    const fov=this.camera.fov*Math.PI/180;
    const distance=Math.max(2.2,(size.y*1.2)/(2*Math.tan(fov/2)));
    this.camera.position.set(0,size.y*.05,distance);
    this.camera.lookAt(0,0,0);
  }
  resize(){
    if(!this.renderer||!this.camera||!this.root)return;
    const w=Math.max(1,this.root.clientWidth),h=Math.max(1,this.root.clientHeight);
    this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();
  }
  setState(raw){
    const next=String(raw||'IDLE').toUpperCase();this.state=STATE_CLIP[next]?next:'IDLE';
    const choices=STATE_CLIP[this.state];
    let action=null;
    for(const name of choices){if(this.actions.has(name)){action=this.actions.get(name);break;}}
    if(action!==this.active){
      if(this.active)this.active.fadeOut(.25);
      this.active=action;
      if(action){action.reset().setLoop(THREE.LoopRepeat,Infinity).fadeIn(.25).play();}
    }
    if(this.root)this.root.dataset.state=this.state;
  }
  animate(){
    if(!this.ready)return;
    this.frame=requestAnimationFrame(()=>this.animate());
    const dt=Math.min(.05,this.clock.getDelta());
    this.mixer?.update(dt);
    if(this.model&&!this.active){
      const t=performance.now()/1000;
      this.model.rotation.z=Math.sin(t*.75)*.012;
      this.model.position.y=Math.sin(t*1.15)*.012;
    }
    this.renderer.render(this.scene,this.camera);
  }
}

const root=document.getElementById('avatar3d');
const avatar=new KrishnaMobileAvatar(root);
window.KrishnaAvatar3D=avatar;
window.setKrishnaAvatarState=(state)=>avatar.setState(state);
avatar.start();
