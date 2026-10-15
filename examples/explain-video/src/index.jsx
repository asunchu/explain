import React from 'react';
import {registerRoot, Composition, AbsoluteFill, Sequence, Audio, staticFile, useCurrentFrame, interpolate, spring} from 'remotion';
import timeline from './timeline.json';

const C={bg:'#08161b',panel:'#10252c',edge:'#27424a',ink:'#edf4ed',muted:'#91a9ac',mint:'#a5f5c7',purple:'#b9a7ff',gold:'#f0cc86'};
const ease=(f,a=0,b=30)=>interpolate(f,[a,b],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
const move=(f,d=0)=>spring({frame:Math.max(0,f-d),fps:30,config:{damping:22,stiffness:95}});
const Box=({children,style={}})=><div style={{background:C.panel,border:`1px solid ${C.edge}`,borderRadius:28,...style}}>{children}</div>;
const Label=({children,color=C.muted,style={}})=><div style={{fontSize:24,letterSpacing:3,textTransform:'uppercase',fontWeight:600,color,...style}}>{children}</div>;
const Enter=({f,delay=0,children,style={}})=><div style={{opacity:ease(f,delay,delay+20),transform:`translateY(${(1-move(f,delay))*30}px)`,...style}}>{children}</div>;

function Mini({kind,f,color=C.mint}){
  f=Math.max(0,f);
  return <svg width="260" height="145" viewBox="0 0 260 145">
    {kind===0&&[0,1,2,3].map(i=><rect key={i} x="18" y={20+i*28} width={(i===3?118:210)*ease(f,8+i*8,24+i*8)} height={i===0?13:8} rx="4" fill={i===0?color:C.muted} opacity={i===0?1:.6}/>)}
    {kind===1&&<><path d="M55 70H200M130 70V117" stroke={C.edge} strokeWidth="3"/>{[[30,46],[105,46],[180,46],[105,100]].map(([x,y],i)=><rect key={i} x={x} y={y} width="48" height="35" rx="9" fill={i===1?color:C.panel} stroke={color} opacity={ease(f,i*9,i*9+20)}/>)}<circle cx={55+(f*1.5)%145} cy="64" r="5" fill={color}/></>}
    {kind===2&&<><path d="M20 115H240M20 115V20" stroke={C.edge} strokeWidth="2"/>{[0,1,2,3,4].map(i=><rect key={i} x={40+i*38} y={110-(30+i*13)*(0.6+.4*Math.sin(f/35))} width="22" height={(30+i*13)*(0.6+.4*Math.sin(f/35))} rx="4" fill={color} opacity={.4+i*.15}/>)}<line x1="35" y1="135" x2="230" y2="135" stroke={C.muted} strokeWidth="3"/><circle cx={130+75*Math.sin(f/35)} cy="135" r="7" fill={C.ink}/></>}
    {kind===3&&<><rect x="22" y="10" width="214" height="120" rx="16" fill="none" stroke={C.edge} strokeWidth="2"/><circle cx="130" cy="65" r={30+Math.sin(f/18)*3} fill={color}/><path d="M123 51L145 65L123 79Z" fill={C.bg}/><rect x="42" y="113" width={175*((f%130)/130)} height="4" rx="2" fill={color}/></>}
  </svg>;
}

function Intro({f}){
 const p=ease(f,15,95);
 return <>
  <div style={{position:'absolute',left:120,top:270}}>
   <Enter f={f}><Label color={C.mint}>A skill for understanding</Label></Enter>
   <Enter f={f} delay={10}><div style={{fontSize:224,fontWeight:600,letterSpacing:-12,lineHeight:1.2}}>Explain<span style={{color:C.mint}}>.</span></div></Enter>
   <Enter f={f} delay={28}><div style={{fontSize:43,color:C.muted,marginTop:12}}>See the idea. Follow the mechanism.</div></Enter>
  </div>
  <div style={{position:'absolute',right:120,top:270,width:470,height:470}}>
   {[0,1,2,3,4,5].map(i=>{let a=i*Math.PI/3+f/260;let r=170*(1-p)+95*p;return <div key={i} style={{position:'absolute',left:210+Math.cos(a)*r,top:210+Math.sin(a)*r,width:80,height:80,background:i%2?C.mint:C.purple,borderRadius:18,opacity:.22+.55*p,transform:`translate(-50%,-50%) rotate(${(1-p)*i*17}deg)`}}/>})}
   <div style={{position:'absolute',left:150,top:150,width:120,height:120,borderRadius:32,background:C.ink,color:C.bg,display:'flex',alignItems:'center',justifyContent:'center',fontSize:78,fontWeight:600,boxShadow:'0 0 100px #a5f5c720',transform:`scale(${move(f,30)})`}}>e</div>
  </div>
 </>;
}

function Brief({f}){
 return <div style={{position:'absolute',left:120,right:120,top:405}}>
  <Enter f={f} delay={8}><Box style={{padding:'30px 40px',display:'flex',alignItems:'center',gap:30}}><span style={{color:C.mint,fontSize:38}}>↗</span><span style={{fontSize:42}}>“Explain how a cache works to a curious beginner.”</span></Box></Enter>
  <div style={{display:'flex',gap:25,marginTop:35}}>{[['TOPIC','How a cache works'],['AUDIENCE','Curious beginner'],['OUTCOME','Understand the shortcut']].map(([a,b],i)=><Enter key={a} f={f} delay={35+i*16} style={{flex:1}}><Box style={{padding:32,height:170}}><Label color={[C.mint,C.purple,C.gold][i]}>{a}</Label><div style={{fontSize:36,marginTop:24}}>{b}</div></Box></Enter>)}</div>
 </div>
}

function Formats({f,scene}){
 const active=f<scene.captions[1].start?Math.min(1,Math.floor(f/85)):f<scene.captions[2].start?2:3;
 return <div style={{position:'absolute',left:120,right:120,top:408,display:'flex',gap:25}}>{[['Prose','Define it'],['Diagram','Connect it'],['Interactive','Explore it'],['Video','Follow it']].map(([a,b],i)=><Enter key={a} f={f} delay={i*10} style={{flex:1}}><Box style={{height:340,padding:30,borderColor:active===i?C.mint:C.edge,transform:`translateY(${active===i?-10:0}px)`,background:active===i?'#183b38':C.panel}}><Label color={active===i?C.mint:C.muted}>0{i+1}</Label><Mini kind={i} f={f-i*10} color={[C.ink,C.purple,C.gold,C.mint][i]}/><div style={{fontSize:39,marginTop:15}}>{a}</div><div style={{fontSize:26,color:C.muted,marginTop:12}}>{b}</div></Box></Enter>)}</div>
}

function Cache({f,scene}){
 const hit=f>=scene.captions[1].start;
 const start=hit?scene.captions[1].start:24;
 const phase=((f-start)%95)/95;
 const x=hit?interpolate(phase,[0,.5,1],[270,840,270]):interpolate(phase,[0,.45,.65,1],[270,1450,1450,270]);
 const y=hit?500:600;
 return <>
  <div style={{position:'absolute',left:125,top:375,display:'flex',gap:15}}>{['FIRST REQUEST','REPEAT REQUEST'].map((v,i)=><div key={v} style={{padding:'14px 22px',borderRadius:30,fontSize:24,background:Number(hit)===i?C.mint:C.panel,color:Number(hit)===i?C.bg:C.muted}}>{v}</div>)}</div>
  <svg style={{position:'absolute',left:0,top:0}} width="1920" height="1080">
   <path d="M390 600H1480" fill="none" stroke={hit?C.edge:C.purple} strokeWidth="4" strokeDasharray="9 12" opacity={hit?.3:.9}/>
   <path d="M390 550V500H960V550" fill="none" stroke={C.mint} strokeWidth="4" opacity={hit?1:.15}/>
   <circle cx={x} cy={y} r="13" fill={hit?C.mint:C.purple}/>
  </svg>
  {[[120,'You','Request data',C.ink],[780,'Cache',hit?'Reuse stored copy':'Store a copy',C.mint],[1440,'Origin','Original source',C.purple]].map(([left,a,b,col],i)=><Box key={a} style={{position:'absolute',left,top:540,width:i===1?360:300,height:170,padding:30,borderColor:col,opacity:hit&&i===2?.35:1}}><Label color={col}>{a}</Label><div style={{fontSize:31,marginTop:28}}>{b}</div></Box>)}
  <div style={{position:'absolute',left:120,top:765,fontSize:30,color:hit?C.mint:C.purple}}>{hit?'Stored response available → take the shorter path':'No stored response yet → fetch from the origin'}</div>
 </>
}

function Story({f,scene}){
 const cards=[['01','Evidence','Check the source',C.purple],['02','Script','Use plain language',C.gold],['03','Storyboard','One point per scene',C.mint]];
 return <div style={{position:'absolute',left:120,right:120,top:413,display:'flex',gap:50}}>{cards.map(([n,a,b,c],i)=><Enter key={n} f={f} delay={i*25} style={{flex:1}}><Box style={{height:320,padding:36}}><div style={{display:'flex',justifyContent:'space-between'}}><Label color={c}>{n}</Label><span style={{fontSize:32,color:c}}>↗</span></div><div style={{fontSize:46,marginTop:28}}>{a}</div><div style={{fontSize:29,color:C.muted,marginTop:18}}>{b}</div><div style={{display:'flex',gap:10,marginTop:35}}>{[0,1,2,3].map(j=><div key={j} style={{height:10,borderRadius:10,width:60,background:c,opacity:ease(f,20+i*25+j*8,40+i*25+j*8)}}/>)}</div></Box></Enter>)}</div>
}

function Motion({f}){
 return <div style={{position:'absolute',left:120,right:120,top:405,display:'flex',gap:30}}>{[['Remotion','Polished video',3,C.mint],['GSAP','Interactive web',2,C.gold],['Motion Canvas','Vector diagrams',1,C.purple]].map(([a,b,k,c],i)=><Enter key={a} f={f} delay={i*15} style={{flex:1}}><Box style={{height:350,padding:34}}><div style={{display:'flex',justifyContent:'center'}}><Mini kind={k} f={f} color={c}/></div><div style={{fontSize:44,marginTop:25,color:c}}>{a}</div><div style={{fontSize:29,color:C.muted,marginTop:14}}>{b}</div></Box></Enter>)}</div>
}

function Voice({f}){
 return <>
  <Box style={{position:'absolute',left:120,top:405,width:530,height:350,padding:40}}><Label color={C.mint}>Made on this computer</Label><div style={{fontSize:77,marginTop:22}}>Kokoro</div><div style={{fontSize:36,color:C.muted,marginTop:12}}>Local narration</div><div style={{fontSize:27,color:C.mint,marginTop:32}}>$0 in speech API charges</div></Box>
  <div style={{position:'absolute',left:730,top:445,width:1040}}><div style={{display:'flex',alignItems:'center',gap:8,height:135}}>{Array.from({length:70},(_,i)=><div key={i} style={{width:7,borderRadius:5,height:12+Math.abs(Math.sin(i*2.15+f*.12)*Math.sin(i*.21+f*.035))*108,background:i<45?C.mint:C.purple,opacity:.8}}/>)}</div><div style={{display:'flex',gap:18,marginTop:58}}>{['Passage 01','Passage 02','Passage 03'].map((v,i)=><Box key={v} style={{padding:'22px 26px',fontSize:29,color:C.muted,borderColor:i===Math.floor(f/65)%3?C.mint:C.edge}}>{v}</Box>)}</div></div>
 </>
}

function Sync({f}){
 const play=190+(f%220)/220*1310;
 return <Box style={{position:'absolute',left:120,right:120,top:405,height:380,padding:35}}>
  {['Voice','Visuals','Captions'].map((name,i)=><div key={name} style={{display:'flex',alignItems:'center',height:90,gap:28}}><div style={{fontSize:29,width:155,color:C.muted}}>{name}</div><div style={{display:'flex',gap:12,flex:1}}>{[320,460,310].map((w,j)=><div key={j} style={{height:56,width:w,borderRadius:12,background:[C.mint,C.purple,C.gold][i],opacity:.75,display:'flex',alignItems:'center',paddingLeft:25,color:C.bg,fontSize:23,fontWeight:600}}>{i===0?'▥  Passage ':i===1?'Scene ':'Caption '}{j+1}</div>)}</div></div>)}
  <div style={{position:'absolute',top:22,bottom:50,left:play,width:3,background:C.ink,boxShadow:'0 0 15px #ffffff55'}}><div style={{position:'absolute',left:-8,top:-2,width:18,height:18,background:C.ink,transform:'rotate(45deg)'}}/></div>
  <Label style={{marginLeft:182,marginTop:4,fontSize:19}}>Measured audio → scene timing → final render</Label>
 </Box>
}

function Verify({f}){
 return <>
  <Box style={{position:'absolute',left:120,top:405,width:850,height:370,padding:30}}><Label color={C.mint}>Inspect the rendered output</Label><div style={{marginTop:24,border:`1px solid ${C.edge}`,borderRadius:17,height:238,display:'flex',alignItems:'center',justifyContent:'center',gap:45}}><div style={{width:112,height:86,borderRadius:16,background:C.purple}}/><div style={{width:120,height:3,background:C.mint,position:'relative'}}><div style={{position:'absolute',left:(f%70)/70*120,top:-7,width:17,height:17,borderRadius:30,background:C.mint}}/></div><div style={{width:112,height:86,borderRadius:16,background:C.mint}}/></div></Box>
  <div style={{position:'absolute',left:1070,top:415}}>{['Facts & readable labels','Voice & pronunciation','Captions & timing','Playable export'].map((v,i)=><Enter f={f} delay={20+i*25} key={v}><div style={{display:'flex',alignItems:'center',gap:24,marginBottom:26,fontSize:34}}><span style={{display:'flex',alignItems:'center',justifyContent:'center',width:45,height:45,borderRadius:25,border:`1px solid ${C.mint}`,color:C.mint,fontSize:26}}>{i+1}</span>{v}</div></Enter>)}</div>
 </>
}

function Deliver({f}){
 return <div style={{position:'absolute',left:120,right:120,top:395}}>
  <Enter f={f}><Box style={{padding:'35px 42px',background:'#19392f',borderColor:'#527963'}}><Label color={C.mint}>Try it</Label><div style={{fontSize:44,marginTop:22,fontFamily:'Menlo, monospace'}}><span style={{color:C.mint}}>$explain</span> how a cache works</div></Box></Enter>
  <div style={{display:'flex',gap:18,marginTop:30}}>{['Codex','OpenCode','Claude Code'].map((v,i)=><Enter key={v} f={f} delay={20+i*10}><div style={{fontSize:30,padding:'18px 32px',border:`1px solid ${C.edge}`,borderRadius:50,color:C.muted}}>{v}</div></Enter>)}</div>
  <Enter f={f} delay={75}><div style={{fontSize:31,color:C.muted,marginTop:33}}>Finished artifact <span style={{color:C.mint,padding:'0 22px'}}>+</span> editable source <span style={{color:C.mint,padding:'0 22px'}}>+</span> transcript</div></Enter>
 </div>
}

function Writing({f,scene}){
 const step=f<scene.captions[1].start?0:f<scene.captions[2].start?1:2;
 return <>
 <div style={{position:'absolute',left:120,top:405,width:520}}>
  <Label color={step===2?C.gold:C.mint}>{['Descriptions','Instructions','Meaning'][step]}</Label>
  <div style={{fontSize:164,lineHeight:1.2,fontWeight:600,letterSpacing:-7,color:step===2?C.gold:C.ink}}>{['25','20','1'][step]}<span style={{fontSize:38,letterSpacing:0,color:C.muted,marginLeft:18}}>{step===2?'truth':'words max'}</span></div>
  <div style={{fontSize:32,color:C.muted,marginTop:16}}>{['One main idea per sentence.','One action per step.','Keep uncertainty intact.'][step]}</div>
 </div>
 <Box style={{position:'absolute',left:740,top:410,width:1060,height:340,padding:42}}>
 <Label color={C.purple}>{['A clear sentence','Separate the actions','Keep the qualification'][step]}</Label>
 {step===0?<><div style={{fontSize:46,marginTop:42}}>The cache stores a copy.</div><div style={{display:'flex',gap:10,marginTop:35}}>{['The','cache','stores','a','copy.'].map((w,i)=><div key={w} style={{fontSize:23,color:C.bg,background:i===2?C.mint:C.purple,padding:'12px 20px',borderRadius:10,opacity:ease(f,20+i*12,38+i*12)}}>{w}</div>)}</div></>:step===1?<div style={{fontSize:40,marginTop:35,lineHeight:1.8}}><div><span style={{color:C.mint}}>01</span> Stop the service.</div><div><span style={{color:C.mint}}>02</span> Restore the backup.</div></div>:<><div style={{fontSize:42,marginTop:42}}>The patch <span style={{color:C.gold,borderBottom:`3px solid ${C.gold}`}}>may</span> reduce failures.</div><div style={{fontSize:28,color:C.muted,marginTop:35}}>A possible result stays possible.</div></>}
 </Box></>
}
function Meaning({f,scene}){
 const change=f>=scene.captions[1].start;
 return <><div style={{position:'absolute',left:120,top:420}}><Label color={C.gold}>The source says</Label><div style={{fontSize:67,marginTop:30}}>The patch <span style={{color:C.gold}}>may</span> reduce failures.</div></div>
 <svg width="1920" height="1080" style={{position:'absolute',inset:0}}><path d="M840 560V620H470V650M840 620H1360V650" stroke={C.edge} strokeWidth="4" fill="none"/><circle cx="840" cy={560+ease(f,25,75)*60} r="8" fill={C.gold}/></svg>
 <Box style={{position:'absolute',left:120,top:650,width:770,padding:'27px 35px',borderColor:C.mint,opacity:ease(f,25,55)}}><Label color={C.mint}>Preserve the meaning</Label><div style={{fontSize:38,marginTop:20}}>A possible improvement.</div></Box>
 <Box style={{position:'absolute',left:960,top:650,width:840,padding:'27px 35px',borderColor:'#d78f95',opacity:change?1:.15}}><Label color="#efb2b7">Changing “may” to “will”</Label><div style={{fontSize:38,marginTop:20}}>Adds a promise the source never made.</div></Box>
 </>
}
function Request({f}){
 return <div style={{position:'absolute',left:120,right:120,top:405}}><Enter f={f}><Box style={{padding:'30px 40px',borderColor:C.mint}}><Label color={C.mint}>Your request</Label><div style={{fontSize:41,lineHeight:1.4,marginTop:20}}>“Explain database indexes to a beginner in a 60-second video.”</div></Box></Enter><div style={{display:'flex',gap:28,marginTop:34}}>{[['AUDIENCE','A beginner',C.purple],['FORMAT','A narrated video',C.mint],['LENGTH','60 seconds',C.gold]].map(([a,b,c],i)=><Enter key={a} f={f} delay={35+i*15} style={{flex:1}}><Box style={{padding:30,height:155,borderColor:c}}><Label color={c}>{a}</Label><div style={{fontSize:36,marginTop:20}}>{b}</div></Box></Enter>)}</div><Enter f={f} delay={100}><div style={{fontSize:28,color:C.muted,marginTop:30}}>You can also set the language, style, and budget.</div></Enter></div>
}
function Production({f,scene}){
 const a=scene.captions[1].start,b=scene.captions[2].start;
 if(f>=b)return <Sync f={f-b}/>;
 if(f>=a)return <Voice f={f-a}/>;
 return <><Box style={{position:'absolute',left:120,top:410,width:610,height:340,padding:36}}><Label color={C.purple}>Editable source</Label><div style={{fontFamily:'Menlo, monospace',fontSize:34,lineHeight:1.9,marginTop:25,color:C.muted}}><div style={{color:C.purple}}>&lt;Scene&gt;</div><div style={{paddingLeft:36}}>Words + visuals</div><div style={{color:C.purple}}>&lt;/Scene&gt;</div></div></Box><svg width="1920" height="1080" style={{position:'absolute',inset:0}}><path d="M770 580H1030" stroke={C.edge} strokeWidth="4"/><circle cx={770+ease(f,15,95)*260} cy="580" r="12" fill={C.mint}/></svg><Box style={{position:'absolute',left:1070,top:410,width:730,height:340,padding:30}}><Label color={C.mint}>The rendered scene</Label><div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:40,marginTop:25}}><Mini kind={3} f={f}/><div style={{fontSize:45}}>Remotion</div></div><div style={{fontSize:27,color:C.muted,marginTop:20}}>The same frame. The same visual state.</div></Box></>
}
function Finish({f}){
 return <div style={{position:'absolute',left:120,right:120,top:405}}><Enter f={f}><Box style={{padding:38,background:'#19392f',borderColor:'#527963'}}><Label color={C.mint}>Ask naturally</Label><div style={{fontSize:46,marginTop:25}}>“Explain database indexes with an interactive example.”</div></Box></Enter><div style={{display:'flex',gap:20,marginTop:30}}>{['Codex','Claude Code','OpenCode'].map((x,i)=><Enter key={x} f={f} delay={20+i*15}><div style={{fontSize:29,border:`1px solid ${C.edge}`,borderRadius:40,padding:'16px 28px',color:C.muted}}>{x}</div></Enter>)}</div><Enter f={f} delay={75}><div style={{fontSize:29,color:C.muted,marginTop:28}}>Global defaults need setup and testing. Explicit skill requests also work.</div></Enter><Enter f={f} delay={120}><div style={{fontSize:31,marginTop:30}}>Finished artifact <span style={{color:C.mint}}> + </span> editable source <span style={{color:C.mint}}> + </span> transcript</div></Enter></div>
}

