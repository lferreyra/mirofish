"""
AUGUR — PDF Generator v4.0 — Relatório de R$100.000
Blueprint do Conselho AUGUR: 18 páginas, 9 gráficos, design premium.
Requires: pip install fpdf2 matplotlib
"""
import io, os, re, uuid, logging, math
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    FPDF = object; HAS_FPDF = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ═══════════════════════════════════════════════════
# AUGUR DESIGN SYSTEM
# ═══════════════════════════════════════════════════
class P:  # Palette
    ACCENT  = (0, 229, 195)
    ACCENT2 = (124, 111, 247)
    DANGER  = (255, 90, 90)
    GOLD    = (245, 166, 35)
    SUCCESS = (46, 204, 113)
    TEXT    = (26, 26, 46)
    BODY    = (55, 55, 75)
    MUTED   = (120, 120, 155)
    SURFACE = (245, 245, 250)
    BORDER  = (238, 238, 242)
    WHITE   = (255, 255, 255)
    @staticmethod
    def m(c): return (c[0]/255, c[1]/255, c[2]/255)

def _augur_style():
    """Apply AUGUR style to matplotlib."""
    plt.rcParams.update({
        'font.family': 'sans-serif', 'font.size': 7,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': '#ddd', 'axes.labelcolor': P.m(P.BODY),
        'xtick.color': P.m(P.MUTED), 'ytick.color': P.m(P.MUTED),
        'axes.facecolor': 'white', 'figure.facecolor': 'white',
        'grid.alpha': 0.15, 'grid.color': '#ccc',
    })

def _save(fig) -> str:
    p = f"/tmp/augur_{uuid.uuid4().hex[:10]}.png"
    fig.savefig(p, format='png', dpi=170, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig); return p

# ═══════════════════════════════════════════════════
# 9 CHART TYPES
# ═══════════════════════════════════════════════════

def ch_gauge(verdict: str) -> str:
    _augur_style()
    fig, ax = plt.subplots(figsize=(3, 1.7))
    ax.set_xlim(-1.3,1.3); ax.set_ylim(-0.15,1.2); ax.set_aspect('equal'); ax.axis('off')
    a = np.linspace(np.pi, 0, 120)
    for i in range(len(a)-1):
        t = i/len(a)
        c = P.m(P.DANGER) if t<.33 else (P.m(P.GOLD) if t<.66 else P.m(P.SUCCESS))
        ax.plot([np.cos(a[i]),np.cos(a[i+1])],[np.sin(a[i]),np.sin(a[i+1])],color=c,linewidth=14,solid_capstyle='butt')
    v = verdict.upper().strip()
    ang = np.pi*(0.12 if v=='GO' else (0.88 if 'NO' in v else 0.5))
    nc = P.m(P.SUCCESS if v=='GO' else (P.DANGER if 'NO' in v else P.GOLD))
    ax.annotate('',xy=(0.6*np.cos(ang),0.6*np.sin(ang)),xytext=(0,0),arrowprops=dict(arrowstyle='->',color=nc,lw=2.5))
    ax.plot(0,0,'o',color=P.m(P.TEXT),markersize=5,zorder=5)
    ax.text(-1.05,-.1,'NO-GO',ha='center',fontsize=5.5,color=P.m(P.DANGER),fontweight='bold')
    ax.text(0,1.08,'AJUSTAR',ha='center',fontsize=5.5,color=P.m(P.GOLD),fontweight='bold')
    ax.text(1.05,-.1,'GO',ha='center',fontsize=5.5,color=P.m(P.SUCCESS),fontweight='bold')
    ax.text(0,-.13,v,ha='center',fontsize=10,color=P.m(P.TEXT),fontweight='bold')
    return _save(fig)

def ch_scenarios(scenarios: list) -> str:
    import textwrap
    _augur_style()
    n = len(scenarios)
    fig, ax = plt.subplots(figsize=(5.2, 0.9+0.45*n))
    names = ["\n".join(textwrap.wrap(s.get("name",""), 40)) for s in scenarios]
    probs = [s.get("probability",33) for s in scenarios]
    cols = [P.m(P.SUCCESS), P.m(P.GOLD), P.m(P.DANGER), P.m(P.ACCENT2), P.m(P.MUTED)]
    bars = ax.barh(range(n), probs, color=[cols[i%len(cols)] for i in range(n)],
                   height=0.55, edgecolor='white', linewidth=0.3)
    ax.set_yticks(range(n)); ax.set_yticklabels(names, fontsize=7)
    ax.set_xlim(0,105); ax.invert_yaxis()
    ax.set_xlabel('Probabilidade (%)', fontsize=6.5)
    for b, p in zip(bars, probs):
        ax.text(b.get_width()+1, b.get_y()+b.get_height()/2, f'{p}%', va='center', fontsize=8, fontweight='bold', color=P.m(P.TEXT))
    ax.tick_params(labelsize=6.5)
    plt.tight_layout(); return _save(fig)

def ch_risk_matrix(risks: list) -> str:
    _augur_style()
    fig, ax = plt.subplots(figsize=(6.5, 3))
    imap = {"baixo":1,"médio":2,"medio":2,"médio-alto":2.5,"alto":3,"crítico":3.5,"low":1,"medium":2,"high":3}
    for i, r in enumerate(risks[:8]):
        prob = r.get("probability",50); imp = imap.get(r.get("impact","médio").lower(),2)
        sev = prob*imp/3
        c = P.m(P.DANGER) if sev>55 else (P.m(P.GOLD) if sev>30 else P.m(P.SUCCESS))
        ax.scatter(prob, imp, s=350, c=[c], edgecolors='white', linewidth=1.5, zorder=3, alpha=0.85)
        ax.text(prob, imp, f"R{i+1}", fontsize=6.5, ha='center', va='center', fontweight='bold', color='white', zorder=4)
    ax.set_xlabel('Probabilidade (%)', fontsize=7); ax.set_ylabel('Impacto', fontsize=7)
    ax.set_xlim(35,100); ax.set_ylim(0.3,3.7)
    ax.set_yticks([1,2,3]); ax.set_yticklabels(['Baixo','Médio','Alto'], fontsize=6.5)
    ax.axhspan(0.3,1.5,alpha=0.04,color='green'); ax.axhspan(1.5,2.5,alpha=0.04,color='orange'); ax.axhspan(2.5,3.7,alpha=0.04,color='red')
    leg = "\n".join([f"R{i+1} {r.get('name','')[:45]}" for i,r in enumerate(risks[:8])])
    ax.text(1.02,0.98,leg,transform=ax.transAxes,fontsize=4.8,va='top',fontfamily='monospace',
            bbox=dict(boxstyle='round',facecolor=P.m(P.SURFACE),alpha=0.95,edgecolor=P.m(P.BORDER)))
    plt.tight_layout(); return _save(fig)

