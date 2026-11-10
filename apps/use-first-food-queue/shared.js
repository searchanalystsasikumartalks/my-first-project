export function read(key,fallback){try {const value=JSON.parse(localStorage.getItem(key));return value??fallback;} catch{return fallback;}}
export function save(key,value){try{localStorage.setItem(key,JSON.stringify(value));say('Saved on this browser.');return true;}catch{say('Storage is unavailable or full. Changes remain in this tab only; export a backup.');return false;}}
export function say(message){document.getElementById('status').textContent=message;}
export function download(filename,text,type='text/plain'){const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);say('Export prepared. Check your downloads.');}
export function el(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
export function button(text,fn,cls='secondary'){const b=el('button',text,cls);b.type='button';b.addEventListener('click',fn);return b;}
export const id=()=>globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+Math.random().toString(36).slice(2);
