"""Turn the claude.ai artifact into a standalone page backed by Firebase.

Usage: python3 build.py <artifact index.html> <repo dir>
Every edit is an exact-text replacement that must match exactly once.
"""
import sys, pathlib

src, out = sys.argv[1], pathlib.Path(sys.argv[2])
s = open(src, encoding='utf-8').read()

def rep(old, new):
    global s
    n = s.count(old)
    assert n == 1, f'expected 1 match, got {n}: {old[:80]!r}'
    s = s.replace(old, new)

# 1. Firebase SDK + the shim that stands in for window.claude, before the page's own script.
SHIM = r'''<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore-compat.js"></script>
<script src="firebase-config.js"></script>
<script>
/* Stands in for the claude.ai runtime: 'db' is Firestore, 'downloads' saves a file in the browser. */
(function(){
  var db=null;
  try{
    var cfg=window.FIREBASE_CONFIG;
    if(window.firebase&&cfg&&cfg.projectId&&cfg.projectId.indexOf('PASTE')<0){
      firebase.initializeApp(cfg);
      db=firebase.firestore();
      db.settings({experimentalAutoDetectLongPolling:true,merge:true});
    } else console.error('[scores] Firebase is not configured or did not load.');
  }catch(e){ console.error('[scores] Firebase failed to start',e); db=null; }
  var dl={save:function(o){return new Promise(function(res,rej){try{
    var b=new Blob([o.data],{type:'text/csv;charset=utf-8'}),u=URL.createObjectURL(b),a=document.createElement('a');
    a.href=u;a.download=o.filename;document.body.appendChild(a);a.click();
    setTimeout(function(){URL.revokeObjectURL(u);a.remove();},1500);res();
  }catch(e){rej(e);}});}};
  window.claude={use:function(n){return Promise.resolve(n==='db'?db:n==='downloads'?dl:null);}};
})();
</script>
<script>
var DATA = '''
rep('<script>\nvar DATA = ', SHIM)

# 2. Listen to one group's scores on the group tab, and to everyone's only on the All groups tab.
rep("S.db.collection('subs').onSnapshot(onSubs,function(){});", "resub();")
rep("function onSubs(snap){", r'''var SUBQ={key:null,off:null,retry:0};
function resub(){
  if(!S.db) return;
  var key=S.tab==='all'?'all':(S.group?'g'+S.group:null);
  if(key===SUBQ.key&&SUBQ.off) return;
  if(SUBQ.off){ try{SUBQ.off();}catch(e){} SUBQ.off=null; }
  SUBQ.key=key; if(!key) return;
  var q=key==='all'?S.db.collection('subs'):S.db.collection('subs').where('group','==',S.group);
  SUBQ.off=q.onSnapshot(function(snap){ if(SUBQ.key!==key) return; SUBQ.retry=0; onSubs(snap); },
    function(e){ console.error('[scores] listener',e); if(SUBQ.key!==key) return; SUBQ.off=null; SUBQ.key=null;
      setTimeout(resub,Math.min(15000,2000*(++SUBQ.retry))); });
}
function onSubs(snap){''')
rep("S.tab=t; closePop();", "S.tab=t; closePop(); resub();")
rep("S.group=g; S.ri=null;", "S.group=g; resub(); S.ri=null;")

# 3. Messages that referred to claude.ai access.
rep("(e&&e.code==='invalid_argument')?'This page can’t save your scores with your current access. Ask the organiser for access to use the page.'",
    "(e&&(e.code==='permission-denied'||e.code==='invalid-argument'))?'Those scores couldn’t be saved. Check your name and try again, or tell your facilitator.'")
rep("The scores couldn’t be cleared with your current access.",
    "Clearing is switched off on this page. To clear, delete the subs collection in the Firebase console.")

rep("Scores can’t be submitted from this view. Open the page signed in to Claude to send them to your group.",
    "Scores can’t be sent right now. Check your connection and reload the page. If it keeps happening, tell your facilitator.")

# 4. Copy changes, 15 Oct: How it works heading and opening line.
rep("<h2 class=\"h2\"><b>You</b> at the centre</h2>", "<h2 class=\"h2\">The <b>impact</b> of a risk <b>on society</b></h2>")
rep("You are part of society like everyone else. We all depend", "We all depend")

# 5. Risk map: no dotted arcs between risks that mention each other (the in-text links stay).
rep("function setXref(src,only){\n", "function setXref(src,only){\n  src=null; // arcs between related risks switched off\n")

