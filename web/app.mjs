import {monthsFor, compare, totals, csv} from './model.mjs';

const by = id => document.getElementById(id);
const nf = new Intl.NumberFormat('en-CA',{maximumFractionDigits:0});
const money = n => '$'+nf.format(n);
const pct = n => n === null ? '—' : n.toFixed(1)+'%';
const pp = n => n === null ? '—' : (n > 0 ? '+' : '')+n.toFixed(1)+' pp';
const date = m => new Date(Date.UTC(Number(m.slice(0,4)),Number(m.slice(4))-1,1)).toLocaleString('en-CA',{year:'numeric',month:'short',timeZone:'UTC'});
const range = months => months.length > 1 ? date(months[0])+' – '+date(months.at(-1)) : date(months[0]);
const text = (id, value) => {by(id).textContent=value;};
function options(id, list, preferred) {
  by(id).replaceChildren(...list.map(([value,label]) => new Option(label,value)));
  if (list.some(([key]) => key===preferred)) by(id).value=preferred;
}
const cache=new Map();
let edition, data, report, periods, request=0, expanded=false;
async function getJSON(url) {
  const response=await fetch(url);
  if (!response.ok) throw new Error('Edition unavailable');
  return response.json();
}
function cellrow(values) {
  const row=document.createElement('tr');
  for (const value of values) {
    const cell=document.createElement('td');
    cell.textContent=value;
    row.append(cell);
  }
  return row;
}
function drawTable() {
  const rows=expanded ? report.rows : report.rows.slice(0,8);
  by('ranking').replaceChildren(...rows.map(r=>cellrow([edition.countries[r.code],money(r.value),pct(r.share),pp(r.change)])));
  by('more').hidden=report.rows.length<=8;
  text('more',expanded ? 'Show top eight' : 'Show all '+report.rows.length+' destinations');
}
function drawSeries() {
  const code=by('destination').value, end=by('month').value;
  const months=edition.months.filter(m=>m<=end);
  const points=months.map(month=>{
    const {countries,total}=totals(data,[month]);
    const value=countries.get(code) ?? 0;
    return {month, value, hasTotal:total>0, share:total>0 ? 100*value/total : null};
  });
  text('trend-label',code ? edition.countries[code]+'’s share of monthly export value, '+range(months)+'. Vertical scale 0–100%. Grey ticks indicate unavailable shares.' : 'No destinations recorded for this selection.');
  by('bars').replaceChildren(...(code ? points : []).map(p=>{
    const bar=document.createElement('span');
    bar.className='bar'+(p.hasTotal?'':' missing');
    bar.style.height=(p.hasTotal ? Math.max(1,p.share*1.2) : 3)+'px';
    bar.title=date(p.month)+' · '+pct(p.share);
    return bar;
  }));
  by('series').replaceChildren(...(code ? points : []).map(p=>cellrow([date(p.month),p.hasTotal?money(p.value):'—',pct(p.share)])));
}
function display() {
  const p=by('province').value, k=by('product').value, month=by('month').value;
  periods=monthsFor(month,by('mode').value,edition.months);
  report=compare(data,periods);
  const top=report.rows[0];
  by('result').hidden=false;
  text('period-title',edition.provinces[p]+' · '+range(periods.selected));
  text('definition',edition.products[k][0]+' · '+(k === 'all' ? 'All HS chapters' : 'HS '+edition.products[k][1].replaceAll(',',', ')));
  text('value',report.current.countries.size ? money(report.current.total) : 'No reported rows');
  text('leader',top && report.current.total>0 ? edition.countries[top.code] : '—');
  text('lead-share',top ? pct(top.share) : '—');
  text('change',top?.change != null ? 'This destination held '+pct(top.oldShare)+' in the matching period a year earlier ('+pp(top.change)+' this year).'
    : 'A year-over-year share comparison needs published positive totals in both periods.');
  text('comparison',periods.previous.length ? 'Compared with '+range(periods.previous)+'. Share changes are in percentage points (pp).' : 'The matching period a year earlier falls outside this edition.');
  drawTable();
  const historyCodes=new Set(report.rows.map(r=>r.code));
  for (const m of edition.months.filter(m=>m<=month)) for(const c of Object.keys(data[m]||{})) historyCodes.add(c);
  options('destination',[...historyCodes].map(c=>[c,edition.countries[c]]).sort((a,b)=>a[1].localeCompare(b[1])),top?.code);
  drawSeries();
  text('edition','Data '+range(edition.months)+' · Source retrieved '+edition.retrieved+' · Nominal CAD');
}
async function update() {
  const key=by('province').value+'-'+by('product').value;
  const id=++request;
  by('result').hidden=true;
  text('edition','Loading trade values…');
  try {
    const next=cache.get(key) || await getJSON('./data/'+key+'.json');
    cache.set(key,next);
    if (id!==request) return;
    data=next;
    expanded=false;
    display();
  } catch {
    if (id===request) text('edition','Trade values could not be loaded. Reload this page or try another product.');
  }
}
function preset(province,product) {
  by('province').value=province;
  by('product').value=product;
  update();
}
by('lobster').addEventListener('click',()=>preset('NS','lobster'));
by('softwood').addEventListener('click',()=>preset('BC','softwood'));
for (const id of ['province','product','month','mode']) by(id).addEventListener('change',update);
by('destination').addEventListener('change',drawSeries);
by('more').addEventListener('click',()=>{expanded=!expanded;drawTable();});
by('download').addEventListener('click',()=>{
  const p=by('province').value,k=by('product').value;
  const rows=[['province','product','start','end','previous_start','previous_end','destination','domestic_export_CAD','share_percent','prior_CAD','prior_share_percent','change_percentage_points']];
  for (const r of report.rows) rows.push([edition.provinces[p],edition.products[k][0],periods.selected[0],periods.selected.at(-1),periods.previous[0],periods.previous.at(-1),edition.countries[r.code],r.value,r.share,report.past.countries.size?r.prior:null,r.oldShare,r.change]);
  const url=URL.createObjectURL(new Blob([csv(rows)],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a'); a.href=url; a.download=[p,k,...[periods.selected[0],periods.selected.at(-1)]].join('-')+'.csv'; a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});
try {
  edition=await getJSON('./data/edition.json');
  options('province',Object.entries(edition.provinces).sort((a,b)=>a[1].localeCompare(b[1])),'NS');
  options('product',Object.entries(edition.products).map(([id,[label]])=>[id,label]).sort((a,b)=>a[1].localeCompare(b[1])),'lobster');
  options('month',edition.months.toReversed().map(m=>[m,date(m)]),edition.months.at(-1));
  await update();
} catch {
  text('edition','The saved edition could not be loaded. Reload this page to try again.');
}