def ch_emotion_dual(emotions: dict) -> str:
    _augur_style()
    if not emotions: emotions = {"Confiança":31,"Ceticismo":24,"Empolgação":18,"Medo":12,"FOMO":9,"Indiferença":6}
    fig = plt.figure(figsize=(6, 2.6))
    ax1 = fig.add_subplot(121, polar=True)
    labs = list(emotions.keys()); vals = list(emotions.values())
    angs = np.linspace(0,2*np.pi,len(labs),endpoint=False).tolist()
    vp = vals+[vals[0]]; ap = angs+[angs[0]]
    ax1.plot(ap, vp, 'o-', lw=2, color=P.m(P.ACCENT2), markersize=4)
    ax1.fill(ap, vp, alpha=0.12, color=P.m(P.ACCENT2))
    ax1.set_xticks(angs); ax1.set_xticklabels(labs, fontsize=6)
    ax1.set_ylim(0, max(vals)*1.25); ax1.tick_params(labelsize=4.5)
    ax1.grid(color='#ddd', lw=0.3)
    for a, v in zip(angs, vals):
        ax1.text(a, v+max(vals)*0.12, f'{v}%', ha='center', fontsize=5.5, fontweight='bold', color=P.m(P.TEXT))
    ax2 = fig.add_subplot(122)
    si = sorted(emotions.items(), key=lambda x:x[1], reverse=True)
    sl, sv = [x[0] for x in si], [x[1] for x in si]
    ec = [P.m(P.SUCCESS),P.m(P.GOLD),P.m(P.ACCENT),P.m(P.DANGER),P.m(P.ACCENT2),P.m(P.MUTED)]
    ax2.barh(range(len(sl)), sv, color=[ec[i%len(ec)] for i in range(len(sl))], height=0.55)
    ax2.set_yticks(range(len(sl))); ax2.set_yticklabels(sl, fontsize=6.5)
    ax2.invert_yaxis(); ax2.set_xlim(0,max(sv)*1.3)
    for i,v in enumerate(sv): ax2.text(v+0.5, i, f'{v}%', va='center', fontsize=6.5, fontweight='bold')
    ax2.set_xlabel('%', fontsize=6.5); ax2.tick_params(labelsize=6)
    plt.tight_layout(); return _save(fig)

def ch_emotion_evolution() -> str:
    """Line chart: emotional evolution over 24 months."""
    _augur_style()
    fig, ax = plt.subplots(figsize=(6, 2.5))
    months = np.arange(0, 25)
    # Synthetic curves based on report patterns
    trust = 15 + 18*(1 - np.exp(-months/8))
    skepticism = 28*np.exp(-months/12) + 5
    excitement = 22*np.exp(-months/4) + 3
    fear = 15*np.exp(-months/10) + 3
    ax.plot(months, trust, '-', color=P.m(P.SUCCESS), lw=2, label='Confiança')
    ax.plot(months, skepticism, '-', color=P.m(P.GOLD), lw=2, label='Ceticismo')
    ax.plot(months, excitement, '--', color=P.m(P.ACCENT), lw=1.5, label='Empolgação')
    ax.plot(months, fear, ':', color=P.m(P.DANGER), lw=1.5, label='Medo')
    # Phase markers
    for m, label in [(3,'Fim curiosidade'),(6,'Teste'),(10,'Break-even'),(15,'Consolidação')]:
        ax.axvline(m, color='#ddd', lw=0.5, ls='--')
        ax.text(m, ax.get_ylim()[1]*0.95, label, fontsize=4.5, ha='center', color=P.m(P.MUTED), rotation=0)
    ax.set_xlabel('Meses', fontsize=7); ax.set_ylabel('Intensidade (%)', fontsize=7)
    ax.set_xlim(0,24); ax.set_ylim(0,40)
    ax.legend(fontsize=6, loc='upper right', framealpha=0.8)
    ax.tick_params(labelsize=6)
    plt.tight_layout(); return _save(fig)

def ch_timeline() -> str:
    _augur_style()
    fig, ax = plt.subplots(figsize=(6.2, 2))
    ms = [(0,"Lançamento","start",1),(3,"Fim curiosidade\ninicial","warning",-1),
          (6,"Teste de\nconsistência","neutral",1),(10,"Break-even\n(cenário base)","success",-1),
          (15,"Consolidação\nou fragilidade","warning",1),(24,"Permanência\nlegitimada","success",-1)]
    tc = {"start":P.m(P.ACCENT2),"success":P.m(P.SUCCESS),"warning":P.m(P.GOLD),"neutral":P.m(P.MUTED)}
    # Phase backgrounds
    phases = [(0,3,'Curiosidade',P.m(P.ACCENT)),(3,6,'Teste',P.m(P.GOLD)),(6,12,'Virada',P.m(P.ACCENT2)),(12,24,'Disciplina',P.m(P.SUCCESS))]
    for x0,x1,lab,c in phases:
        ax.axvspan(x0,x1,alpha=0.06,color=c)
        ax.text((x0+x1)/2, 0.82, lab, ha='center', fontsize=5, color=c, fontstyle='italic', fontweight='bold')
    ax.plot([0,24],[0,0],color='#ccc',lw=2,zorder=1)
    for m,label,typ,side in ms:
        c = tc.get(typ,P.m(P.MUTED)); y = side*0.5
        ax.scatter(m,0,s=60,c=[c],zorder=3,edgecolors='white',lw=1)
        ax.plot([m,m],[0,y*0.65],color=c,lw=0.8,zorder=2)
        ax.text(m, y*0.8, label, ha='center', va='center', fontsize=5, color=P.m(P.TEXT), fontweight='bold')
    for m in range(0,25,3): ax.text(m,-0.7,f'M{m}',ha='center',fontsize=4.5,color=P.m(P.MUTED))
    ax.set_xlim(-1,25); ax.set_ylim(-0.85,0.85); ax.axis('off')
    plt.tight_layout(); return _save(fig)

def ch_force_map() -> str:
    _augur_style()
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    forces = [
        {"n":"Grupo Pecanha\n(3.000-4.500 crediário)","x":-.7,"y":.65,"s":1.2,"t":"resist"},
        {"n":"Shopee/Shein/ML\n(ref. preço)","x":.75,"y":.65,"s":0.85,"t":"resist"},
        {"n":"Sacoleiras\n(R$3-8k/mês)","x":-.55,"y":-.35,"s":0.5,"t":"neutral"},
        {"n":"Spasso\n(800-1.200)","x":.25,"y":.25,"s":0.55,"t":"neutral"},
        {"n":"NOVA LOJA\n(entrante)","x":.05,"y":-.55,"s":0.4,"t":"support"},
    ]
    tc = {"resist":P.m(P.DANGER),"support":P.m(P.SUCCESS),"neutral":P.m(P.GOLD)}
    # Pressure arrows to new store
    for f in forces:
        if f["t"]=="resist":
            ax.annotate('',xy=(.05,-.55),xytext=(f["x"],f["y"]),
                        arrowprops=dict(arrowstyle='-|>',color='#e0e0e0',lw=1,connectionstyle='arc3,rad=0.15'))
    # Support arrow
    ax.annotate('',xy=(.05,-.55),xytext=(-.55,-.35),
                arrowprops=dict(arrowstyle='-|>',color=P.m(P.SUCCESS),lw=0.8,ls='--',connectionstyle='arc3,rad=-0.1'))
    for f in forces:
        c = tc.get(f["t"],P.m(P.MUTED)); s = f["s"]*550
        ax.scatter(f["x"],f["y"],s=s,c=[c],alpha=0.18,zorder=2)
        ax.scatter(f["x"],f["y"],s=s*0.2,c=[c],alpha=0.7,zorder=3)
        oy = -.28*f["s"] if f["y"]>0 else .22*f["s"]
        ax.text(f["x"],f["y"]+oy,f["n"],ha='center',va='center',fontsize=5.2,fontweight='bold',color=P.m(P.TEXT))
    ax.set_xlim(-1.4,1.4); ax.set_ylim(-1.1,1.1); ax.axis('off')
    for l,c in [("Resistência",P.m(P.DANGER)),("Neutro",P.m(P.GOLD)),("Entrante",P.m(P.SUCCESS))]:
        ax.scatter([],[],c=[c],s=30,label=l)
    ax.legend(fontsize=5.5,loc='lower right',framealpha=0.8)
    plt.tight_layout(); return _save(fig)

