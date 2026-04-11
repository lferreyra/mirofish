"""
AUGUR PDF Generator v2 — Consome AugurReportSchema JSON diretamente.

Zero regex. Zero parsing de texto livre.
Todos os dados vêm do JSON estruturado produzido pelo report_agent v2.

Caminho no repo: backend/app/services/pdf_generator_v2.py

Uso:
    from app.services.pdf_generator_v2 import PDFGeneratorV2
    
    pdf_bytes = PDFGeneratorV2.generate(report_structured_json)
"""

import os
import re
import json
import tempfile
import logging

logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from fpdf import FPDF

# ============================================================
# PALETA
# ============================================================
TEAL = (0, 229, 195)
PURPLE = (124, 111, 247)
DARK = (26, 26, 46)
GRAY = (107, 114, 128)
LGRAY = (229, 231, 235)
RED = (255, 90, 90)
AMBER = (245, 166, 35)
GREEN = (34, 197, 94)
BLUE = (59, 130, 246)
WHITE = (255, 255, 255)


def _c(text):
    if not isinstance(text, str): return str(text)
    return (text.replace('\u2014','-').replace('\u2013','-')
        .replace('\u201c','"').replace('\u201d','"')
        .replace('\u2018',"'").replace('\u2019',"'")
        .replace('\u2022','-').replace('\u2192','->').replace('\u2026','...'))


def _mpl_save(fig) -> str:
    path = os.path.join(tempfile.gettempdir(), f'augur_{id(fig)}.png')
    fig.savefig(path, dpi=200, bbox_inches='tight', pad_inches=0.15, facecolor='white')
    plt.close(fig)
    return path


def _rgb(c): return (c[0]/255, c[1]/255, c[2]/255)


# ============================================================
# CHART GENERATORS — Cada um recebe dados do schema
# ============================================================

def chart_gauge(verdict_type: str) -> str:
    fig, ax = plt.subplots(figsize=(4.5, 2.5))
    ax.set_xlim(-1.4,1.4); ax.set_ylim(-0.3,1.3); ax.set_aspect('equal'); ax.axis('off')
    colors = [(180,126,_rgb(RED)),(126,72,(1,.6,.2)),(72,54,_rgb(AMBER)),(54,36,(.5,.85,.5)),(36,0,_rgb(GREEN))]
    for start,end,color in colors:
        from matplotlib.patches import Arc
        ax.add_patch(Arc((0,0),2.2,2.2,angle=0,theta1=end,theta2=start,linewidth=18,color=color,capstyle='butt'))
    v = verdict_type.upper().strip()
    ang = {'GO':12,'NO-GO':168,'AJUSTAR':63}.get(v, 63)
    rad = np.radians(ang)
    ax.annotate('',xy=(0.85*np.cos(rad),0.85*np.sin(rad)),xytext=(0,0),arrowprops=dict(arrowstyle='->',color=_rgb(DARK),lw=2.5))
    ax.plot(0,0,'o',color=_rgb(DARK),markersize=8,zorder=5)
    ax.text(-1.25,-.15,'NO-GO',fontsize=9,fontweight='bold',color=_rgb(RED),ha='center')
    ax.text(0,1.25,'AJUSTAR',fontsize=9,fontweight='bold',color=_rgb(AMBER),ha='center')
    ax.text(1.25,-.15,'GO',fontsize=9,fontweight='bold',color=_rgb(GREEN),ha='center')
    ax.text(0,-.25,v,fontsize=16,fontweight='bold',color=_rgb(DARK),ha='center')
    return _mpl_save(fig)


def chart_scenarios_bars(cenarios: list) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 2.5))
    names = [c.get('nome','')[:45] for c in cenarios]
    probs = [c.get('probabilidade',33) for c in cenarios]
    colors = [_rgb(TEAL), _rgb(AMBER), _rgb(RED)][:len(cenarios)]
    bars = ax.barh(range(len(names)), probs, color=colors, height=0.55)
    for b,p in zip(bars,probs):
        ax.text(b.get_width()+1.5, b.get_y()+b.get_height()/2, f'{p}%', va='center', fontsize=13, fontweight='bold')
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=9)
    ax.set_xlim(0,62); ax.set_xlabel('Probabilidade (%)', fontsize=9, color=_rgb(GRAY))
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['left'].set_visible(False)
    ax.tick_params(left=False)
    return _mpl_save(fig)


def chart_financial_projection(cenarios: list) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    colors = [_rgb(TEAL), _rgb(AMBER), _rgb(RED)]
    for i, c in enumerate(cenarios):
        proj = c.get('projecao_faturamento_24m', [])
        if proj:
            months = np.arange(len(proj))
            ax.fill_between(months, proj, alpha=0.1, color=colors[i%3])
            ax.plot(months, proj, '-', color=colors[i%3], linewidth=2.5 - i*0.5,
                    label=f"{c.get('nome','')[:30]} ({c.get('probabilidade',0)}%)")
    ax.axhline(y=30, color='#d1d5db', linestyle='--', linewidth=0.8)
    ax.text(24.5, 30, 'Break-even', fontsize=7, color=_rgb(GRAY), va='center')
    ax.set_xlim(0,24); ax.set_xlabel('Meses', fontsize=9, color=_rgb(GRAY))
    ax.set_ylabel('Faturamento (R$ mil/mes)', fontsize=9, color=_rgb(GRAY))
    ax.legend(fontsize=7, loc='upper left', framealpha=0.9)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    return _mpl_save(fig)


def chart_risk_scatter(riscos: list) -> str:
    fig, ax = plt.subplots(figsize=(5.5, 4))
    imap = {'alto':95,'medio':60,'medio-alto':75,'baixo':30,'critico':100}
    ax.axhspan(75,100,color='#fff0f0',zorder=0); ax.axhspan(50,75,color='#fffbf0',zorder=0)
    for r in riscos:
        prob = r.get('probabilidade',50)
        impact_val = imap.get(r.get('impacto','medio').lower().replace('é','e'),60)
        color = _rgb(RED) if impact_val > 75 else (_rgb(AMBER) if impact_val > 50 else _rgb(GREEN))
        ax.scatter(prob, impact_val, s=350, color=color, alpha=0.85, edgecolors='white', linewidth=1.5, zorder=4)
        ax.text(prob, impact_val, f"R{r.get('numero',0)}", ha='center', va='center', fontsize=8, fontweight='bold', color='white', zorder=5)
    ax.set_xlim(40,100); ax.set_ylim(20,105)
    ax.set_xlabel('Probabilidade (%)', fontsize=9); ax.set_ylabel('Impacto', fontsize=9)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    # Legend
    for i, r in enumerate(riscos[:7]):
        ax.text(101, 100-i*8, f"R{r.get('numero',i+1)} {r.get('titulo','')[:30]}", fontsize=6, color=_rgb(GRAY))
    return _mpl_save(fig)


