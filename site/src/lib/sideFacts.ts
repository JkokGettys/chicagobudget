import {sourceUrl} from './sources';
export type SideFact = {kind?:string;label?:string;amount_cents?:number;basis?:string;period?:string;extra?:unknown;source?:number};
type Source = {url?:string;repo_path?:string;doc?:string;dataset?:string;note?:string};
const money = (cents:number) => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(cents/100);
const title = (value:string) => value.replace(/_/g,' ').replace(/\b\w/g,letter=>letter.toUpperCase());
const el = (tag:string,text?:string) => {const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node};
const append = (parent:Element,tag:string,text:string) => {const child=el(tag,text);parent.append(child);return child};
const object = (value:unknown):Record<string,unknown>|null => value!==null && typeof value==='object' && !Array.isArray(value) ? value as Record<string,unknown> : null;
const valueText = (key:string,value:unknown):string => typeof value==='number' && (key==='amount'||key==='amount_cents'||key.endsWith('_cents')||key==='by_year') ? money(value) : String(value);

function renderValue(parent:Element,key:string,value:unknown,depth=0):void {
  if(value==null || value==='')return;
  if(depth>5){append(parent,'span','Additional detail');return}
  if(Array.isArray(value)){
    const list=el('ul');parent.append(list);
    for(const item of value){const row=el('li');list.append(row);renderValue(row,'',item,depth+1)}
  } else if(object(value)){
    const list=el('dl');parent.append(list);
    for(const [name,item] of Object.entries(value)){
      if(item==null||item==='')continue;
      append(list,'dt',title(name));const description=el('dd');list.append(description);renderValue(description,name,item,depth+1);
    }
  } else append(parent,'span',valueText(key,value));
}
function sourceLink(source:Source|undefined,index:number):HTMLElement {
  const label=`Source ${index+1}${source?.doc?`: ${source.doc}`:source?.dataset?`: ${source.dataset}`:''}`;
  const href=source ? sourceUrl(source) : undefined;
  if(!href)return el('span',label);
  const a=el('a',label) as HTMLAnchorElement;a.href=href;a.target='_blank';a.rel='noopener noreferrer';return a;
}
let sourcesPromise:Promise<Source[]>|undefined;
function getSources():Promise<Source[]>{return sourcesPromise??=fetch('/data/sources.json').then(response=>{if(!response.ok)throw Error('Sources unavailable');return response.json()}).then(data=>Array.isArray(data)?data:[]).catch(()=>[])}

/** Render untrusted side facts using DOM text nodes, never HTML parsing. */
export async function renderSideFacts(container:HTMLElement,facts:SideFact[]):Promise<void>{
  container.replaceChildren();
  if(!Array.isArray(facts)||!facts.length){append(container,'p','No additional facts available.');return}
  const sources=await getSources();
  const groups=new Map<string,SideFact[]>();
  for(const fact of facts){if(!object(fact))continue;const kind=typeof fact.kind==='string'?fact.kind:'other';const period=typeof fact.period==='string'&&fact.period?fact.period:'Period not stated';const key=JSON.stringify([kind,period]);const group=groups.get(key)??[];group.push(fact);groups.set(key,group)}
  for(const [key,items] of groups){
    const [kind,period]=JSON.parse(key) as [string,string];const disclosure=el('details');disclosure.className='side-facts-group';
    append(disclosure,'summary',`${title(kind)} · ${period} (${items.length})`);
    const list=el('ul');disclosure.append(list);
    for(const fact of items){
      const row=el('li');list.append(row);
      append(row,'strong',typeof fact.label==='string'?fact.label:'Additional fact');
      if(typeof fact.amount_cents==='number'&&Number.isFinite(fact.amount_cents))append(row,'span',` ${money(fact.amount_cents)}`);
      const meta=el('p',`${typeof fact.basis==='string'?title(fact.basis):'Basis not stated'} · ${period}`);row.append(meta);
      const extra=object(fact.extra);
      if(extra&&Object.keys(extra).length){
        const detail=el('details');detail.className='side-fact-detail';append(detail,'summary','Details');row.append(detail);
        if(Array.isArray(extra.items)){
          append(detail,'h4','Payment details');
          const items=el('ul');detail.append(items);
          for(const raw of extra.items){const item=object(raw);if(!item)continue;const entry=el('li');items.append(entry);
            append(entry,'strong',item.is_individual===true?'Individual (name hidden)':typeof item.vendor==='string'?item.vendor:'Payment');
            if(typeof item.amount==='number')append(entry,'span',` · ${money(item.amount)}`);
            const fields=Object.fromEntries(Object.entries(item).filter(([name])=>!['vendor','amount','is_individual'].includes(name)));renderValue(entry,'',fields);
          }
        }
        const rest=Object.fromEntries(Object.entries(extra).filter(([name])=>name!=='items'));
        renderValue(detail,'',rest);
      }
      if(typeof fact.source==='number'&&Number.isInteger(fact.source)&&fact.source>=0){const citation=el('p');citation.append(sourceLink(sources[fact.source],fact.source));row.append(citation)}
    }
    container.append(disclosure);
  }
}
/** Initialize a SideFacts mount. sideRef is fetched only upon opening the outer disclosure. */
export function initSideFacts(root:HTMLElement):void {
  const disclosure=root.querySelector<HTMLElement>('details[data-side-toggle]');
  const output=root.querySelector<HTMLElement>('[data-side-output]');
  if(!disclosure||!output)return;
  let loaded=false;
  disclosure.addEventListener('toggle',async()=>{
    if(!('open' in disclosure)||!(disclosure as HTMLDetailsElement).open||loaded)return;
    loaded=true;output.setAttribute('aria-busy','true');
    try {
      const ref=root.dataset.sideRef;
      const facts=ref ? await (async()=>{if(!/^(?:\/?data\/)?side\/[\w-]+\.json$/.test(ref))throw Error('Invalid facts path');const response=await fetch(`/${ref.replace(/^\/?(?:data\/)?/,'data/')}`);if(!response.ok)throw Error('Facts unavailable');return response.json()})() : JSON.parse(root.dataset.side??'[]');
      await renderSideFacts(output,facts);
    }catch{output.replaceChildren(el('p','Could not load additional facts. Please try again later.'));loaded=false}
    finally{output.removeAttribute('aria-busy')}
  });
}