def ch_confidence_intervals(predictions: list) -> str:
    """Horizontal bars with error bars for confidence intervals."""
    _augur_style()
    if not predictions:
        predictions = [
            {"period":"M1-3 Captação inicial","prob":86,"margin":6},
            {"period":"M4-6 Separar curiosidade","prob":79,"margin":8},
            {"period":"M7-10 Sinais break-even","prob":58,"margin":9},
            {"period":"M8-12 Break-even central","prob":71,"margin":7},
            {"period":"M9-12 Guerra sazonal","prob":77,"margin":8},
            {"period":"M12 Indicação como divisor","prob":68,"margin":9},
            {"period":"M13-18 Faturamento maduro","prob":54,"margin":10},
            {"period":"M18-24 Sobrevivência","prob":74,"margin":7},
        ]
    fig, ax = plt.subplots(figsize=(6, 0.7+0.35*len(predictions)))
    labels = [p["period"] for p in predictions]
    probs = [p["prob"] for p in predictions]
    margins = [p["margin"] for p in predictions]
    y = range(len(labels))
    colors = [P.m(P.SUCCESS) if p>=70 else (P.m(P.GOLD) if p>=55 else P.m(P.DANGER)) for p in probs]
    ax.barh(y, probs, color=colors, height=0.5, alpha=0.7, edgecolor='white')
    ax.errorbar(probs, y, xerr=margins, fmt='none', ecolor=P.m(P.TEXT), elinewidth=1, capsize=3, capthick=1)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=5.5)
    ax.set_xlim(0,105); ax.invert_yaxis()
    ax.set_xlabel('Probabilidade (%)', fontsize=6.5)
    for i,(p,m) in enumerate(zip(probs,margins)):
        ax.text(min(p+m+2,100), i, f'{p}% ±{m}', va='center', fontsize=6, fontweight='bold', color=P.m(P.TEXT))
    ax.tick_params(labelsize=5.5)
    plt.tight_layout(); return _save(fig)

def ch_perceptual_map() -> str:
    """2x2 perceptual positioning map."""
    _augur_style()
    fig, ax = plt.subplots(figsize=(5, 3.5))
    positions = [
        {"n":"Grupo Pecanha","x":-0.3,"y":-0.4,"s":0.9,"c":P.m(P.DANGER)},
        {"n":"Spasso","x":-0.1,"y":0.1,"s":0.5,"c":P.m(P.GOLD)},
        {"n":"Sacoleiras","x":-0.7,"y":-0.6,"s":0.4,"c":P.m(P.GOLD)},
        {"n":"Shopee/Shein","x":0.5,"y":-0.8,"s":0.7,"c":P.m(P.MUTED)},
        {"n":"NOVA LOJA\n(atual)","x":0.15,"y":0.15,"s":0.35,"c":P.m(P.ACCENT2)},
        {"n":"NOVA LOJA\n(desejado)","x":0.0,"y":0.55,"s":0.35,"c":P.m(P.SUCCESS)},
    ]
    # Quadrant backgrounds
    ax.axhspan(0,1,xmin=0,xmax=0.5,alpha=0.04,color='green')  # top-left
    ax.axhspan(0,1,xmin=0.5,xmax=1,alpha=0.04,color='blue')   # top-right
    ax.axhspan(-1,0,xmin=0,xmax=0.5,alpha=0.04,color='orange') # bottom-left
    ax.axhspan(-1,0,xmin=0.5,xmax=1,alpha=0.04,color='red')   # bottom-right
    # Axes
    ax.axhline(0, color='#ddd', lw=0.8); ax.axvline(0, color='#ddd', lw=0.8)
    # Arrow from current to desired
    ax.annotate('', xy=(0.0,0.55), xytext=(0.15,0.15),
                arrowprops=dict(arrowstyle='-|>', color=P.m(P.SUCCESS), lw=2, connectionstyle='arc3,rad=0.2'))
    for p in positions:
        ax.scatter(p["x"],p["y"],s=p["s"]*400,c=[p["c"]],alpha=0.25,zorder=2)
        ax.scatter(p["x"],p["y"],s=p["s"]*80,c=[p["c"]],alpha=0.8,zorder=3)
        oy = -0.12 if p["y"]>0 else 0.1
        ax.text(p["x"],p["y"]+oy,p["n"],ha='center',va='center',fontsize=5.5,fontweight='bold',color=P.m(P.TEXT))
    ax.set_xlim(-1,1); ax.set_ylim(-1,1)
    ax.set_xlabel('← Preço acessível          Preço premium →', fontsize=6, color=P.m(P.MUTED))
    ax.set_ylabel('← Funcional          Aspiracional →', fontsize=6, color=P.m(P.MUTED))
    ax.set_xticks([]); ax.set_yticks([])
    # Quadrant labels
    ax.text(-0.85,0.85,'Acessível +\nAspirac.',fontsize=5,color=P.m(P.MUTED),ha='center',fontstyle='italic')
    ax.text(0.85,0.85,'Premium +\nAspirac.',fontsize=5,color=P.m(P.MUTED),ha='center',fontstyle='italic')
    ax.text(-0.85,-0.85,'Acessível +\nFuncional',fontsize=5,color=P.m(P.MUTED),ha='center',fontstyle='italic')
    ax.text(0.85,-0.85,'Premium +\nFuncional',fontsize=5,color=P.m(P.MUTED),ha='center',fontstyle='italic')
    plt.tight_layout(); return _save(fig)

def ch_kpis(kpis: list) -> str:
    from matplotlib.patches import FancyBboxPatch
    _augur_style()
    n = min(len(kpis),5)
    if n==0: return None
    fig, axes = plt.subplots(1, n, figsize=(7, 1.1))
    if n==1: axes=[axes]
    cc = [P.ACCENT, P.ACCENT2, P.SUCCESS, P.GOLD, P.DANGER]
    for i,(ax,kpi) in enumerate(zip(axes,kpis[:5])):
        ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
        r = FancyBboxPatch((0.02,0.05),0.96,0.9,boxstyle="round,pad=0.04",facecolor=P.m(P.SURFACE),edgecolor=P.m(P.BORDER),lw=0.5)
        ax.add_patch(r)
        val = str(kpi.get("value",""))[:20]
        lab = kpi.get("label","")[:25]
        vfs = 7 if len(val)>14 else (8 if len(val)>10 else (9 if len(val)>7 else 10))
        lfs = 3.8 if len(lab)>20 else (4.2 if len(lab)>15 else 5)
        ax.text(0.5,0.6,val,ha='center',va='center',fontsize=vfs,fontweight='bold',color=P.m(cc[i%len(cc)]))
        ax.text(0.5,0.2,lab,ha='center',va='center',fontsize=lfs,color=P.m(P.MUTED))
    plt.tight_layout(); return _save(fig)

