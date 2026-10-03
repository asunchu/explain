import {bundle} from '@remotion/bundler';
import {selectComposition,renderMedia,renderStill} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const mode=process.argv[2]||'full';
const timeline=JSON.parse(fs.readFileSync(path.join(root,'src/timeline.json')));
const serveUrl=await bundle({entryPoint:path.join(root,'src/index.jsx'),publicDir:path.join(root,'public')});
const composition=await selectComposition({serveUrl,id:'Explain'});
if(mode==='stills'){
 for(const scene of timeline.scenes){
  const frame=scene.start+Math.min(scene.duration-25, Math.max(100,scene.captions[1]?.start+25||100));
  await renderStill({composition,serveUrl,output:path.join(root,`output/${scene.id}.png`),frame,imageFormat:'png',scale:.75});
  console.log('Still:',scene.id);
 }
} else {
 let last=-1;
 const s=timeline.scenes.find(x=>x.id==='example');
 await renderMedia({composition,serveUrl,codec:'h264',audioCodec:'aac',pixelFormat:'yuv420p',crf:19,concurrency:4,
  outputLocation:path.join(root,mode==='sample'?'output/sample.mp4':'output/explain-raw.mp4'),
  ...(mode==='sample'?{frameRange:[s.start,s.start+s.duration-1]}:{}),
  onProgress:({progress})=>{let p=Math.floor(progress*10);if(p!==last){last=p;console.log(`Render ${p*10}%`);}}
 });
}
