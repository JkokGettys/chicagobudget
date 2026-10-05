import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
export type Box = {id:string;parent_id?:string|null;root?:string;name:string;short_name?:string;amount_cents:number;basis?:string;period_label?:string;why?:string;note?:string;kind?:string;path?:unknown[];source?:number|number[];side?:Record<string,any>[];side_ref?:string;n_children?:number;is_leaf?:boolean;depth?:number;collapse_into?:string};
const base = join(process.cwd(),'public/data');
function read<T>(file:string, fallback:T):T { const path=join(base,file); return existsSync(path)?JSON.parse(readFileSync(path,'utf8')) as T:fallback; }
export const manifest = read<Record<string,any>>('manifest.json',{});
export const spine = read<Box[]>('spine.json',[]);
export const sources = read<Record<string,any>[]>('sources.json',[]);
const records = new Map<string,Box>();
const chunks = manifest.chunks ?? {};
export function box(id:string):Box|undefined {
  if(records.has(id)) return records.get(id);
  const key = Object.keys(chunks).filter(k=>id===k||id.startsWith(k+'.')).sort((a,b)=>b.length-a.length)[0];
  if(key){ const file=String(chunks[key]); const data=read<any>(`chunks/${file.replace(/^chunks\//,'')}`,{}); for(const n of data.nodes??[]) records.set(n.id,n); }
  return records.get(id) ?? spine.find(n=>n.id===id);
}
export function children(id:string):Box[]{
  const own=box(id);
  // A chunk includes full children or lightweight boundary stubs.
  const key=Object.keys(chunks).filter(k=>id===k||id.startsWith(k+'.')).sort((a,b)=>b.length-a.length)[0];
  let stubs:Box[]=[];
  if(key){const data=read<any>(`chunks/${String(chunks[key]).replace(/^chunks\//,'')}`,{});stubs=data.stubs??[];}
  const combined=[...spine,...records.values(),...stubs.map(n=>({...n,parent_id:n.parent_id??n.id.slice(0,n.id.lastIndexOf('.'))}))];
  return [...new Map(combined.filter(n=>n.parent_id===id).map(n=>[n.id,n])).values()].sort((a,b)=>Math.abs(b.amount_cents)-Math.abs(a.amount_cents));
}
export const roots = ['city','cps','parks'] as const;
export const titles:Record<string,string>={city:'City of Chicago',cps:'Chicago Public Schools',parks:'Chicago Park District','city-twice':'Counted twice'};
export function href(n:Box){const root=n.root==='city-twice'?'city':n.root??n.id.split('.')[0];return n.id==='city-twice'?'/city/counted-twice':n.id===root?`/${root}`:`/${root}/box/${n.id}/`;}
export function compact(cents:number){const n=Math.abs(cents)/100;const value=n>=1e9?`$${(n/1e9).toFixed(2)} billion`:n>=1e6?`$${(n/1e6).toFixed(1)} million`:`$${Math.round(n).toLocaleString('en-US')}`;return cents<0?`takes away ${value}`:value;}
export function exact(cents:number){return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(cents/100)}
export const basisLabels:Record<string,string>={budget:'In the budget',tied:'Adds up exactly',gov_estimate:'Government estimate',paid_to_date:'Paid so far',proxy:'Our estimate',residual:'Leftover',adjustment:'Adjustment'};
export function sideFor(n:Box):Record<string,any>[]{return n.side_ref?read<Record<string,any>[]>(n.side_ref,[]):n.side??[]}
export function sourceFor(n:Box){return (Array.isArray(n.source)?n.source:[n.source]).filter((i):i is number=>typeof i==='number').map(i=>sources[i]).filter(Boolean)}