def chart_emotion_radar(emocoes: list) -> str:
    fig = plt.figure(figsize=(7, 3.5))
    labels = [e.get('nome','') for e in emocoes]
    values = [e.get('percentual',0) for e in emocoes]
    N = len(labels)
    angles = [n/N * 2 * np.pi for n in range(N)] + [0]
    values_c = values + [values[0]]
    ax = fig.add_subplot(121, polar=True)
    ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1)
    ax.plot(angles, values_c, 'o-', linewidth=2, color=_rgb(PURPLE), markersize=4)
    ax.fill(angles, values_c, alpha=0.15, color=_rgb(PURPLE))
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylim(0, max(values)*1.3)
    # Bars
    ax2 = fig.add_subplot(122)
    bar_colors = [_rgb(TEAL),_rgb(AMBER),_rgb(PURPLE),_rgb(RED),_rgb(BLUE),_rgb(GRAY)]
    bars = ax2.barh(range(N), values, color=[bar_colors[i%6] for i in range(N)], height=0.5)
    for b,v in zip(bars,values): ax2.text(b.get_width()+0.5, b.get_y()+b.get_height()/2, f'{v}%', va='center', fontsize=9, fontweight='bold')
    ax2.set_yticks(range(N)); ax2.set_yticklabels(labels, fontsize=9); ax2.invert_yaxis()
    ax2.set_xlim(0,40); ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False); ax2.spines['left'].set_visible(False)
    ax2.tick_params(left=False)
    fig.tight_layout()
    return _mpl_save(fig)


def chart_emotion_timeline(evolucao: dict) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 3))
    style = {'confianca':(_rgb(TEAL),'-',2.5), 'ceticismo':(_rgb(AMBER),'-',2.5),
             'empolgacao':(_rgb(PURPLE),'--',1.5), 'medo':(_rgb(RED),':',1.5)}
    for key, data in evolucao.items():
        s = style.get(key, (_rgb(GRAY),'-',1))
        ax.plot(range(len(data)), data, linestyle=s[1], color=s[0], linewidth=s[2], label=key.capitalize())
    for x,lbl in [(3,'Fim curiosidade'),(6,'Teste'),(12,'Break-even'),(18,'Consolidacao')]:
        ax.axvline(x=x, color='#e5e7eb', linestyle='--', linewidth=0.8)
        ax.text(x, ax.get_ylim()[1]*0.95, lbl, fontsize=6.5, color=_rgb(GRAY), ha='center')
    ax.set_xlim(0,24); ax.set_xlabel('Meses', fontsize=9); ax.set_ylabel('Intensidade (%)', fontsize=9)
    ax.legend(fontsize=7.5, loc='upper right'); ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    return _mpl_save(fig)


def chart_agent_spectrum(agentes: list) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 2))
    ax.set_xlim(-0.5,10.5); ax.set_ylim(-0.8,1.5); ax.axis('off')
    gradient = np.linspace(0,1,256).reshape(1,-1)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list('', [_rgb(TEAL),'#e5e7eb',_rgb(RED)])
    ax.imshow(gradient, aspect='auto', cmap=cmap, extent=[0,10,0,0.4], zorder=1)
    ax.text(0,-0.3,'Apoiador',fontsize=8,fontweight='bold',color=_rgb(TEAL))
    ax.text(5,-0.3,'Neutro',fontsize=8,color=_rgb(GRAY),ha='center')
    ax.text(10,-0.3,'Resistente',fontsize=8,fontweight='bold',color=_rgb(RED),ha='right')
    type_colors = {'Apoiador':_rgb(TEAL),'Neutro':_rgb(AMBER),'Resistente':_rgb(RED),'Cauteloso':_rgb(PURPLE)}
    for a in agentes:
        x = a.get('posicao_espectro',0.5) * 10
        color = type_colors.get(a.get('tipo','Neutro'), _rgb(GRAY))
        ax.plot(x, 0.2, 'o', color=color, markersize=14, zorder=4, markeredgecolor='white', markeredgewidth=1.5)
        ax.text(x, 0.7, a.get('nome',''), fontsize=7.5, fontweight='bold', ha='center', linespacing=1.1)
        ax.text(x, 1.1, a.get('papel_na_dinamica',''), fontsize=6, ha='center', color=_rgb(GRAY))
    return _mpl_save(fig)


def chart_stack_ranking(recomendacoes: list) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    colors = [_rgb(TEAL),_rgb(PURPLE),_rgb(AMBER),_rgb(BLUE),_rgb(GREEN)]
    labels = [r.get('titulo','') for r in recomendacoes]
    values = [r.get('impacto_relativo',50) for r in recomendacoes]
    bars = ax.barh(range(len(labels)), values, color=[colors[i%5] for i in range(len(labels))], height=0.55, alpha=0.7)
    for b,l in zip(bars,labels):
        ax.text(2, b.get_y()+b.get_height()/2, l[:55], va='center', fontsize=8.5, fontweight='bold',
                color='white' if b.get_width()>60 else _rgb(DARK), zorder=5)
    ax.set_xlim(0,110); ax.set_yticks([]); ax.invert_yaxis()
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['left'].set_visible(False); ax.spines['bottom'].set_visible(False)
    ax.tick_params(bottom=False, labelbottom=False)
    return _mpl_save(fig)


def chart_confidence_bars(previsoes: list) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 4))
    labels = [p.get('titulo','')[:30] for p in previsoes]
    probs = [p.get('probabilidade',50) for p in previsoes]
    margins = [p.get('margem_erro',5) for p in previsoes]
    colors = [_rgb(TEAL) if p>=70 else (_rgb(AMBER) if p>=55 else _rgb(RED)) for p in probs]
    bars = ax.barh(range(len(labels)), probs, color=colors, height=0.5, alpha=0.7)
    ax.errorbar(probs, range(len(labels)), xerr=margins, fmt='none', ecolor=_rgb(DARK), elinewidth=1.2, capsize=4)
    for i,(p,m) in enumerate(zip(probs,margins)):
        ax.text(min(p+m+2,100), i, f'{p}% +/-{m}', va='center', fontsize=8, fontweight='bold')
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=8); ax.set_xlim(0,105); ax.invert_yaxis()
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['left'].set_visible(False)
    ax.tick_params(left=False)
    return _mpl_save(fig)


