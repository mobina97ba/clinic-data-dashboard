"""Build docs/preview.html: a static preview of the dashboard, rendered from the real package.

Run:  python build_preview.py
"""
import json
from pathlib import Path

import pandas as pd

from clinic_agent import (by_dimension, clean_data, generate_insights, monthly, repeat_patients,
                          status_counts, summarise)

BASE = Path(__file__).parent
DATASETS = {
    "clean": ("Clean sample", BASE / "sample_data" / "clinic_appointments.csv"),
    "messy": ("Messy sample", BASE / "sample_data" / "clinic_appointments_messy.csv"),
}


def records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.astype(object).where(df.notna(), None).to_json(orient="records", date_format="iso"))


def payload() -> dict:
    out = {}
    for key, (label, path) in DATASETS.items():
        r = clean_data(pd.read_csv(path))
        k, bc, bs, bm = summarise(r.clean), by_dimension(r.clean, "clinic"), \
            by_dimension(r.clean, "marketing_source"), monthly(r.clean)
        out[key] = {
            "label": label, "file": path.name, "uploaded": r.rows_uploaded, "kpis": k,
            "clinic": records(bc), "source": records(bs), "monthly": records(bm),
            "status": records(status_counts(r.clean)), "insights": generate_insights(k, bc, bs, bm, r.quality),
            "quality": r.quality, "repeat": repeat_patients(r.clean),
            "excluded": records(r.excluded[["source_row", "appointment_id", "reason"]]),
        }
    return out


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Clinic Data Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{--bg:#f4f7f8;--surface:#fff;--ink:#14232e;--muted:#5b6b77;--line:#d9e2e7;--teal:#0e7c86;--amber:#b87a0d;--rose:#b83f55;--slate:#5b7083;--plum:#7a5c9e;--soft:#e6f2f3;
box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1a21;--surface:#16252e;--ink:#e8f0f3;--muted:#9db0bb;--line:#27404d;--teal:#3fb7c2;--amber:#e0a43a;--rose:#e8758a;--slate:#8aa3b5;--plum:#b295d6;--soft:#183840;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f1a21;--surface:#16252e;--ink:#e8f0f3;--muted:#9db0bb;--line:#27404d;--teal:#3fb7c2;--amber:#e0a43a;--rose:#e8758a;--slate:#8aa3b5;--plum:#b295d6;--soft:#183840;color-scheme:dark}
*{box-sizing:border-box}html{scroll-padding-top:env(safe-area-inset-top,0px)}
body{margin:0;background:var(--bg);color:var(--ink);font:400 16px/1.55 Figtree,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1080px;margin:0 auto;padding:28px 20px 64px}
h1{font-size:clamp(1.7rem,4vw,2.4rem);line-height:1.1;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:1.15rem;margin:40px 0 12px;letter-spacing:-.01em}
.sub{color:var(--muted);margin:0;max-width:60ch}
.bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin:22px 0 8px}
.tabs{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--surface)}
.tabs button{font:inherit;font-weight:500;border:0;background:none;color:var(--muted);padding:9px 16px;cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--teal);color:#fff}
.tabs button:focus-visible,a:focus-visible{outline:3px solid var(--amber);outline-offset:-3px}
.file{color:var(--muted);font-size:.9rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));border-top:3px solid var(--teal);background:var(--surface);border-bottom:1px solid var(--line)}
.kpi{padding:16px 16px 14px;border-left:1px solid var(--line)}.kpi:first-child{border-left:0}
.kpi .l{color:var(--muted);font-size:.85rem}.kpi .v{font-size:1.9rem;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi .n{color:var(--muted);font-size:.82rem}
.note{color:var(--muted);font-size:.85rem;margin:8px 0 0;max-width:80ch}
ul.tips{margin:0;padding:0;list-style:none;display:grid;gap:8px}
ul.tips li{background:var(--surface);border-left:4px solid var(--teal);padding:10px 14px;border-radius:0 6px 6px 0}
ul.tips li.warn{border-left-color:var(--amber)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:760px){.grid{grid-template-columns:1fr}.kpi{border-left:0;border-top:1px solid var(--line)}}
.box{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px}
.box h3{margin:0 0 8px;font-size:1rem}.ch{position:relative;height:260px}
.scroll{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:.92rem}
th,td{padding:9px 12px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:500}
tr:last-child td{border-bottom:0}.bad{color:var(--rose);font-weight:500}
footer{margin-top:48px;color:var(--muted);font-size:.85rem;max-width:75ch}
</style></head><body><main>
<h1>Clinic Data Intelligence</h1>
<p class="sub">KPIs, clinic and marketing comparisons and data checks from one appointment export. This page is a static preview of the Streamlit app, built from the same Python code.</p>
<div class="bar"><div class="tabs" role="tablist" aria-label="Sample data" id="tabs"></div><span class="file" id="file"></span></div>
<div class="kpis" id="kpis"></div>
<p class="note">Outstanding is the per-visit shortfall (billed minus collected, never below zero) on completed visits. Confirm against finance rules.</p>
<h2>Automated insights</h2><ul class="tips" id="tips"></ul>
<h2>Revenue and appointments</h2>
<div class="grid"><div class="box"><h3>Revenue by clinic (AUD)</h3><div class="ch"><canvas id="c1" role="img" aria-label="Billed and collected revenue by clinic"></canvas></div></div>
<div class="box"><h3>Appointment status</h3><div class="ch"><canvas id="c2" role="img" aria-label="Appointments by status"></canvas></div></div></div>
<div class="box" style="margin-top:20px"><h3>Monthly trend (AUD)</h3><div class="ch"><canvas id="c3" role="img" aria-label="Billed and collected revenue by month"></canvas></div></div>
<h2>By clinic</h2><div class="scroll" id="t-clinic"></div>
<h2>By marketing source</h2><div class="scroll" id="t-source"></div>
<h2>Data quality</h2><div class="grid"><div class="scroll" id="t-quality"></div><div id="excl"></div></div>
<footer>Run the real app with <code>streamlit run app.py</code>. Sample data is synthetic. Use de-identified data only.</footer>
</main>
<script>
const D=__DATA__;const $=s=>document.querySelector(s);
const money=n=>'$'+Math.round(n).toLocaleString('en-AU'),pct=n=>(n*100).toFixed(1)+'%',int=n=>Number(n).toLocaleString('en-AU');
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let cur='clean',charts=[];
function table(rows,cols){if(!rows.length)return'<p class="note" style="padding:12px">No data.</p>';
return'<table><thead><tr>'+cols.map(c=>'<th>'+c[0]+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+cols.map(c=>'<td>'+c[1](r)+'</td>').join('')+'</tr>').join('')+'</tbody></table>'}
function render(){const d=D[cur],k=d.kpis,rp=d.repeat;
$('#file').textContent=d.file+' · '+d.uploaded+' rows uploaded · '+d.quality['Usable rows']+' usable';
const items=[['Appointments',int(k.appointments),''],['Completed',int(k.completed),pct(k.completion_rate)+' of bookings'],['Billed revenue',money(k.billed),'completed visits'],['Collections',money(k.collected),pct(k.collection_rate)+' of billed'],['Outstanding',money(k.outstanding),k.unpaid_visits+' visits'],['Repeat patients',rp?pct(rp.rate):'n/a',rp?rp.repeat+' of '+rp.patients:'']];
$('#kpis').innerHTML=items.map(i=>'<div class="kpi"><div class="l">'+i[0]+'</div><div class="v">'+i[1]+'</div><div class="n">'+(i[2]||'&nbsp;')+'</div></div>').join('');
$('#tips').innerHTML=d.insights.map(t=>'<li class="'+(/above|excluded|lowest|outstanding/.test(t)?'warn':'')+'">'+t+'</li>').join('');
const seg=[['Appts',r=>r.appointments],['Completed',r=>r.completed],['Cancel + no-show',r=>pct(r.lost_rate)],['Billed',r=>money(r.billed)],['Collected',r=>money(r.collected)],['Collection rate',r=>pct(r.collection_rate)]];
$('#t-clinic').innerHTML=table(d.clinic,[['Clinic',r=>r.clinic]].concat(seg));
$('#t-source').innerHTML=table(d.source,[['Source',r=>r.marketing_source]].concat(seg));
$('#t-quality').innerHTML=table(Object.entries(d.quality),[['Check',r=>r[0]],['Count',r=>'<span class="'+(r[1]>0&&!/uploaded|Usable/.test(r[0])?'bad':'')+'">'+r[1]+'</span>']]);
$('#excl').innerHTML=d.excluded.length?'<div class="scroll">'+table(d.excluded,[['File row',r=>r.source_row],['Appointment',r=>r.appointment_id||'(blank)'],['Reason',r=>'<span style="text-align:left">'+r.reason+'</span>']])+'</div><p class="note">Rows left out of every number above.</p>':'<div class="box"><h3>No rows excluded</h3><p class="note">Every uploaded row passed validation.</p></div>';
charts.forEach(c=>c.destroy());charts=[];
const ink=css('--muted'),line=css('--line'),pal=[css('--teal'),css('--amber'),css('--rose'),css('--slate'),css('--plum')];
Chart.defaults.font.family='Figtree,system-ui,sans-serif';Chart.defaults.color=ink;
const axes={x:{grid:{display:false}},y:{beginAtZero:true,grid:{color:line},ticks:{callback:v=>'$'+v.toLocaleString()}}};
const opt={responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom'}},scales:axes};
const two=(rows,key)=>({labels:rows.map(r=>r[key]),datasets:[{label:'Billed',data:rows.map(r=>r.billed),backgroundColor:pal[0]},{label:'Collected',data:rows.map(r=>r.collected),backgroundColor:pal[1]}]});
charts.push(new Chart($('#c1'),{type:'bar',data:two(d.clinic,'clinic'),options:opt}));
charts.push(new Chart($('#c2'),{type:'doughnut',data:{labels:d.status.map(s=>s.status),datasets:[{data:d.status.map(s=>s.appointments),backgroundColor:[pal[0],pal[2],pal[1],pal[3]],borderColor:css('--surface')}]},options:{responsive:true,maintainAspectRatio:false,cutout:'55%',plugins:{legend:{position:'bottom'}}}}));
const m=two(d.monthly,'month');m.datasets.forEach((s,i)=>{s.borderColor=pal[i];s.backgroundColor=pal[i];s.tension=.25;});
charts.push(new Chart($('#c3'),{type:'line',data:m,options:opt}));}
$('#tabs').innerHTML=Object.keys(D).map(k=>'<button role="tab" data-k="'+k+'" aria-selected="'+(k===cur)+'">'+D[k].label+'</button>').join('');
$('#tabs').onclick=e=>{const b=e.target.closest('button');if(!b)return;cur=b.dataset.k;document.querySelectorAll('#tabs button').forEach(x=>x.setAttribute('aria-selected',x===b));render()};
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',render);
render();
</script></body></html>"""


def main():
    html = TEMPLATE.replace("__DATA__", json.dumps(payload(), separators=(",", ":")))
    out = BASE / "docs" / "preview.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