const views={intro:Intro,writing:Writing,example:Meaning,formats:Formats,request:Request,production:Production,checks:Verify,finish:Finish};
function Scene({scene,index}){
 const f=useCurrentFrame();const View=views[scene.id];const cue=scene.captions.find(c=>f>=c.start&&f<c.end);
 const opacity=ease(f,0,12)*(1-ease(f,scene.duration-10,scene.duration));
 return <AbsoluteFill style={{opacity}}>
   <Audio src={staticFile(`audio/${scene.id}.wav`)}/>
   {scene.id!=='intro'&&<div style={{position:'absolute',left:120,top:194}}><Enter f={f}><Label color={C.mint}>{scene.chapter}</Label></Enter><Enter f={f} delay={5}><div style={{fontSize:76,fontWeight:500,letterSpacing:-2.5,marginTop:22}}>{scene.title}</div></Enter></div>}
   <View f={f} scene={scene}/>
   {cue&&<div style={{position:'absolute',left:190,right:190,top:892,height:105,display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center'}}><div style={{fontSize:34,lineHeight:1.4,color:C.ink,background:'#08161bea',padding:'14px 28px',borderRadius:14,maxWidth:1480}}>{cue.text}</div></div>}
   <div style={{position:'absolute',bottom:35,left:120,fontSize:19,letterSpacing:2,color:C.muted}}>EXPLAIN / HOW IT WORKS</div><div style={{position:'absolute',bottom:35,right:120,fontSize:19,color:C.muted}}>{String(index+1).padStart(2,'0')} / {timeline.scenes.length}</div>
 </AbsoluteFill>
}
function Film(){
 const f=useCurrentFrame();
 return <AbsoluteFill style={{background:C.bg,color:C.ink,fontFamily:'Arial, Helvetica, sans-serif',overflow:'hidden'}}>
  <AbsoluteFill style={{background:'radial-gradient(ellipse at 85% 5%, #23524550, transparent 55%), radial-gradient(ellipse at 3% 85%, #41345525, transparent 55%)'}}/>
  <AbsoluteFill style={{opacity:.18,backgroundImage:'linear-gradient(#43636b28 1px, transparent 1px),linear-gradient(90deg,#43636b28 1px,transparent 1px)',backgroundSize:'80px 80px'}}/>
  <div style={{position:'absolute',left:120,right:120,top:63,display:'flex',justifyContent:'space-between',alignItems:'center'}}><div style={{display:'flex',alignItems:'center',gap:16}}><div style={{width:39,height:39,borderRadius:11,background:C.mint,color:C.bg,fontSize:30,textAlign:'center',fontWeight:700}}>e</div><span style={{fontSize:28,fontWeight:600,letterSpacing:-.5}}>Explain</span></div><Label style={{fontSize:18}}>A small skill. A clearer idea.</Label></div>
  <div style={{position:'absolute',left:120,right:120,top:132,height:1,background:C.edge}}/>
  {timeline.scenes.map((s,i)=><Sequence key={s.id} from={s.start} durationInFrames={s.duration}><Scene scene={s} index={i}/></Sequence>)}
  <div style={{position:'absolute',bottom:0,left:0,height:5,width:`${f/timeline.duration*100}%`,background:C.mint}}/>
 </AbsoluteFill>
}
registerRoot(()=> <Composition id="Explain" component={Film} width={1920} height={1080} fps={30} durationInFrames={timeline.duration}/>);
