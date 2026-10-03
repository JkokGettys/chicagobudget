export function sourceUrl(source:Record<string,any>):string|undefined {
  const official=source.url;
  if(typeof official==='string'&&/^https?:\/\//i.test(official))return official;
  const base=import.meta.env.PUBLIC_REPO_URL;
  const path=source.repo_path;
  if(typeof base==='string'&&/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/.test(base)&&typeof path==='string'&&/^(raw|data|research|build)\/[\w./ -]+$/.test(path)&&!path.split('/').includes('..'))return `${base.replace(/\/$/,'')}/blob/main/${path.split('/').map(encodeURIComponent).join('/')}`;
  return undefined;
}