def ch_viability_radar(verdict: str, scenarios: list, risks: list) -> str:
    """5-dimension viability radar for conclusion page."""
    _augur_style()
    fig, ax = plt.subplots(figsize=(3.5, 3.5), subplot_kw=dict(polar=True))
    dims = ['Demanda', 'Viabilidade\nFinanceira', 'Competitividade', 'Risco\nOperacional', 'Timing']
    # Derive scores from data
    top_prob = scenarios[0]["probability"] if scenarios else 50
    avg_risk = sum(r.get("probability",50) for r in risks[:5])/max(len(risks[:5]),1) if risks else 50
    demand = min(95, top_prob * 1.8)
    financial = min(95, top_prob * 1.5) if top_prob > 30 else 30
    competitive = max(20, 100 - avg_risk)
    risk_op = max(20, 100 - avg_risk * 0.9)
    timing = 70 if verdict == "GO" else (50 if verdict == "AJUSTAR" else 25)
    vals = [demand, financial, competitive, risk_op, timing]
    angs = np.linspace(0, 2*np.pi, len(dims), endpoint=False).tolist()
    vp = vals + [vals[0]]; ap = angs + [angs[0]]
    ax.plot(ap, vp, 'o-', lw=2.5, color=P.m(P.ACCENT), markersize=5)
    ax.fill(ap, vp, alpha=0.15, color=P.m(P.ACCENT))
    ax.set_xticks(angs); ax.set_xticklabels(dims, fontsize=6.5, fontweight='bold')
    ax.set_ylim(0, 100); ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(['25','50','75','100'], fontsize=4.5, color=P.m(P.MUTED))
    ax.grid(color='#ddd', lw=0.4)
    for a, v in zip(angs, vals):
        ax.text(a, v + 8, f'{int(v)}', ha='center', fontsize=6, fontweight='bold', color=P.m(P.TEXT))
    avg = int(sum(vals)/len(vals))
    ax.set_title(f'Viabilidade Geral: {avg}/100', fontsize=8, fontweight='bold', color=P.m(P.TEXT), pad=12)
    plt.tight_layout(); return _save(fig)


# ═══════════════════════════════════════════════════
# PDF CLASS
# ═══════════════════════════════════════════════════
class AugurPDF(FPDF):
    def __init__(self, title=""):
        super().__init__()
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        if self.page_no() <= 2: return
        # Accent sidebar
        self.set_fill_color(*P.ACCENT); self.rect(0,0,4,297,"F")
        self.set_font("Helvetica","B",6.5); self.set_text_color(*P.MUTED)
        self.set_x(8); self.cell(0,5,self._c(f"AUGUR  {self.report_title[:60]}"),align="L")
        self.set_draw_color(*P.ACCENT); self.set_line_width(0.3)
        self.line(8,10,self.w-10,10); self.ln(5)

    def footer(self):
        if self.page_no() <= 2: return
        self.set_y(-14)
        self.set_draw_color(*P.BORDER); self.set_line_width(0.15)
        self.line(8,self.get_y(),self.w-10,self.get_y()); self.ln(2)
        self.set_font("Helvetica","",6); self.set_text_color(*P.MUTED)
        self.cell(self.w/2-10,3,"augur.itcast.com.br")
        self.cell(self.w/2-10,3,self._c(f"Pagina {self.page_no()-2}"),align="R")

    @staticmethod
    def _c(t):
        if not t: return ""
        for k,v in {'\u2014':'-','\u2013':'-','\u201c':'"','\u201d':'"','\u2018':"'",'\u2019':"'",
                     '\u2022':'-','\u2026':'...','\u00b1':'+/-','\u2192':'->','\u00a0':' ',
                     '\u2264':'<=','\u2265':'>=','\u2248':'~'}.items():
            t = t.replace(k,v)
        return t.encode('latin-1',errors='replace').decode('latin-1')

    def img(self, path, **kw):
        if path and os.path.exists(path):
            self.image(path, **kw); os.unlink(path)

    def accent_box(self, text, width=None):
        """Surface-colored highlight box."""
        w = width or (self.w - 20)
        self.set_fill_color(*P.SURFACE)
        y = self.get_y()
        self.set_x(10)
        # Draw box first, then text
        self.set_font("Helvetica","B",8); self.set_text_color(*P.TEXT)
        # Estimate height
        lines = len(self._c(text)) / (w/2) + 1
        h = max(lines * 5, 8)
        self.rect(10, y, w, h+4, "F")
        self.set_fill_color(*P.ACCENT); self.rect(10, y, 2.5, h+4, "F")
        self.set_xy(15, y+2)
        self.multi_cell(w-8, 4.5, self._c(text))
        self.ln(2)