def chart_positioning(players: list) -> str:
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.axhline(y=50,color='#e5e7eb',lw=0.8); ax.axvline(x=50,color='#e5e7eb',lw=0.8)
    role_colors = {'Incumbente':_rgb(RED),'Entrante':_rgb(TEAL),'CanalDigital':_rgb(GRAY),
                   'CanalInformal':_rgb(AMBER),'desejado':_rgb(GREEN),'atual':_rgb(BLUE)}
    for p in players:
        x,y = p.get('x',50), p.get('y',50)
        color = role_colors.get(p.get('papel',''), _rgb(GRAY))
        ax.scatter(x,y,s=300,color=color,alpha=0.5,edgecolors=color,linewidth=1.5,zorder=3)
        ax.text(x,y-5,p.get('nome',''),fontsize=7.5,ha='center',fontweight='bold',zorder=5)
    ax.set_xlim(0,100); ax.set_ylim(0,100)
    ax.set_xlabel('Preco acessivel  <---->  Preco premium', fontsize=8, color=_rgb(GRAY))
    ax.set_ylabel('Funcional  <---->  Aspiracional', fontsize=8, color=_rgb(GRAY))
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    return _mpl_save(fig)


def chart_final_radar(scores: dict) -> str:
    fig = plt.figure(figsize=(4.5,4.5))
    labels = list(scores.keys()); values = list(scores.values())
    N = len(labels)
    angles = [n/N*2*np.pi for n in range(N)] + [0]
    values_c = values + [values[0]]
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1)
    ax.plot(angles, values_c, 'o-', linewidth=2.5, color=_rgb(TEAL), markersize=6)
    ax.fill(angles, values_c, alpha=0.15, color=_rgb(TEAL))
    for a,v in zip(angles[:-1],values): ax.text(a, v+8, str(v), ha='center', fontsize=11, fontweight='bold')
    ax.set_xticks(angles[:-1]); ax.set_xticklabels([l.replace('_',' ').title() for l in labels], fontsize=8.5)
    ax.set_ylim(0,100)
    total = sum(values)//len(values)
    ax.set_title(f'Viabilidade Geral: {total}/100', fontsize=12, fontweight='bold', pad=20)
    return _mpl_save(fig)


def chart_roi(riscos_evitados: list, custo_analise: str, risco_total: str) -> str:
    fig, ax = plt.subplots(figsize=(5.5, 3))
    cats = [r.get('titulo','')[:15] for r in riscos_evitados] + ['Total']
    # Parse R$ values
    def parse_val(s):
        m = re.search(r'(\d+)', str(s).replace('.',''))
        return int(m.group(1)) if m else 50
    sem = [parse_val(r.get('valor_risco','50k')) for r in riscos_evitados]
    sem.append(parse_val(risco_total))
    com = [parse_val(custo_analise)] * len(riscos_evitados) + [parse_val(custo_analise)]
    x = np.arange(len(cats)); width=0.35
    ax.bar(x-width/2, sem, width, label='Sem AUGUR (risco)', color=_rgb(RED), alpha=0.6)
    ax.bar(x+width/2, com, width, label='Com AUGUR (invest.)', color=_rgb(TEAL), alpha=0.7)
    for i,v in enumerate(sem): ax.text(i-width/2, v+2, f'R${v}k', ha='center', fontsize=7, color=_rgb(RED), fontweight='bold')
    for i,v in enumerate(com): ax.text(i+width/2, v+2, f'R${v}k', ha='center', fontsize=7, color=_rgb(TEAL), fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=7.5)
    ax.legend(fontsize=8); ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    return _mpl_save(fig)


# ============================================================
# PDF GENERATOR V2 — Consome AugurReportSchema
# ============================================================