# 6. How it works diagram, 15 Oct: "Risk" with an exclamation mark at the centre, dotted straight
#    lines to the nine areas, and the grey Society circle grown to hold most of them.
rep("'<div class=\"yme\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\">'+PERSON+'</svg><b>You</b><span>assembly member</span></div>'",
    "'<div class=\"yme\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\" style=\"stroke-width:2.6\"><path d=\"M12 4v11\"/><path d=\"M12 19.8v.01\"/></svg><b>Risk</b></div>'")
rep('<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js">',
    '<style>\n'
    '.you .ystage{isolation:isolate}\n'
    '.you .ysoc{width:86%;z-index:-1}\n'
    '.you .ysoc span{bottom:23%}\n'
    '.you .ylines line{stroke:#2A4A78;stroke-width:2.6;stroke-dasharray:0 7;stroke-linecap:round;opacity:.8}\n'
    '</style>\n<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js">')

# 7. All groups heatmap, 23 Oct: a smooth colour scale shifted up so the 1.3-2.4 range most
#    averages fall in spreads across the colours instead of reading as all red, plus a
#    toggle to hide the numbers in the cells. Data is untouched:
#    the averages are computed exactly as before, only how they are drawn changes.
rep("function hbin(m){return HB[Math.min(5,Math.floor(m*2+1e-9))];}",
    r"""/* the heatmap scale: the six colours above, blended smoothly in OKLab and placed where the
   averages actually fall, so blue holds to about 1.1, turns yellow by 1.5 and reaches the
   darkest red at 2.7 */
var HM_POS=[1.1,1.5,1.75,2.0,2.35,2.7];
var HM_STOPS=(function(){
  function lin(c){return c<=.04045?c/12.92:Math.pow((c+.055)/1.055,2.4);}
  function lab(h){var c=[1,3,5].map(function(i){return lin(parseInt(h.substr(i,2),16)/255);}),r=c[0],g=c[1],b=c[2];
    var l=Math.cbrt(.4122214708*r+.5363325363*g+.0514459929*b),m=Math.cbrt(.2119034982*r+.6806995451*g+.1073969566*b),s=Math.cbrt(.0883024619*r+.2817188376*g+.6299787005*b);
    return [.2104542553*l+.7936177850*m-.0040720468*s,1.9779984951*l-2.4285922050*m+.4505937099*s,.0259040371*l+.7827717662*m-.8086757660*s];}
  return HB.map(function(b,i){return {v:HM_POS[i],lab:lab(b[0])};});
})();
function hmColour(m){
  function gam(c){c=Math.max(0,Math.min(1,c));return c<=.0031308?12.92*c:1.055*Math.pow(c,1/2.4)-.055;}
  function lin(c){return c<=.04045?c/12.92:Math.pow((c+.055)/1.055,2.4);}
  var a=HM_STOPS[0],b=HM_STOPS[HM_STOPS.length-1],i;
  if(m<=a.v) b=a; else if(m>=b.v) a=b; else for(i=0;i<HM_STOPS.length-1;i++) if(m<=HM_STOPS[i+1].v){a=HM_STOPS[i];b=HM_STOPS[i+1];break;}
  var t=a===b?0:(m-a.v)/(b.v-a.v), L=[0,1,2].map(function(k){return a.lab[k]+(b.lab[k]-a.lab[k])*t;});
  var l=Math.pow(L[0]+.3963377774*L[1]+.2158037573*L[2],3),mm=Math.pow(L[0]-.1055613458*L[1]-.0638541728*L[2],3),s=Math.pow(L[0]-.0894841775*L[1]-1.2914855480*L[2],3);
  var rgb=[4.0767416621*l-3.3077115913*mm+.2309699292*s,-1.2684380046*l+2.6097574011*mm-.3413193965*s,-.0041960863*l-.7034186147*mm+1.7076147010*s].map(gam);
  var Y=rgb.map(lin), y=.2126*Y[0]+.7152*Y[1]+.0722*Y[2], k=.2126*.003035+.7152*.003035+.0722*.003035;
  return ['rgb('+rgb.map(function(x){return Math.round(x*255);}).join(',')+')', (1.05/(y+.05))>((y+.05)/(k+.05))?'#FFFFFF':'#0A0A0A'];
}
function hbin(m){var c=hmColour(m);return [c[0],c[1],''];}
var HM_GRAD=(function(){var st=[];for(var v=0;v<=30;v++) st.push(hmColour(v/10)[0]+' '+(v/30*100).toFixed(1)+'%');return 'linear-gradient(90deg,'+st.join(',')+')';})();""")
# The key, a Hide numbers toggle and a Reset order button sit in the legend row.
rep("""'<div class="legend"><span>Average<span class="bins">'+HB.map(function(b){return '<i style="background:'+b[0]+';color:'+b[1]+'">'+b[2]+'</i>';}).join('')+'</span></span>""",
    """'<div class="legend"><span>Average<span class="hm-key" aria-hidden="true"><span class="hm-grad" style="background:'+HM_GRAD+'"></span><span class="hm-ticks"><i>0</i><i>1</i><i>2</i><i>3</i></span></span></span>'+
    '<span class="hm-tog"><button type="button" data-hmt="num">'+(S.hmNoNum?'Show numbers':'Hide numbers')+'</button><button type="button" data-hmt="reset"'+(S.hmByRisk||S.hmByArea?'':' disabled')+'>Reset order</button></span>""")
