export function today(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
export function dayGap(date,now=today()){if(!date)return null;return Math.round((Date.parse(date+'T00:00:00Z')-Date.parse(now+'T00:00:00Z'))/86400000);}
export function dateLabel(date,now=today()){const days=dayGap(date,now);if(days===null)return 'No date recorded';if(days<0)return `${Math.abs(days)} day${days===-1?'':'s'} past entered date`;if(days===0)return 'Entered date is today';return `Entered date in ${days} day${days===1?'':'s'}`;}
export function sortFoods(items){return [...items].sort((a,b)=>(a.date||'9999').localeCompare(b.date||'9999')||a.name.localeCompare(b.name));}
export function validFoods(items){return Array.isArray(items)&&items.every(i=>i&&['id','name','date','storage','quantity','notes'].every(k=>typeof i[k]==='string'));}