class PDFGeneratorV2:
    """
    Gera PDF a partir do JSON estruturado (AugurReportSchema).
    
    ZERO regex. ZERO parsing de texto livre.
    Cada seção renderiza diretamente do campo tipado do JSON.
    """
    
    @classmethod
    def generate(cls, data: dict, output_path: str = None) -> bytes:
        """
        Gera o PDF completo a partir do JSON estruturado.
        
        Args:
            data: JSON no formato AugurReportSchema
            output_path: caminho para salvar (opcional)
        
        Returns:
            bytes do PDF
        """
        from io import BytesIO
        
        pdf = cls._create_pdf()
        
        meta = data.get('meta', {})
        veredicto = data.get('veredicto', {})
        dashboard = data.get('dashboard', {})
        cenarios_data = data.get('cenarios', {})
        cenarios = cenarios_data.get('cenarios', [])
        riscos_data = data.get('riscos', {})
        riscos = riscos_data.get('riscos', [])
        emocional = data.get('emocional', {})
        agentes = data.get('agentes', [])
        forcas = data.get('forcas', {})
        cronologia = data.get('cronologia', {})
        padroes = data.get('padroes', [])
        recomendacoes = data.get('recomendacoes', [])
        checklist = data.get('checklist', [])
        previsoes = data.get('previsoes', [])
        posicionamento = data.get('posicionamento', {})
        roi = data.get('roi', {})
        sintese = data.get('sintese', {})
        
        # P1: Capa
        cls._page_cover(pdf, meta, veredicto)
        # P2: Decisão 30s
        cls._page_decision(pdf, veredicto, dashboard)
        # P3: Sumário + Metodologia
        cls._page_toc(pdf, meta)
        # P4: Resumo Executivo
        cls._page_executive(pdf, veredicto)
        # P5: Dashboard KPIs (NOVO)
        cls._page_dashboard(pdf, dashboard)
        # P6: Cenários Futuros
        cls._page_scenarios(pdf, cenarios, cenarios_data)
        # P7: Cenários Financeiros (NOVO)
        cls._page_financial(pdf, cenarios)
        # P8-9: Fatores de Risco
        cls._page_risks(pdf, riscos_data, riscos)
        # P10: Análise Emocional
        cls._page_emotions(pdf, emocional)
        # P11: Perfis dos Agentes (NOVO)
        cls._page_agents(pdf, agentes)
        # P12: Mapa de Forças
        cls._page_forces(pdf, forcas)
        # P13: Cronologia
        cls._page_timeline(pdf, cronologia)
        # P14: Padrões Emergentes
        cls._page_patterns(pdf, padroes)
        # P15: Recomendações
        cls._page_recommendations(pdf, recomendacoes)
        # P16: Checklist (NOVO)
        cls._page_checklist(pdf, checklist)
        # P17: Previsões
        cls._page_predictions(pdf, previsoes)
        # P18: Posicionamento
        cls._page_positioning(pdf, posicionamento)
        # P19: ROI (NOVO)
        cls._page_roi(pdf, roi)
        # P20: Síntese Final
        cls._page_synthesis(pdf, sintese, veredicto)
        # P21: Contracapa
        cls._page_back(pdf, veredicto)
        
        if output_path:
            pdf.output(output_path)
            with open(output_path, 'rb') as f:
                return f.read()
        else:
            return pdf.output()
    
    @classmethod
    def _create_pdf(cls):
        """Cria instância do FPDF com fontes e configuração."""
        pdf = FPDF('P', 'mm', 'A4')
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        pdf.add_font('DejaVu', 'B', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
        pdf.add_font('DejaVu', 'I', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf')
        pdf.add_font('Mono', '', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
        pdf.add_font('Mono', 'B', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf')
        pdf._margin = 18
        pdf._cw = 210 - 36  # content width
        return pdf
    
    # ── Helper methods ──
    
    @classmethod
    def _header(cls, pdf, section_num=None, section_total=16, title="", is_new=False):
        """Standard page header with section tag."""
        pdf.add_page()
        # Top accent line
        pdf.set_draw_color(*TEAL); pdf.set_line_width(0.8)
        pdf.line(18, 14, 192, 14)
        # Header text
        pdf.set_font('DejaVu', '', 7); pdf.set_text_color(*GRAY)
        pdf.set_xy(18, 8)
        pdf.cell(174, 5, _c(f'AUGUR  Relatorio de Previsao'), 0, 0, 'L')
        pdf.set_y(18)
        # Section tag
        if section_num:
            tag = f'SECAO {section_num:02d} DE {section_total}'
            if is_new: tag += '  -  NOVO'
            color = TEAL if is_new else TEAL
            pdf.set_fill_color(240, 253, 250)
            pdf.set_font('DejaVu', 'B', 8); pdf.set_text_color(*color)
            w = pdf.get_string_width(tag) + 12
            pdf.cell(w, 7, _c(tag), 0, 1, 'C', True); pdf.ln(3)
        # Title
        if title:
            pdf.set_font('DejaVu', 'B', 18); pdf.set_text_color(*DARK)
            pdf.multi_cell(174, 8, _c(title), 0, 'L'); pdf.ln(2)
    
    @classmethod
    def _body(cls, pdf, text, size=9.5):
        pdf.set_font('DejaVu', '', size); pdf.set_text_color(75, 85, 99)
        pdf.multi_cell(174, 5.5, _c(text), 0, 'L'); pdf.ln(2)
    
    @classmethod
    def _bold(cls, pdf, text, size=9.5):
        pdf.set_font('DejaVu', 'B', size); pdf.set_text_color(*DARK)
        pdf.multi_cell(174, 5.5, _c(text), 0, 'L'); pdf.ln(1)
    
    @classmethod
    def _quote(cls, pdf, text):
        y = pdf.get_y()
        pdf.set_font('DejaVu', 'I', 9); pdf.set_text_color(90, 90, 110)
        lines = pdf.multi_cell(162, 5, _c(f'"{text}"'), 0, 'L', dry_run=True, output='LINES')
        h = len(lines) * 5 + 6
        pdf.set_fill_color(245, 245, 250); pdf.rect(18, y, 174, h, 'F')
        pdf.set_draw_color(*PURPLE); pdf.set_line_width(0.6); pdf.line(18, y, 18, y+h)
        pdf.set_xy(24, y+3); pdf.multi_cell(162, 5, _c(f'"{text}"'), 0, 'L')
        pdf.ln(3)
    
    @classmethod
    def _chart(cls, pdf, chart_path, w=None):
        if not chart_path or not os.path.exists(chart_path): return
        if w is None: w = 174
        x = 18 + (174 - w) / 2
        pdf.image(chart_path, x=x, w=w); pdf.ln(3)
    
    @classmethod
    def _kpi_grid(cls, pdf, items):
        """items: [(value, label, color), ...]"""
        n = len(items); w = (174 - (n-1)*3) / n; y0 = pdf.get_y()
        for i, (val, label, color) in enumerate(items):
            x = 18 + i*(w+3)
            pdf.set_fill_color(248,248,252); pdf.rect(x, y0, w, 20, 'DF')
            pdf.set_font('Mono', 'B', 13); pdf.set_text_color(*color)
            pdf.set_xy(x, y0+2); pdf.cell(w, 8, _c(val), 0, 0, 'C')
            pdf.set_font('DejaVu', '', 7); pdf.set_text_color(*GRAY)
            pdf.set_xy(x, y0+11); pdf.cell(w, 5, _c(label), 0, 0, 'C')
        pdf.set_y(y0 + 24)
    
    @classmethod
    def _footer_line(cls, pdf):
        pdf.set_y(-14); pdf.set_font('DejaVu','',7); pdf.set_text_color(*GRAY)
        pdf.cell(87, 5, _c('augur.itcast.com.br'), 0, 0, 'L')
        pdf.cell(87, 5, _c(f'Pagina {pdf.page_no()-1}'), 0, 0, 'R')
    
    # ── Page builders ──
    # Each method consumes ONE section of the schema JSON directly.
    # No parsing. No regex. Just data → layout.
    
    @classmethod
    def _page_cover(cls, pdf, meta, veredicto):
        pdf.add_page()
        pdf.set_fill_color(*WHITE); pdf.rect(0,0,210,297,'F')
        pdf.set_fill_color(*TEAL); pdf.rect(0,0,6,297,'F')  # left bar
        pdf.set_fill_color(*TEAL); pdf.rect(6,30,204,1.5,'F')
        pdf.set_xy(18,50); pdf.set_font('Mono','B',38); pdf.set_text_color(*DARK)
        pdf.cell(0,18,_c('A U G U R'),0,1,'C')
        pdf.set_font('DejaVu','',10); pdf.set_text_color(*GRAY)
        pdf.cell(0,7,_c('Plataforma de Previsao de Mercado por IA'),0,1,'C')
        pdf.ln(12)
        pdf.set_font('DejaVu','',11); pdf.set_text_color(*DARK)
        pdf.cell(0,6,_c('Relatorio de Previsao:'),0,1,'C'); pdf.ln(2)
        pdf.set_font('DejaVu','B',15)
        pdf.multi_cell(0,8,_c(meta.get('projeto','Projeto AUGUR')),0,'C')
        # Gauge
        if HAS_MPL:
            pdf.ln(10)
            gp = chart_gauge(veredicto.get('tipo','AJUSTAR'))
            cls._chart(pdf, gp, w=85)
        # Verdict badge
        vt = veredicto.get('tipo','AJUSTAR')
        vc = AMBER if vt=='AJUSTAR' else (GREEN if vt=='GO' else RED)
        pdf.ln(2); y = pdf.get_y(); bw=90; bx=(210-bw)/2
        pdf.set_fill_color(255,248,230); pdf.set_draw_color(*vc); pdf.set_line_width(0.8)
        pdf.rect(bx,y,bw,12,'DF')
        pdf.set_font('DejaVu','B',13); pdf.set_text_color(*vc)
        pdf.set_xy(bx,y+1); pdf.cell(bw,10,_c(f'VEREDICTO: {vt}'),0,1,'C')
        pdf.ln(6)
        pdf.set_font('DejaVu','I',9); pdf.set_text_color(*GRAY); pdf.set_x(25)
        pdf.multi_cell(160,5,_c(veredicto.get('frase_chave','')),0,'C')
        # Footer
        pdf.set_y(255); pdf.set_draw_color(*LGRAY); pdf.line(50,pdf.get_y(),160,pdf.get_y()); pdf.ln(6)
        pdf.set_font('DejaVu','',9); pdf.set_text_color(*GRAY)
        pdf.cell(0,5,_c(meta.get('data_geracao','')[:10]),0,1,'C')
        pdf.set_font('DejaVu','B',8); pdf.set_text_color(180,180,190)
        pdf.cell(0,5,_c('CONFIDENCIAL'),0,1,'C')
        pdf.set_fill_color(*TEAL); pdf.rect(6,285,204,1.5,'F')
    
    @classmethod
    def _page_decision(cls, pdf, veredicto, dashboard):
        cls._header(pdf, title='Decisao em 30 segundos')
        cls._body(pdf, 'O que voce precisa saber para decidir agora:')
        cls._kpi_grid(pdf, [
            (dashboard.get('capital_giro_necessario','?'), 'Capital giro crediario', DARK),
            (dashboard.get('breakeven_cenario1','?'), 'Break-even provavel', PURPLE),
            (dashboard.get('prob_sobrevivencia_24m','?'), 'Prob. sobrevivencia', TEAL),
            (dashboard.get('margem_bruta_alvo','?'), 'Margem bruta alvo', AMBER),
        ])
        cls._bold(pdf, 'Fatos que definem esta decisao:')
        for f in veredicto.get('top5_fatos', []):
            cls._bold(pdf, f'  {f.get("titulo","")}', 9)
            cls._body(pdf, f'  {f.get("descricao","")}', 8.5)
        cls._quote(pdf, veredicto.get('frase_chave',''))
    
    @classmethod
    def _page_toc(cls, pdf, meta):
        cls._header(pdf, title='Sumario')
        sections = ['01 Resumo Executivo','02 Dashboard de KPIs (NOVO)','03 Cenarios Futuros',
            '04 Cenarios Financeiros (NOVO)','05 Fatores de Risco','06 Analise Emocional',
            '07 Perfis dos Agentes (NOVO)','08 Mapa de Forcas','09 Cronologia',
            '10 Padroes Emergentes','11 Recomendacoes Estrategicas','12 Checklist GO (NOVO)',
            '13 Previsoes com Intervalo de Confianca','14 Posicionamento',
            '15 ROI da Analise (NOVO)','16 Sintese Final']
        for s in sections:
            is_new = 'NOVO' in s
            pdf.set_font('DejaVu','B' if is_new else '',9.5)
            pdf.set_text_color(*(TEAL if is_new else DARK))
            pdf.cell(0,6.5,_c(s),0,1,'L')
        pdf.ln(6); cls._bold(pdf, 'Sobre esta analise', 10)
        cls._body(pdf, f'Projeto: {meta.get("projeto","")}\nAgentes: {meta.get("num_agentes",0)} perfis sinteticos\nRodadas: {meta.get("num_rodadas",0)} ciclos ({meta.get("periodo_simulado_meses",24)} meses)\nModelo: {meta.get("modelo_ia","GPT-5.4")}', 8.5)
    
    @classmethod
    def _page_executive(cls, pdf, veredicto):
        cls._header(pdf, 1, title='Resumo Executivo')
        cls._bold(pdf, veredicto.get('resumo_executivo',''))
        if veredicto.get('leitura_para_decisao'):
            cls._bold(pdf, 'Leitura para decisao:', 9)
            cls._body(pdf, veredicto.get('leitura_para_decisao',''))
    
    @classmethod
    def _page_dashboard(cls, pdf, dashboard):
        cls._header(pdf, 2, title='Dashboard de KPIs - 24 Meses', is_new=True)
        d = dashboard
        cls._kpi_grid(pdf, [
            (d.get('ticket_medio','?'),'Ticket medio',TEAL),
            (d.get('volume_breakeven','?'),'Volume break-even',PURPLE),
            (d.get('margem_bruta_alvo','?'),'Margem bruta',DARK),
            (d.get('capital_giro_necessario','?'),'Capital giro',AMBER),
        ])
        cls._kpi_grid(pdf, [
            (d.get('recompra_alvo','?'),'Recompra alvo',TEAL),
            (d.get('vendas_por_indicacao','?'),'Vendas indicacao',PURPLE),
            (d.get('erosao_margem_sazonal','?'),'Erosao sazonal',RED),
            (d.get('breakeven_cenario1','?'),'Break-even cen.1',DARK),
        ])
        if d.get('investimento_total_estimado'):
            cls._bold(pdf, f'Investimento total estimado: {d["investimento_total_estimado"]}')
            for item in d.get('composicao_investimento',[]):
                cls._body(pdf, f'  - {item.get("item","")}: {item.get("valor","")}', 8.5)
        # Semaforo
        cls._bold(pdf, 'Faixas de monitoramento')
        # Simple 3-column layout
        y0 = pdf.get_y(); w = (174-6)/3
        for i,(items,color,bg,title) in enumerate([
            (d.get('sinais_consolidacao',[]),(15,80,10),(234,243,222),'Consolidacao'),
            (d.get('sinais_alerta',[]),(133,79,11),(250,238,218),'Alerta'),
            (d.get('sinais_risco_critico',[]),(163,45,45),(252,235,235),'Risco critico'),
        ]):
            x = 18 + i*(w+3)
            pdf.set_fill_color(*bg); pdf.rect(x,y0,w,45,'F')
            pdf.set_font('DejaVu','B',8); pdf.set_text_color(*color)
            pdf.set_xy(x+3,y0+2); pdf.cell(w-6,5,_c(title),0,1,'L')
            pdf.set_font('DejaVu','',7.5); cur_y = y0+8
            for it in items:
                pdf.set_xy(x+3,cur_y); pdf.multi_cell(w-6,4,_c(f'- {it}'),0,'L')
                cur_y = pdf.get_y()
        pdf.set_y(y0+50)
    
    @classmethod
    def _page_scenarios(cls, pdf, cenarios, cenarios_data):
        cls._header(pdf, 3, title='Cenarios Futuros')
        if HAS_MPL and cenarios: cls._chart(pdf, chart_scenarios_bars(cenarios), w=150)
        for c in cenarios:
            cls._bold(pdf, f'{c.get("nome","")}')
            pdf.set_font('Mono','B',9); pdf.set_text_color(*TEAL)
            pdf.cell(0,5,_c(f'Probabilidade: {c.get("probabilidade",0)}%  |  Break-even: {c.get("breakeven","")}'),0,1,'L'); pdf.ln(2)
            cls._body(pdf, c.get('descricao',''))
            if c.get('citacao_agente'): cls._quote(pdf, c['citacao_agente'])
        if cenarios_data.get('ponto_bifurcacao'):
            cls._body(pdf, f'Ponto de bifurcacao: {cenarios_data["ponto_bifurcacao"]}', 9)
    
    @classmethod
    def _page_financial(cls, pdf, cenarios):
        cls._header(pdf, 4, title='Cenarios Financeiros Comparados', is_new=True)
        if HAS_MPL and cenarios and cenarios[0].get('projecao_faturamento_24m'):
            cls._chart(pdf, chart_financial_projection(cenarios), w=155)
        # Table
        cls._bold(pdf, 'Comparativo por cenario')
        col_w = [45,38,38,38]
        headers = ['Metrica'] + [f'Cen. {i+1} ({c.get("probabilidade",0)}%)' for i,c in enumerate(cenarios)]
        rows = [
            ['Break-even'] + [c.get('breakeven','') for c in cenarios],
            ['Faturamento M24'] + [c.get('faturamento_m24','') for c in cenarios],
            ['Margem bruta'] + [c.get('margem_bruta','') for c in cenarios],
            ['Risco central'] + [c.get('risco_central','') for c in cenarios],
        ]
        y = pdf.get_y()
        for i, h in enumerate(headers[:4]):
            x = 18 + sum(col_w[:i])
            pdf.set_fill_color(240,253,250); pdf.set_font('DejaVu','B',8); pdf.set_text_color(*TEAL)
            pdf.set_xy(x,y); pdf.cell(col_w[i],7,_c(h),1,0,'C',True)
        pdf.ln(7)
        for row in rows:
            y = pdf.get_y()
            for i, val in enumerate(row[:4]):
                x = 18 + sum(col_w[:i])
                pdf.set_font('DejaVu','' if i>0 else 'B',8); pdf.set_text_color(*(DARK if i==0 else GRAY))
                pdf.set_xy(x,y); pdf.cell(col_w[i],6,_c(val),1,0,'C' if i>0 else 'L')
            pdf.ln(6)
    
    @classmethod
    def _page_risks(cls, pdf, riscos_data, riscos):
        cls._header(pdf, 5, title='Fatores de Risco')
        cls._body(pdf, riscos_data.get('texto_introducao',''))
        if HAS_MPL and riscos: cls._chart(pdf, chart_risk_scatter(riscos), w=135)
        for r in riscos:
            y = pdf.get_y()
            if y > 255: pdf.add_page(); y = pdf.get_y()
            imp = r.get('impacto','Medio')
            pdf.set_fill_color(*(RED if imp=='Alto' else AMBER)); pdf.rect(18,y,3,18,'F')
            pdf.set_font('DejaVu','B',9.5); pdf.set_text_color(*DARK); pdf.set_xy(24,y)
            pdf.cell(0,5,_c(f'#{r.get("numero",0)} {r.get("titulo","")}'),0,1,'L')
            pdf.set_font('Mono','',8); pdf.set_text_color(*GRAY); pdf.set_x(24)
            pdf.cell(0,4,_c(f'Probabilidade: {r.get("probabilidade",0)}%  |  Impacto: {imp}'),0,1,'L')
            pdf.set_font('DejaVu','',8.5); pdf.set_text_color(75,85,99); pdf.set_x(24)
            pdf.multi_cell(168,4.5,_c(r.get('descricao','')),0,'L'); pdf.ln(1)
            if r.get('citacao_agente'): cls._quote(pdf, r['citacao_agente'])
    
    @classmethod
    def _page_emotions(cls, pdf, emocional):
        cls._header(pdf, 6, title='Analise Emocional')
        emocoes = emocional.get('emocoes',[])
        if HAS_MPL and emocoes: cls._chart(pdf, chart_emotion_radar(emocoes), w=160)
        cls._body(pdf, emocional.get('saldo_positivo_vs_negativo',''))
        if emocional.get('texto_confianca'):
            cls._bold(pdf, 'Confianca - emocao mais relevante')
            cls._body(pdf, emocional['texto_confianca'])
            if emocional.get('citacao_confianca'): cls._quote(pdf, emocional['citacao_confianca'])
        if emocional.get('texto_ceticismo'):
            cls._bold(pdf, 'Ceticismo - defesa natural')
            cls._body(pdf, emocional['texto_ceticismo'])
            if emocional.get('citacao_ceticismo'): cls._quote(pdf, emocional['citacao_ceticismo'])
        evolucao = emocional.get('evolucao_24m',{})
        if HAS_MPL and evolucao:
            cls._bold(pdf, 'Evolucao temporal das emocoes')
            cls._chart(pdf, chart_emotion_timeline(evolucao), w=150)
    
    @classmethod
    def _page_agents(cls, pdf, agentes):
        cls._header(pdf, 7, title='Perfis dos Agentes - Quem disse o que', is_new=True)
        cls._body(pdf, 'Cada agente e um perfil sintetico que representa um segmento real do mercado.')
        type_colors = {'Apoiador':TEAL,'Neutro':AMBER,'Resistente':RED,'Cauteloso':PURPLE}
        for a in agentes:
            y = pdf.get_y()
            if y > 248: pdf.add_page(); y = pdf.get_y()
            color = type_colors.get(a.get('tipo','Neutro'), GRAY)
            pdf.set_fill_color(*color); pdf.rect(18,y,3,22,'F')
            pdf.set_font('DejaVu','B',10); pdf.set_text_color(*DARK); pdf.set_x(24)
            pdf.cell(40,5,_c(a.get('nome','')),0,0,'L')
            pdf.set_font('DejaVu','',8); pdf.set_text_color(*color)
            pdf.cell(0,5,_c(f'  {a.get("papel_na_dinamica","")}'),0,1,'L')
            pdf.set_font('DejaVu','',8.5); pdf.set_text_color(*GRAY); pdf.set_x(24)
            pdf.cell(0,4.5,_c(a.get('descricao','')),0,1,'L')
            pdf.set_font('DejaVu','I',8.5); pdf.set_text_color(90,90,110); pdf.set_x(24)
            pdf.multi_cell(168,4.5,_c(f'"{a.get("citacao_chave","")}"'),0,'L'); pdf.ln(4)
        if HAS_MPL and agentes:
            cls._bold(pdf, 'Espectro de posicionamento')
            cls._chart(pdf, chart_agent_spectrum(agentes), w=155)
    
    @classmethod
    def _page_forces(cls, pdf, forcas):
        cls._header(pdf, 8, title='Mapa de Forcas')
        # Use chart if matplotlib available, otherwise text
        if HAS_MPL:
            from matplotlib.patches import Arc
            # Generate force map from structured data - simplified
            pass  # TODO: generate from forcas.blocos dynamically
        for b in forcas.get('blocos',[]):
            cls._bold(pdf, b.get('nome',''), 9.5)
            cls._body(pdf, f'{b.get("base_clientes","")}. {b.get("descricao","")}', 8.5)
            if b.get('citacao'): cls._quote(pdf, b['citacao'])
        if forcas.get('hierarquia_poder'):
            cls._bold(pdf, 'Hierarquia de poder:', 9)
            cls._body(pdf, forcas['hierarquia_poder'], 8.5)
    
    @classmethod
    def _page_timeline(cls, pdf, cronologia):
        cls._header(pdf, 9, title='Cronologia da Simulacao')
        for fase in cronologia.get('fases',[]):
            cls._bold(pdf, f'{fase.get("periodo","")}: {fase.get("nome","")}')
            cls._body(pdf, fase.get('descricao',''))
            if fase.get('citacao'): cls._quote(pdf, fase['citacao'])
    
    @classmethod
    def _page_patterns(cls, pdf, padroes):
        cls._header(pdf, 10, title='Padroes Emergentes')
        for p in padroes:
            cls._bold(pdf, f'{p.get("numero","")}. {p.get("titulo","")}', 9.5)
            cls._body(pdf, p.get('descricao',''), 8.5)
    
    @classmethod
    def _page_recommendations(cls, pdf, recomendacoes):
        cls._header(pdf, 11, title='Recomendacoes Estrategicas')
        cls._body(pdf, 'Stack ranking: #1 decide sobrevivencia.')
        if HAS_MPL and recomendacoes:
            cls._chart(pdf, chart_stack_ranking(recomendacoes), w=155)
        for r in recomendacoes:
            cls._bold(pdf, r.get('titulo',''), 10)
            cls._body(pdf, r.get('descricao',''), 8.5)
            if r.get('citacao'): cls._quote(pdf, r['citacao'])
    
    @classmethod
    def _page_checklist(cls, pdf, checklist):
        cls._header(pdf, 12, title='Checklist: AJUSTAR para GO', is_new=True)
        cls._body(pdf, 'Condicoes mensuraveis para transformar AJUSTAR em GO.')
        for item in checklist:
            y = pdf.get_y()
            if y > 265: pdf.add_page()
            pdf.set_draw_color(*AMBER); pdf.set_line_width(0.6)
            pdf.ellipse(19, pdf.get_y()+1, 5, 5)
            pdf.set_font('DejaVu','B',9); pdf.set_text_color(*DARK); pdf.set_x(27)
            pdf.cell(0,5,_c(item.get('titulo','')),0,1,'L')
            pdf.set_font('DejaVu','',8); pdf.set_text_color(*GRAY); pdf.set_x(27)
            pdf.cell(0,4,_c(f'{item.get("timing","")} - {item.get("justificativa","")}'),0,1,'L')
            pdf.ln(3)
    
    @classmethod
    def _page_predictions(cls, pdf, previsoes):
        cls._header(pdf, 13, title='Previsoes com Intervalo de Confianca')
        if HAS_MPL and previsoes: cls._chart(pdf, chart_confidence_bars(previsoes), w=155)
        for p in previsoes:
            pdf.set_font('DejaVu','B',8.5); pdf.set_text_color(*DARK)
            pdf.cell(95,4.5,_c(p.get('titulo','')),0,0,'L')
            pdf.set_font('Mono','',8); pdf.set_text_color(*TEAL)
            pdf.cell(30,4.5,_c(f'{p.get("probabilidade",0)}% +/-{p.get("margem_erro",0)}'),0,0,'C')
            pdf.set_font('DejaVu','',8); pdf.set_text_color(*GRAY)
            pdf.cell(0,4.5,_c(p.get('descricao','')),0,1,'L'); pdf.ln(1)
    
    @classmethod
    def _page_positioning(cls, pdf, posicionamento):
        cls._header(pdf, 14, title='Posicionamento Percebido vs Desejado')
        players = posicionamento.get('players',[])
        if HAS_MPL and players: cls._chart(pdf, chart_positioning(players), w=130)
        cls._bold(pdf, 'Percebido:')
        cls._body(pdf, posicionamento.get('percebido_descricao',''))
        if posicionamento.get('percebido_citacao'): cls._quote(pdf, posicionamento['percebido_citacao'])
        cls._bold(pdf, 'Desejado:')
        cls._body(pdf, posicionamento.get('desejado_descricao',''))
        if posicionamento.get('desejado_citacao'): cls._quote(pdf, posicionamento['desejado_citacao'])
        evitar = posicionamento.get('rotulos_a_evitar',[])
        if evitar:
            cls._bold(pdf, 'Rotulos a evitar:', 9)
            cls._body(pdf, '. '.join(f'{i+1}. {r}' for i,r in enumerate(evitar)), 8.5)
        if posicionamento.get('posicionamento_vencedor'):
            pdf.set_font('DejaVu','B',12); pdf.set_text_color(*TEAL)
            pdf.cell(0,8,_c(f'Posicionamento vencedor: "{posicionamento["posicionamento_vencedor"]}"'),0,1,'C')
    
    @classmethod
    def _page_roi(cls, pdf, roi):
        cls._header(pdf, 15, title='ROI da Analise', is_new=True)
        cls._body(pdf, 'Custo de errar vs custo de saber.')
        riscos_ev = roi.get('riscos_evitados',[])
        if HAS_MPL and riscos_ev:
            cls._chart(pdf, chart_roi(riscos_ev, roi.get('custo_analise','5k'), roi.get('risco_total_evitado','150k')), w=130)
        for r in riscos_ev:
            pdf.set_font('DejaVu','B',9); pdf.set_text_color(*RED)
            pdf.cell(90,5,_c(r.get('titulo','')),0,0,'L')
            pdf.set_font('Mono','',8); pdf.cell(0,5,_c(r.get('valor_risco','')),0,1,'R')
            pdf.set_font('DejaVu','',8.5); pdf.set_text_color(*GRAY)
            pdf.cell(0,4.5,_c(f'Solucao: {r.get("solucao","")}'),0,1,'L'); pdf.ln(2)
        # ROI highlight box
        pdf.ln(3); y=pdf.get_y()
        pdf.set_fill_color(240,253,250); pdf.rect(18,y,174,18,'F')
        pdf.set_font('DejaVu','B',11); pdf.set_text_color(*TEAL)
        pdf.set_xy(18,y+2); pdf.cell(174,7,_c(f'Investimento: {roi.get("custo_analise","")}'),0,1,'C')
        pdf.set_font('Mono','B',10)
        pdf.cell(174,7,_c(f'Risco evitado: {roi.get("risco_total_evitado","")}  |  ROI: {roi.get("roi_multiplicador","")}'),0,1,'C')
        pdf.ln(5)
        for c in roi.get('citacoes',[]): cls._quote(pdf, c)
    
    @classmethod
    def _page_synthesis(cls, pdf, sintese, veredicto):
        cls._header(pdf, 16, title='Sintese e Direcionamento')
        scores = sintese.get('scores',{})
        if HAS_MPL and scores: cls._chart(pdf, chart_final_radar(scores), w=100)
        vt = veredicto.get('tipo','AJUSTAR')
        vc = AMBER if vt=='AJUSTAR' else (GREEN if vt=='GO' else RED)
        pdf.set_font('DejaVu','B',13); pdf.set_text_color(*vc)
        pdf.cell(0,8,_c(f'VEREDICTO: {vt}'),0,1,'C'); pdf.ln(2)
        cls._body(pdf, f'Cenario mais provavel: {sintese.get("cenario_mais_provavel","")}\nRisco principal: {sintese.get("risco_principal","")}')
        cls._bold(pdf, 'Direcionamento estrategico')
        for d in sintese.get('direcionamento',[]): cls._body(pdf, f'- {d}', 8.5)
    
    @classmethod
    def _page_back(cls, pdf, veredicto):
        pdf.add_page(); pdf.ln(30)
        vt = veredicto.get('tipo','AJUSTAR')
        pdf.set_font('DejaVu','B',14); pdf.set_text_color(*AMBER)
        pdf.cell(0,10,_c(vt),0,1,'C')
        pdf.set_font('Mono','B',28); pdf.set_text_color(*DARK)
        pdf.cell(0,15,_c('A U G U R'),0,1,'C')
        pdf.set_font('DejaVu','I',11); pdf.set_text_color(*TEAL)
        pdf.cell(0,8,_c('Preveja o futuro. Antes que ele aconteca.'),0,1,'C')
        pdf.ln(10)
        pdf.set_font('DejaVu','',9); pdf.set_text_color(*GRAY)
        pdf.cell(0,6,_c('augur.itcast.com.br'),0,1,'C')
        pdf.cell(0,6,_c('contato@itcast.com.br'),0,1,'C')
        pdf.ln(15)
        pdf.set_font('DejaVu','',7); pdf.set_text_color(180,180,180)
        pdf.multi_cell(0,4,_c('Este relatorio foi gerado por IA com base em simulacoes de opiniao publica. Os resultados representam cenarios possiveis e nao garantem resultados futuros.'),0,'C')


# ============================================================
# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================
# api/report.py importa: from ..services.pdf_generator import PDFGenerator, HAS_FPDF
# e chama: PDFGenerator.generate(report_data, pdf_path, client_name=client_name)
# Mantemos compatibilidade sem alterar api/report.py
# ============================================================

HAS_FPDF = True

class PDFGenerator:
    """Wrapper de compatibilidade. Delega para PDFGeneratorV2."""

    @classmethod
    def generate(cls, report_data: dict, output_path: str = None, **kwargs):
        """
        Aceita tanto o formato antigo (report_data com sections de texto)
        quanto o novo (report_data com campo 'structured').
        """
        # Se tem campo structured (pipeline v2), usa direto
        structured = report_data.get("structured", None)
        if structured:
            return PDFGeneratorV2.generate(structured, output_path=output_path)

        # Fallback: montar um structured mínimo a partir do formato antigo
        # para que o PDFGeneratorV2 consiga renderizar algo
        logger.info("PDF fallback: convertendo formato v1 para v2")
        minimal = cls._convert_v1_to_v2(report_data)
        return PDFGeneratorV2.generate(minimal, output_path=output_path)

    @staticmethod
    def _convert_v1_to_v2(report_data: dict) -> dict:
        """Converte report_data v1 (texto livre) para schema v2 (mínimo)."""
        title = report_data.get("title", "Relatorio AUGUR")
        summary = report_data.get("summary", "")
        sections = report_data.get("sections", [])

        # Extrair veredicto do summary
        tipo = "AJUSTAR"
        for v in ["GO", "NO-GO", "AJUSTAR"]:
            if v in summary.upper():
                tipo = v
                break

        # Montar conteúdo de cada seção como texto
        section_contents = {}
        for sec in sections:
            key = sec.get("key", sec.get("title", "").lower().replace(" ", "_"))
            section_contents[key] = sec.get("content", "")

        return {
            "meta": {
                "projeto": re.sub(r'Relat[oó]rio de Previs[aã]o:\s*', '', title).strip(),
                "setor": "varejo_local",
                "tipo_decisao": "novo_negocio",
                "data_geracao": "",
                "modelo_ia": "GPT-5.4",
                "num_agentes": 6,
                "num_rodadas": 5,
                "periodo_simulado_meses": 24,
            },
            "veredicto": {
                "tipo": tipo,
                "score_viabilidade": 52,
                "frase_chave": summary[:200] if summary else title,
                "resumo_executivo": section_contents.get("resumo_executivo", summary),
                "leitura_para_decisao": "",
                "top5_fatos": [],
            },
            "dashboard": {},
            "cenarios": {"cenarios": [], "ponto_bifurcacao": ""},
            "riscos": {"texto_introducao": "", "riscos": []},
            "emocional": {"emocoes": [], "saldo_positivo_vs_negativo": "",
                         "texto_confianca": "", "citacao_confianca": "",
                         "texto_ceticismo": "", "citacao_ceticismo": "",
                         "texto_empolgacao": "", "texto_medo": "", "evolucao_24m": {}},
            "agentes": [],
            "forcas": {"blocos": [], "hierarquia_poder": "", "coalizao_entrante": ""},
            "cronologia": {"fases": []},
            "padroes": [],
            "recomendacoes": [],
            "checklist": [],
            "previsoes": [],
            "posicionamento": {"percebido_descricao": "", "percebido_citacao": "",
                              "desejado_descricao": "", "desejado_citacao": "",
                              "rotulos_a_evitar": [], "posicionamento_vencedor": "",
                              "players": []},
            "roi": {"riscos_evitados": [], "custo_analise": "", "risco_total_evitado": "",
                   "roi_multiplicador": "", "citacoes": []},
            "sintese": {"scores": {}, "veredicto_final": tipo,
                       "cenario_mais_provavel": "", "risco_principal": "",
                       "direcionamento": [], "sinais_consolidacao": [],
                       "sinais_alerta": [], "sinais_risco": []},
        }