rep("""'<p class="swipehint">Swipe the table sideways to see all nine areas.</p>'+""",
    """'<p class="hm-hint">Click a risk to put the areas it hits hardest on the left. Click an area to put the risks that hit it hardest at the top.</p>'+
    '<p class="swipehint">Swipe the table sideways to see all nine areas.</p>'+""")

# 8. Sorting, 23 Oct: clicking a risk orders the area columns by that risk's averages, high to
#    the left; clicking an area orders the risk rows by that area's averages, high at the top.
#    Clicking the same one again, or Reset order, puts the default order back. Only the order
#    of what is drawn changes; every average is computed exactly as before.
rep("var hi={}; AREAS.forEach(function(a){hi[a.k]=",
    """var COLS=AREAS.slice(), ROWS=DATA.core.slice();
  function hmVal(c){return c&&c.m!==null?c.m:-1;}
  if(S.hmByRisk&&cell[S.hmByRisk]) COLS.sort(function(a,b){return hmVal(cell[S.hmByRisk][b.k])-hmVal(cell[S.hmByRisk][a.k]);});
  if(S.hmByArea) ROWS.sort(function(a,b){return hmVal(cell[b.id][S.hmByArea])-hmVal(cell[a.id][S.hmByArea]);});
  var hi={}; AREAS.forEach(function(a){hi[a.k]=""")
rep("""AREAS.map(function(a){return '<th scope="col"><i style="--c:'+a.c+'"><svg viewBox="0 0 24 24" aria-hidden="true">'+a.ic+'</svg></i>'+esc(a.s)+'</th>';})""",
    """COLS.map(function(a){return '<th scope="col" data-k="h-'+a.k+'"><button type="button" class="hm-sort" data-hma="'+a.k+'" aria-pressed="'+(S.hmByArea===a.k)+'" title="Put the risks that hit '+esc(a.n)+' hardest at the top"><i style="--c:'+a.c+'"><svg viewBox="0 0 24 24" aria-hidden="true">'+a.ic+'</svg></i>'+esc(a.s)+'</button></th>';})""")
rep("""DATA.core.map(function(r){return '<tr><th class="rk" scope="row">'+esc(r.t)+'</th>'+AREAS.map(function(a){var c=cell[r.id][a.k];""",
    """ROWS.map(function(r){return '<tr><th class="rk" scope="row" data-k="r-'+r.id+'"><button type="button" class="hm-sort" data-hmr="'+r.id+'" aria-pressed="'+(S.hmByRisk===r.id)+'" title="Put the areas this risk hits hardest on the left">'+esc(r.t)+'</button></th>'+COLS.map(function(a){var c=cell[r.id][a.k];""")
