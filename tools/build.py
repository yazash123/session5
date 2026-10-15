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

(out / 'index.html').write_text(s, encoding='utf-8')
print('wrote', out / 'index.html', len(s))
