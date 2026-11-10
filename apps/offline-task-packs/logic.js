export function makeTasks(text){return text.split('\n').map(x=>x.trim()).filter(Boolean).map((text,index)=>({id:String(index),text,done:false}));}
export function progress(packs){const tasks=packs.flatMap(p=>p.tasks);return {total:tasks.length,done:tasks.filter(t=>t.done).length};}
export function validPacks(value){return Array.isArray(value)&&value.every(p=>p&&typeof p.id==='string'&&typeof p.name==='string'&&Array.isArray(p.tasks)&&p.tasks.every(t=>t&&typeof t.id==='string'&&typeof t.text==='string'&&typeof t.done==='boolean'));}