rep("""'<td class="none">–</td>'""", """'<td class="none" data-k="'+r.id+'-'+a.k+'">–</td>'""")
rep("""'<td style="--hc:'""", """'<td data-k="'+r.id+'-'+a.k+'" style="--hc:'""")
rep("""AREAS.map(function(a){return '<th>'+hi[a.k]+'</th>';})""", """COLS.map(function(a){return '<th data-k="f-'+a.k+'">'+hi[a.k]+'</th>';})""")
rep("/* hovering the table keeps one row and one column sharp and softens the rest */",
    r"""/* the controls live on #v-all, which is never redrawn, so their state survives every new score */
function hmReorder(resetX){
  var t=document.querySelector('#v-all table.hm'), w=document.querySelector('#v-all .hm-wrap'), x=w?w.scrollLeft:0, old={};
  if(t&&!RM) t.querySelectorAll('[data-k]').forEach(function(el){old[el.dataset.k]=el.getBoundingClientRect();});
  renderAll();
  w=document.querySelector('#v-all .hm-wrap'); if(w) w.scrollLeft=resetX?0:x;
  if(RM) return;
  var moved=[];
  document.querySelectorAll('#v-all table.hm [data-k]').forEach(function(el){
    var o=old[el.dataset.k]; if(!o) return;
    var n=el.getBoundingClientRect(), dx=o.left-n.left, dy=o.top-n.top;
    if(Math.abs(dx)<1&&Math.abs(dy)<1) return;
    el.style.transition='none'; el.style.transform='translate('+dx+'px,'+dy+'px)'; moved.push(el);
  });
  if(!moved.length) return;
  void document.body.offsetWidth;
  moved.forEach(function(el){ el.style.transition='transform .6s cubic-bezier(.2,.7,.2,1)'; el.style.transform=''; });
  setTimeout(function(){ moved.forEach(function(el){ el.style.transition=''; }); },650);
}
(function(){
  var va=document.getElementById('v-all');
  va.addEventListener('click',function(e){
    var b=e.target.closest&&e.target.closest('[data-hmt],[data-hmr],[data-hma]'); if(!b||b.disabled) return;
    if(b.dataset.hmt==='num'){ S.hmNoNum=!S.hmNoNum; va.classList.toggle('hm-nonum',S.hmNoNum); b.textContent=S.hmNoNum?'Show numbers':'Hide numbers'; return; }
    if(b.dataset.hmt==='reset'){ S.hmByRisk=null; S.hmByArea=null; hmReorder(true); return; }
    if(b.dataset.hmr){ S.hmByRisk=S.hmByRisk===b.dataset.hmr?null:b.dataset.hmr; hmReorder(true); }
    else { S.hmByArea=S.hmByArea===b.dataset.hma?null:b.dataset.hma; hmReorder(false); }
    var again=document.querySelector('#v-all [data-hmr="'+(b.dataset.hmr||'')+'"],#v-all [data-hma="'+(b.dataset.hma||'')+'"]'); if(again) again.focus({preventScroll:true});
  });
})();
/* hovering the table keeps one row and one column sharp and softens the rest */""")
rep('<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js">',
    '<style>\n'
    '.hm-key{display:inline-flex;flex-direction:column;gap:3px;vertical-align:middle;margin:0 8px;width:220px}\n'
    '.hm-grad{display:block;height:16px}\n'
    '.hm-ticks{display:flex;justify-content:space-between;font-size:12px;font-weight:700;line-height:1}\n'
    '.hm-ticks i{font-style:normal}\n'
    '.hm-tog{display:inline-flex;align-items:center;gap:6px;margin-left:auto}\n'
    '.hm-tog button{font:inherit;font-size:14px;font-weight:700;padding:5px 12px;border:2px solid var(--black);background:var(--white);color:var(--black);cursor:pointer}\n'
    '.hm-tog button:disabled{opacity:.35;cursor:default}\n'
    '.hm-hint{font-size:14px;margin-top:-4px}\n'
    '.hm-sort{display:block;width:100%;margin:0;padding:0;border:0;background:none;font:inherit;color:inherit;text-align:inherit;line-height:inherit;cursor:pointer}\n'
    '.hm-sort:hover{text-decoration:underline;text-underline-offset:3px}\n'
    '.hm thead .hm-sort[aria-pressed="true"]::after{content:"\\2193";display:block;font-size:16px;line-height:1;margin-top:2px}\n'
    '.hm th.rk .hm-sort[aria-pressed="true"]{font-weight:600}\n'
    '.hm th.rk .hm-sort[aria-pressed="true"]::after{content:" \\2192";font-family:var(--ff-sans);font-weight:700}\n'
    '#v-all.hm-nonum .hm td b,#v-all.hm-nonum .hm td small{visibility:hidden}\n'
    '</style>\n<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js">')

(out / 'index.html').write_text(s, encoding='utf-8')
print('wrote', out / 'index.html', len(s))