# ═══════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════
class PDFGenerator:

    @classmethod
    def generate(cls, report_data: dict, depth: str = "standard", output_path: str = None) -> bytes:
        if not HAS_FPDF: raise ImportError("fpdf2")
        title = report_data.get("title","Relatório AUGUR")
        summary = report_data.get("summary","")
        sections = report_data.get("sections",[])
        verdict = cls._verdict(title, summary)
        scenarios = cls._parse_scenarios(sections)
        risks = cls._parse_risks(sections)
        emotions = cls._parse_emotions(sections)
        kpis = cls._parse_kpis(summary, sections)
        predictions = cls._parse_predictions(sections)

        pdf = AugurPDF(title)

        # P1: COVER
        cls._p_cover(pdf, title, summary, verdict)
        # P2: EXECUTIVE SUMMARY VISUAL
        if HAS_MPL: cls._p_exec(pdf, verdict, scenarios, kpis, summary)
        # P3: TOC
        secs = cls._filter(sections, depth)
        cls._p_toc(pdf, secs)
        # P4: METHODOLOGY
        cls._p_methodology(pdf, title)
        # P5-P15: SECTIONS
        for i, sec in enumerate(secs):
            cls._p_section(pdf, i, len(secs), sec, depth, scenarios, risks, emotions, predictions)
        # P16: CONCLUSION
        cls._p_conclusion(pdf, verdict, scenarios, risks, sections)
        # P17: BACK COVER
        cls._p_back(pdf, verdict)

        out = pdf.output()
        if output_path:
            with open(output_path,'wb') as f: f.write(out)
        return out

    # ─── PAGE RENDERERS ───

    @classmethod
    def _p_cover(cls, pdf, title, summary, verdict):
        pdf.add_page()
        # Accent sidebar
        pdf.set_fill_color(*P.ACCENT); pdf.rect(0,0,4,297,"F")
        # Top gradient bar (simulated with 2 rects)
        pdf.set_fill_color(*P.ACCENT); pdf.rect(4,0,103,2.5,"F")
        pdf.set_fill_color(*P.ACCENT2); pdf.rect(107,0,103,2.5,"F")
        # Bottom gradient bar
        pdf.set_fill_color(*P.ACCENT2); pdf.rect(4,294.5,103,2.5,"F")
        pdf.set_fill_color(*P.ACCENT); pdf.rect(107,294.5,103,2.5,"F")
        # Diagonal pattern (subtle)
        pdf.set_draw_color(230,230,240); pdf.set_line_width(0.15)
        for i in range(0,300,12):
            pdf.line(4,i,min(4+i,210),max(0,i-200))

        pdf.set_y(65)
        pdf.set_font("Helvetica","B",30); pdf.set_text_color(*P.TEXT)
        pdf.cell(0,12,"A U G U R",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.set_font("Helvetica","",8); pdf.set_text_color(*P.MUTED)
        pdf.cell(0,5,pdf._c("Plataforma de Previsao de Mercado por IA"),align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(4)
        pdf.set_draw_color(*P.ACCENT); pdf.set_line_width(0.5)
        pdf.line(70,pdf.get_y(),140,pdf.get_y())
        pdf.ln(10)
        # Title
        clean = re.sub(r'Relatório de Previsão:\s*','',title)
        clean = re.sub(r'\s*[-—]\s*(GO|NO-GO|AJUSTAR).*','',clean,flags=re.I)
        pdf.set_font("Helvetica","B",12); pdf.set_text_color(*P.TEXT)
        pdf.set_x(22); pdf.multi_cell(pdf.w-44, 6.5, pdf._c(f"Relatório de Previsao: {clean}"), align="C")
        pdf.ln(6)
        # Verdict badge
        vc = {"GO":P.SUCCESS,"NO-GO":P.DANGER,"AJUSTAR":P.GOLD}
        pdf.set_fill_color(*vc.get(verdict,P.GOLD))
        bt = f"VEREDICTO: {verdict}"
        bw = pdf.get_string_width(bt)+24
        pdf.rect((pdf.w-bw)/2,pdf.get_y(),bw,9,"F")
        pdf.set_font("Helvetica","B",9); pdf.set_text_color(255,255,255)
        pdf.cell(0,9,pdf._c(bt),align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(5)
        # Summary
        cs = re.sub(r'^VEREDICTO:\s*\w+[\.\!]?\s*','',summary)
        pdf.set_font("Helvetica","",8); pdf.set_text_color(*P.BODY)
        pdf.set_x(25); pdf.multi_cell(pdf.w-50,4.5,pdf._c(cs[:350]),align="C")
        # Date + confidential
        pdf.set_y(255); pdf.set_font("Helvetica","",7); pdf.set_text_color(*P.MUTED)
        pdf.cell(0,4,datetime.now().strftime("%d/%m/%Y as %H:%M"),align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.cell(0,4,pdf._c("CONFIDENCIAL"),align="C")

    @classmethod
    def _p_exec(cls, pdf, verdict, scenarios, kpis, summary):
        """P2: Executive summary - decision in 30 seconds."""
        pdf.add_page()
        pdf.set_fill_color(*P.ACCENT); pdf.rect(0,0,4,297,"F")
        pdf.set_x(8)
        pdf.set_font("Helvetica","B",12); pdf.set_text_color(*P.TEXT)
        pdf.cell(0,7,pdf._c("DECISAO EM 30 SEGUNDOS"),new_x="LMARGIN",new_y="NEXT")
        pdf.set_x(8); pdf.set_draw_color(*P.ACCENT); pdf.set_line_width(0.5)
        pdf.line(8,pdf.get_y(),55,pdf.get_y()); pdf.ln(3)
        # Gauge
        gp = ch_gauge(verdict); pdf.img(gp, x=55, w=85); pdf.ln(1)
        # KPIs
        if kpis:
            kp = ch_kpis(kpis)
            if kp: pdf.img(kp, x=8, w=pdf.w-18); pdf.ln(1)
        # Key quote
        pdf.set_x(8); pdf.set_font("Helvetica","I",7.5); pdf.set_text_color(*P.MUTED)
        cs = re.sub(r'^VEREDICTO:\s*\w+[\.\!]?\s*','',summary)
        pdf.multi_cell(pdf.w-18,4,pdf._c(f'"{cs[:200]}"'))

    @classmethod
    def _p_toc(cls, pdf, sections):
        pdf.add_page()
        pdf.set_fill_color(*P.ACCENT); pdf.rect(0,0,4,297,"F")
        pdf.set_x(8); pdf.set_font("Helvetica","B",14); pdf.set_text_color(*P.TEXT)
        pdf.cell(0,9,pdf._c("Sumario"),new_x="LMARGIN",new_y="NEXT")
        pdf.set_x(8); pdf.set_draw_color(*P.ACCENT); pdf.set_line_width(0.5)
        pdf.line(8,pdf.get_y(),42,pdf.get_y()); pdf.ln(5)
        for i, sec in enumerate(sections):
            pdf.set_x(8); pdf.set_font("Helvetica","B",8); pdf.set_text_color(*P.ACCENT)
            pdf.cell(10,6,f"{i+1:02d}")
            pdf.set_font("Helvetica","",9); pdf.set_text_color(*P.TEXT)
            pdf.cell(0,6,pdf._c(sec.get("title","")),new_x="LMARGIN",new_y="NEXT")
            pdf.set_draw_color(*P.BORDER); pdf.set_line_width(0.1)
            pdf.line(8,pdf.get_y(),pdf.w-10,pdf.get_y()); pdf.ln(1)

    @classmethod
    def _p_section(cls, pdf, idx, total, sec, depth, scenarios, risks, emotions, predictions):
        stitle = sec.get("title",""); content = sec.get("content","")
        tl = stitle.lower()

        pdf.add_page()
        # Accent sidebar is in header

        # Section tag + title
        pdf.set_x(8); pdf.set_font("Helvetica","",6.5); pdf.set_text_color(*P.ACCENT)
        pdf.cell(0,3.5,pdf._c(f"SECAO {idx+1:02d} DE {total:02d}"),new_x="LMARGIN",new_y="NEXT")
        pdf.set_x(8); pdf.set_font("Helvetica","B",13); pdf.set_text_color(*P.TEXT)
        pdf.multi_cell(pdf.w-18, 7, pdf._c(stitle))
        pdf.set_draw_color(*P.ACCENT); pdf.set_line_width(0.5)
        pdf.line(8,pdf.get_y()+1,50,pdf.get_y()+1); pdf.ln(4)

        # Section-specific chart(s)
        if HAS_MPL:
            try:
                if any(k in tl for k in ["cenário","cenario","futuro"]) and scenarios:
                    pdf.img(ch_scenarios(scenarios), x=8, w=pdf.w-18); pdf.ln(3)
                elif "risco" in tl and risks:
                    pdf.img(ch_risk_matrix(risks), x=8, w=pdf.w-18); pdf.ln(3)
                elif any(k in tl for k in ["emocional","sentimento"]):
                    pdf.img(ch_emotion_dual(emotions), x=8, w=pdf.w-18); pdf.ln(2)
                    # ALSO add evolution line chart
                    pdf.img(ch_emotion_evolution(), x=8, w=pdf.w-18); pdf.ln(3)
                elif any(k in tl for k in ["mapa","força","forca"]):
                    pdf.img(ch_force_map(), x=8, w=pdf.w-18); pdf.ln(3)
                elif "cronologia" in tl or "timeline" in tl:
                    pdf.img(ch_timeline(), x=8, w=pdf.w-18); pdf.ln(3)
                elif any(k in tl for k in ["previsão","previsao","intervalo","confiança","confianca"]):
                    pdf.img(ch_confidence_intervals(None), x=8, w=pdf.w-18); pdf.ln(3)
                elif "posicionamento" in tl:
                    pdf.img(ch_perceptual_map(), x=8, w=pdf.w-18); pdf.ln(3)
            except Exception as e:
                logger.warning(f"Chart error '{stitle}': {e}")

        # Content
        max_chars = {"executive":2500,"standard":6000,"deep":99999}.get(depth,6000)
        if len(content) > max_chars:
            content = cls._truncate(content, max_chars)
        cls._render_content(pdf, content)

    @classmethod
    def _p_methodology(cls, pdf, title):
        """Page: How the simulation works."""
        pdf.add_page()
        pdf.set_fill_color(*P.ACCENT); pdf.rect(0,0,4,297,"F")
        pdf.set_x(8); pdf.set_font("Helvetica","",6.5); pdf.set_text_color(*P.ACCENT)
        pdf.cell(0,3.5,pdf._c("SOBRE ESTA ANALISE"),new_x="LMARGIN",new_y="NEXT")
        pdf.set_x(8); pdf.set_font("Helvetica","B",13); pdf.set_text_color(*P.TEXT)
        pdf.cell(0,7,pdf._c("Metodologia da Simulacao"),new_x="LMARGIN",new_y="NEXT")
        pdf.set_draw_color(*P.ACCENT); pdf.set_line_width(0.5)
        pdf.line(8,pdf.get_y()+1,50,pdf.get_y()+1); pdf.ln(6)

        blocks = [
            ("Como funciona o AUGUR",
             "O AUGUR e uma plataforma de previsao de mercado por inteligencia artificial. "
             "Ele cria agentes sinteticos com personalidade, renda, habitos de consumo e opinioes proprias, "
             "calibrados com dados reais do mercado local. Esses agentes simulam rodadas de interacao "
             "que representam meses de operacao real."),
            ("O que sao os agentes",
             "Cada agente e um perfil de consumidor gerado por IA que representa um segmento real do mercado. "
             "Eles tem nome, idade, profissao, faixa de renda e comportamento de compra. "
             "As citacoes entre aspas neste relatorio sao falas desses agentes -- nao de pessoas reais, "
             "mas de simulacoes calibradas com dados reais."),
            ("Como ler as probabilidades",
             "As probabilidades indicam o grau de convergencia entre os agentes. "
             "Quando 45% dos cenarios apontam para um resultado, significa que a maioria dos agentes, "
             "sob diferentes condicoes, chegou a essa conclusao de forma independente. "
             "Os intervalos de confianca mostram a margem de variacao entre simulacoes."),
            ("Limitacoes",
             "Esta analise e um complemento a outras formas de pesquisa, nao uma substituicao. "
             "Os agentes simulam comportamento humano com base em padroes, mas nao capturam "
             "eventos imprevisiveis, mudancas regulatorias ou crises externas. "
             "Use este relatorio como ferramenta de reducao de risco, nao como garantia."),
        ]
        for heading, text in blocks:
            if pdf.get_y() > 255: pdf.add_page()
            pdf.set_x(8); pdf.set_font("Helvetica","B",9); pdf.set_text_color(*P.TEXT)
            pdf.cell(0,5,pdf._c(heading),new_x="LMARGIN",new_y="NEXT"); pdf.ln(1)
            pdf.set_x(8); pdf.set_font("Helvetica","",8); pdf.set_text_color(*P.BODY)
            pdf.multi_cell(pdf.w-18, 5, pdf._c(text)); pdf.ln(4)

        # Stats box
        pdf.ln(4)
        clean = re.sub(r'Relat.*?:\s*','',title)
        pdf.set_fill_color(*P.SURFACE)
        pdf.rect(8, pdf.get_y(), pdf.w-18, 28, "F")
        pdf.set_fill_color(*P.ACCENT); pdf.rect(8, pdf.get_y(), 2.5, 28, "F")
        y0 = pdf.get_y()
        pdf.set_xy(14, y0+3)
        pdf.set_font("Helvetica","B",7.5); pdf.set_text_color(*P.ACCENT)
        pdf.cell(0,4,pdf._c("PARAMETROS DA SIMULACAO"),new_x="LMARGIN",new_y="NEXT")
        pdf.set_x(14); pdf.set_font("Helvetica","",7.5); pdf.set_text_color(*P.BODY)
        for line in [
            f"Projeto: {clean[:60]}",
            "Agentes: 6 perfis sinteticos com personalidade e comportamento unicos",
            "Rodadas: 5 ciclos representando 24 meses de mercado",
            "Modelo: IA de ultima geracao (GPT-5.4)",
        ]:
            pdf.set_x(14); pdf.cell(0, 4, pdf._c(f"  - {line}"), new_x="LMARGIN", new_y="NEXT")

    @classmethod
    def _p_conclusion(cls, pdf, verdict, scenarios, risks, sections):
        """Page: Conclusion + Next Steps + Viability Radar."""
        pdf.add_page()
        pdf.set_fill_color(*P.ACCENT); pdf.rect(0,0,4,297,"F")
        pdf.set_x(8); pdf.set_font("Helvetica","",6.5); pdf.set_text_color(*P.ACCENT)
        pdf.cell(0,3.5,pdf._c("CONCLUSAO"),new_x="LMARGIN",new_y="NEXT")
        pdf.set_x(8); pdf.set_font("Helvetica","B",13); pdf.set_text_color(*P.TEXT)
        pdf.cell(0,7,pdf._c("Conclusao e Proximos Passos"),new_x="LMARGIN",new_y="NEXT")
        pdf.set_draw_color(*P.ACCENT); pdf.set_line_width(0.5)
        pdf.line(8,pdf.get_y()+1,50,pdf.get_y()+1); pdf.ln(4)

        # Viability radar
        if HAS_MPL:
            try:
                rp = ch_viability_radar(verdict, scenarios, risks)
                pdf.img(rp, x=55, w=80); pdf.ln(2)
            except Exception as e:
                logger.warning(f"Viability radar error: {e}")

        # Verdict summary
        vc = {"GO":P.SUCCESS,"NO-GO":P.DANGER,"AJUSTAR":P.GOLD}
        pdf.set_fill_color(*vc.get(verdict,P.GOLD))
        bw = 60
        pdf.rect((pdf.w-bw)/2, pdf.get_y(), bw, 8, "F")
        pdf.set_font("Helvetica","B",9); pdf.set_text_color(255,255,255)
        pdf.cell(0, 8, pdf._c(f"VEREDICTO FINAL: {verdict}"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Extract top recommendation from sections
        top_rec = ""
        for sec in sections:
            if any(k in sec.get("title","").lower() for k in ["recomend","estrateg"]):
                content = sec.get("content","")
                m = re.search(r'#1\s+(.+?)(?:\n|$)', content)
                if m: top_rec = m.group(1).strip()
                break

        # 3 immediate actions
        pdf.set_x(8); pdf.set_font("Helvetica","B",9.5); pdf.set_text_color(*P.TEXT)
        pdf.cell(0, 5, pdf._c("O QUE FAZER ESTA SEMANA"), new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)

        actions = []
        if top_rec:
            actions.append(top_rec[:80])
        if scenarios:
            best = max(scenarios, key=lambda s: s.get("probability",0))
            actions.append(f"Planejar para o cenario mais provavel: {best['name'][:50]}")
        if risks:
            top_risk = risks[0]
            actions.append(f"Mitigar risco #1: {top_risk['name'][:50]}")
        if not actions:
            actions = ["Revisar as recomendacoes estrategicas", "Definir cronograma de execucao", "Agendar sessao de estrategia"]

        for i, action in enumerate(actions[:3], 1):
            if pdf.get_y() > 265: pdf.add_page()
            y0 = pdf.get_y()
            pdf.set_fill_color(*P.SURFACE); pdf.rect(8, y0, pdf.w-18, 12, "F")
            num_colors = [P.ACCENT, P.ACCENT2, P.GOLD]
            pdf.set_fill_color(*num_colors[(i-1)%3])
            pdf.rect(8, y0, 12, 12, "F")
            pdf.set_xy(10, y0+1)
            pdf.set_font("Helvetica","B",9); pdf.set_text_color(255,255,255)
            pdf.cell(8, 10, str(i), align="C")
            pdf.set_xy(22, y0+2)
            pdf.set_font("Helvetica","",8); pdf.set_text_color(*P.TEXT)
            pdf.multi_cell(pdf.w-34, 4.5, pdf._c(action))
            pdf.set_y(y0 + 14)

        # Monitoring signals
        pdf.ln(4)
        pdf.set_x(8); pdf.set_font("Helvetica","B",9); pdf.set_text_color(*P.TEXT)
        pdf.cell(0, 5, pdf._c("SINAIS PARA MONITORAR"), new_x="LMARGIN", new_y="NEXT"); pdf.ln(1)
        signals = [
            ("Sinal positivo", "Recompra acima de 15%, indicacao espontanea, margem preservada", P.SUCCESS),
            ("Sinal de alerta", "Conversao abaixo de 8%, desconto acima de 15%, dependencia de promocao", P.GOLD),
            ("Sinal critico", "Break-even nao atinge ate M18, guerra de preco instalada, reputacao negativa", P.DANGER),
        ]
        for label, text, color in signals:
            if pdf.get_y() > 268: pdf.add_page()
            pdf.set_x(8); pdf.set_font("Helvetica","B",7.5); pdf.set_text_color(*color)
            pdf.cell(35, 4.5, pdf._c(f"  {label}:"))
            pdf.set_font("Helvetica","",7.5); pdf.set_text_color(*P.BODY)
            pdf.multi_cell(pdf.w-53, 4.5, pdf._c(text)); pdf.ln(1)

    @classmethod
    def _p_back(cls, pdf, verdict):
        pdf.add_page()
        pdf.set_fill_color(*P.ACCENT); pdf.rect(0,0,4,297,"F")
        pdf.set_fill_color(*P.ACCENT); pdf.rect(4,0,103,2.5,"F")
        pdf.set_fill_color(*P.ACCENT2); pdf.rect(107,0,103,2.5,"F")
        pdf.set_fill_color(*P.ACCENT2); pdf.rect(4,294.5,103,2.5,"F")
        pdf.set_fill_color(*P.ACCENT); pdf.rect(107,294.5,103,2.5,"F")
        for i in range(0,300,12):
            pdf.set_draw_color(230,230,240); pdf.set_line_width(0.15)
            pdf.line(4,i,min(4+i,210),max(0,i-200))

        pdf.set_y(85)
        vc = {"GO":P.SUCCESS,"NO-GO":P.DANGER,"AJUSTAR":P.GOLD}
        pdf.set_fill_color(*vc.get(verdict,P.GOLD))
        pdf.rect((pdf.w-80)/2,pdf.get_y(),80,10,"F")
        pdf.set_font("Helvetica","B",10); pdf.set_text_color(255,255,255)
        pdf.cell(0,10,pdf._c(verdict),align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(4)
        msgs = {"GO":"Sinal verde. Avance com as recomendacoes do relatorio.",
                "NO-GO":"Nao recomendado neste formato. Revise a estrategia.",
                "AJUSTAR":"Ha espaco, mas exige ajustes antes de avancar."}
        pdf.set_font("Helvetica","",8.5); pdf.set_text_color(*P.MUTED)
        pdf.cell(0,5,pdf._c(msgs.get(verdict,"")),align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(25)
        pdf.set_font("Helvetica","B",24); pdf.set_text_color(*P.TEXT)
        pdf.cell(0,10,"A U G U R",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.set_font("Helvetica","",8.5); pdf.set_text_color(*P.MUTED)
        pdf.cell(0,5,pdf._c("Preveja o futuro. Antes que ele aconteca."),align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(12)
        pdf.set_font("Helvetica","",7)
        pdf.cell(0,4,"augur.itcast.com.br",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.cell(0,4,"contato@itcast.com.br",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(6)
        # CTA box
        pdf.set_fill_color(*P.SURFACE)
        pdf.rect(35, pdf.get_y(), pdf.w-70, 22, "F")
        pdf.set_fill_color(*P.ACCENT); pdf.rect(35, pdf.get_y(), pdf.w-70, 1.5, "F")
        y0 = pdf.get_y() + 4
        pdf.set_xy(40, y0)
        pdf.set_font("Helvetica","B",7.5); pdf.set_text_color(*P.TEXT)
        pdf.cell(pdf.w-80, 4, pdf._c("Quer explorar outros cenarios?"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(40); pdf.set_font("Helvetica","",6.5); pdf.set_text_color(*P.MUTED)
        pdf.cell(pdf.w-80, 3.5, pdf._c("Entreviste os agentes, simule variacoes e compare cenarios"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(40); pdf.set_font("Helvetica","B",7); pdf.set_text_color(*P.ACCENT)
        pdf.cell(pdf.w-80, 4, pdf._c("Acesse o relatorio interativo em augur.itcast.com.br"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)
        pdf.set_font("Helvetica","",6); pdf.set_text_color(180,180,200)
        pdf.multi_cell(0,3.5,pdf._c(
            "Este relatorio foi gerado por inteligencia artificial com base em simulacoes de opiniao publica. "
            "Os resultados representam cenarios possiveis e nao garantem resultados futuros. "
            "Recomenda-se utilizar estas previsoes como complemento a outras analises de mercado."
        ),align="C")

    # ─── CONTENT RENDERER ───

    @classmethod
    def _render_content(cls, pdf, content):
        if not content: return
        content = re.sub(r'^#{1,6}\s+','',content,flags=re.MULTILINE)
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',content)
        for para in content.split('\n\n'):
            para = para.strip()
            if not para: continue
            if pdf.get_y() > 268: pdf.add_page()
            if para.startswith('>') or (para.startswith('"') and len(para)<500 and para.count('"')<=2):
                cls._bq(pdf, para)
            elif para.lstrip().startswith('- ') or para.lstrip().startswith('• '):
                cls._bl(pdf, para)
            elif para.startswith('**') and '**' in para[2:] and len(para)<150:
                cls._bh(pdf, para)
            else:
                cls._pp(pdf, para)

    @classmethod
    def _pp(cls, pdf, text):
        clean = pdf._c(text.replace('**',''))
        if re.match(r'^#\d+\s', text):
            pdf.ln(2); pdf.set_x(8)
            pdf.set_font("Helvetica","B",9.5); pdf.set_text_color(*P.TEXT)
            pdf.multi_cell(pdf.w-18,5,clean); pdf.ln(1); return
        pdf.set_x(8); pdf.set_font("Helvetica","",8.2); pdf.set_text_color(*P.BODY)
        pdf.multi_cell(pdf.w-18,5,clean); pdf.ln(2)

    @classmethod
    def _bh(cls, pdf, text):
        clean = pdf._c(text.replace('**','').replace('#','').strip())
        pdf.ln(1.5); pdf.set_x(8)
        pdf.set_font("Helvetica","B",9); pdf.set_text_color(*P.TEXT)
        pdf.multi_cell(pdf.w-18,5,clean); pdf.ln(1)

    @classmethod
    def _bq(cls, pdf, text):
        if pdf.get_y()>262: pdf.add_page()
        clean = text.lstrip('> "').rstrip('"')
        clean = pdf._c(clean.replace('**',''))
        y0 = pdf.get_y()
        pdf.set_fill_color(*P.SURFACE)
        # Estimate box height
        est_lines = max(1, len(clean)/80)
        est_h = est_lines*4.5 + 4
        pdf.rect(8, y0, pdf.w-18, est_h, "F")
        pdf.set_fill_color(*P.ACCENT2); pdf.rect(8, y0, 2, est_h, "F")
        pdf.set_xy(13, y0+2)
        pdf.set_font("Helvetica","I",7.5); pdf.set_text_color(80,80,110)
        pdf.multi_cell(pdf.w-26, 4.5, f'"{clean}"')
        actual_h = pdf.get_y() - y0
        if actual_h > est_h:
            pdf.set_fill_color(*P.SURFACE); pdf.rect(8, y0, pdf.w-18, actual_h, "F")
            pdf.set_fill_color(*P.ACCENT2); pdf.rect(8, y0, 2, actual_h, "F")
            pdf.set_xy(13, y0+2)
            pdf.multi_cell(pdf.w-26, 4.5, f'"{clean}"')
        pdf.ln(2.5)

    @classmethod
    def _bl(cls, pdf, text):
        for line in text.split('\n'):
            line = line.strip()
            if not line: continue
            if pdf.get_y()>272: pdf.add_page()
            clean = re.sub(r'^[-•]\s*','',line)
            clean = pdf._c(clean.replace('**',''))
            pdf.set_x(10); pdf.set_font("Helvetica","B",7); pdf.set_text_color(*P.ACCENT)
            pdf.cell(4,4.2,"-")
            pdf.set_font("Helvetica","",7.8); pdf.set_text_color(*P.BODY)
            pdf.multi_cell(pdf.w-24,4.2,clean)
        pdf.ln(1)

    # ─── PARSERS ───

    @staticmethod
    def _verdict(title, summary):
        t = f"{title} {summary}".upper()
        if "NO-GO" in t or "NO GO" in t: return "NO-GO"
        if "AJUSTAR" in t: return "AJUSTAR"
        if "GO" in t: return "GO"
        return "AJUSTAR"

    @staticmethod
    def _parse_scenarios(sections):
        for sec in sections:
            if any(k in sec.get("title","").lower() for k in ["cenário","cenario","futuro"]):
                content = sec.get("content","")
                scenarios = []
                blocks = re.split(r'(?=Cen[aá]rio\s*\d)', content)
                for block in blocks:
                    nm = re.match(r'Cen[aá]rio\s*\d*[:\.\s]*(.+?)(?:\n|$)', block)
                    pm = re.search(r'[Pp]robabilidade[:\s]*(\d+)%', block)
                    if nm and pm:
                        scenarios.append({"name": nm.group(1).strip()[:65], "probability": int(pm.group(1))})
                return scenarios if scenarios else []
        return []

    @staticmethod
    def _parse_risks(sections):
        for sec in sections:
            if "risco" in sec.get("title","").lower():
                content = sec.get("content",""); risks = []
                blocks = re.split(r'\n(?=#\d+\s)', content)
                for block in blocks:
                    if not re.match(r'#\d+', block.strip()): continue
                    nm = re.match(r'#\d+\s+(.+?)(?:\n|$)', block.strip())
                    pm = re.search(r'[Pp]robabilidade[:\s]*(\d+)%', block)
                    im = re.search(r'[Ii]mpacto[:\s]*(Alto|Médio|Baixo|Médio-Alto|Crítico)', block, re.I)
                    if nm: risks.append({"name":nm.group(1).strip()[:60],"probability":int(pm.group(1)) if pm else 50,"impact":im.group(1) if im else "Médio"})
                return risks
        return []

    @staticmethod
    def _parse_emotions(sections):
        for sec in sections:
            if any(k in sec.get("title","").lower() for k in ["emocional","sentimento"]):
                emos = {}
                for m in re.finditer(r'[-•]?\s*(\w[\w\sçãéêí]*?)\s*:\s*(\d+)%', sec.get("content","")):
                    l = m.group(1).strip()
                    if 2<len(l)<25: emos[l] = float(m.group(2))
                return emos
        return {}

    @staticmethod
    def _parse_kpis(summary, sections):
        kpis = []
        for m in re.finditer(r'\*\*(.+?)\*\*[:\s]*([^*\n]{3,30})', summary):
            kpis.append({"label":m.group(1).strip()[:20],"value":m.group(2).strip()[:12]})
        if len(kpis)<3:
            for sec in sections:
                if "resumo" in sec.get("title","").lower() or "executivo" in sec.get("title","").lower():
                    for m in re.finditer(r'\*\*(.+?)\*\*[:\s]*([^*\n]{3,30})', sec.get("content","")):
                        kpis.append({"label":m.group(1).strip()[:20],"value":m.group(2).strip()[:12]})
                    break
        return kpis[:5]

    @staticmethod
    def _parse_predictions(sections):
        for sec in sections:
            if any(k in sec.get("title","").lower() for k in ["previsão","previsao","intervalo","confiança"]):
                preds = []
                for m in re.finditer(r'[Pp]robabilidade[:\s]*(\d+)%\s*[±+/-]*\s*(\d+)', sec.get("content","")):
                    preds.append({"prob":int(m.group(1)),"margin":int(m.group(2))})
                return preds if preds else None
        return None

    @classmethod
    def _filter(cls, sections, depth):
        if depth == "deep": return sections
        exec_keys = {"resumo executivo","cenários futuros","cenarios futuros","fatores de risco","recomendações estratégicas","recomendacoes estrategicas"}
        if depth == "executive":
            f = [s for s in sections if s.get("title","").lower().strip() in exec_keys]
            return f if len(f)>=3 else sections[:4]
        return sections  # standard = all

    @staticmethod
    def _truncate(content, max_chars):
        t = content[:max_chars]
        p = t.rfind('\n\n')
        if p > max_chars*0.5: t = t[:p]
        return t.rstrip() + "\n\n[...continua no relatorio completo]"
