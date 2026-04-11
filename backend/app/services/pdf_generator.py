"""
AUGUR — Gerador de PDF Profissional (Nível McKinsey)
Requer: pip install fpdf2 --break-system-packages
"""
import os, re, logging, json
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    FPDF = object
    HAS_FPDF = False
    logger.warning("fpdf2 nao instalado")

class C:
    ACCENT=(0,229,195); PURPLE=(124,111,247); DANGER=(255,90,90); GOLD=(245,166,35)
    BG_DARK=(9,9,15); TEXT=(240,240,255); BODY=(50,55,70); MUTED=(100,105,130)
    DIM=(150,155,175); WHITE=(255,255,255); LIGHT=(247,247,252); BORDER=(230,232,240)
    A_LIGHT=(230,252,248); P_LIGHT=(240,238,255); D_LIGHT=(255,240,240)

class AugurPDF(FPDF):
    def __init__(self, title="Relatório", client=""):
        super().__init__()
        self.report_title = title
        self.client = client
        self.set_auto_page_break(auto=True, margin=28)
    def header(self):
        if self.page_no() <= 2: return
        self.set_fill_color(*C.ACCENT); self.rect(0,0,self.w,1.5,"F")
        self.set_y(5); self.set_font("Helvetica","",7); self.set_text_color(*C.DIM)
        self.cell(0,5,"AUGUR",align="L"); self.cell(0,5,self.report_title[:55],align="R"); self.ln(8)
    def footer(self):
        if self.page_no() <= 2: return
        self.set_y(-16); self.set_draw_color(*C.BORDER); self.set_line_width(0.2)
        self.line(15,self.get_y(),self.w-15,self.get_y()); self.ln(3)
        self.set_font("Helvetica","",7); self.set_text_color(*C.DIM)
        self.cell(self.w/2-15,4,"augur.itcast.com.br"); self.cell(self.w/2-15,4,f"Pagina {self.page_no()-2}",align="R")

class PDFGenerator:
    @classmethod
    def generate(cls, report_data, output_path, client_name=""):
        if not HAS_FPDF: raise RuntimeError("fpdf2 nao instalado")
        o = report_data.get("outline",{})
        title = o.get("title","Relatorio de Previsao")
        summary = o.get("summary","")
        sections = o.get("sections",[])
        created = report_data.get("completed_at") or report_data.get("created_at","")
        pdf = AugurPDF(title=title, client=client_name)
        pdf.set_title(title); pdf.set_author("AUGUR by itcast")
        cls._cover(pdf, title, summary, created, client_name)
        cls._toc(pdf, sections)
        total = len([s for s in sections if (s.get("content","")).strip()])
        n = 0
        for i,s in enumerate(sections):
            c = s.get("content","")
            if not c.strip(): continue
            n += 1
            cls._section(pdf, n, s.get("title",f"Secao {i+1}"), c, total)
        cls._closing(pdf, title, summary, sections)
        cls._back(pdf)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pdf.output(output_path)
        return output_path

    @classmethod
    def _cover(cls, pdf, title, summary, created, client):
        pdf.add_page()
        pdf.set_fill_color(*C.BG_DARK); pdf.rect(0,0,210,297,"F")
        pdf.set_fill_color(*C.ACCENT); pdf.rect(0,0,5,297,"F")
        pdf.set_fill_color(*C.PURPLE); pdf.ellipse(130,-30,130,130,"F")
        pdf.set_fill_color(*C.BG_DARK); pdf.ellipse(135,-25,120,120,"F")
        pdf.set_y(80); pdf.set_font("Helvetica","B",16); pdf.set_text_color(*C.ACCENT)
        pdf.cell(0,10,"AUGUR",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.set_font("Helvetica","",8); pdf.set_text_color(*C.DIM)
        pdf.cell(0,5,"PLATAFORMA DE PREVISAO DE MERCADO POR IA",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(18); pdf.set_draw_color(*C.ACCENT); pdf.set_line_width(1.5); pdf.line(40,pdf.get_y(),170,pdf.get_y())
        pdf.ln(18); pdf.set_font("Helvetica","B",22); pdf.set_text_color(*C.TEXT)
        pdf.multi_cell(0,12,cls._c(title),align="C"); pdf.ln(10)
        if summary:
            pdf.set_font("Helvetica","",10); pdf.set_text_color(*C.DIM)
            pdf.set_x(25); pdf.multi_cell(160,6,cls._c(summary)[:300],align="C")
        if client:
            pdf.ln(18); pdf.set_font("Helvetica","",10); pdf.set_text_color(*C.ACCENT)
            pdf.cell(0,6,f"Preparado para: {client}",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.set_y(260); pdf.set_font("Helvetica","",8); pdf.set_text_color(*C.DIM)
        d = cls._date(created)
        if d: pdf.cell(0,5,d,align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.cell(0,5,"AUGUR by itcast",align="C")

    @classmethod
    def _toc(cls, pdf, sections):
        pdf.add_page()
        pdf.set_fill_color(*C.WHITE); pdf.rect(0,0,210,297,"F")
        pdf.set_fill_color(*C.ACCENT); pdf.rect(0,0,4,297,"F")
        pdf.set_y(30); pdf.set_font("Helvetica","B",22); pdf.set_text_color(*C.BODY)
        pdf.cell(0,12,"Sumario",new_x="LMARGIN",new_y="NEXT")
        pdf.set_draw_color(*C.ACCENT); pdf.set_line_width(2); pdf.line(15,pdf.get_y()+2,55,pdf.get_y()+2)
        pdf.ln(12)
        n=0
        for s in sections:
            if not (s.get("content","")).strip(): continue
            n+=1
            pdf.set_font("Helvetica","B",11); pdf.set_text_color(*C.ACCENT)
            pdf.cell(12,9,f"{n:02d}"); pdf.set_font("Helvetica","",11); pdf.set_text_color(*C.BODY)
            pdf.cell(0,9,s.get("title","")[:55],new_x="LMARGIN",new_y="NEXT")
            pdf.set_draw_color(*C.BORDER); pdf.set_line_width(0.15); pdf.line(15,pdf.get_y(),195,pdf.get_y())

    @classmethod
    def _section(cls, pdf, num, title, content, total):
        pdf.add_page()
        pdf.set_fill_color(*C.WHITE); pdf.rect(0,0,210,297,"F")
        col = cls._scol(title)
        pdf.set_fill_color(*col); pdf.rect(0,0,4,35,"F")
        pdf.set_y(15); pdf.set_font("Helvetica","B",8); pdf.set_text_color(*col)
        pdf.cell(0,5,f"SECAO {num:02d} DE {total}",new_x="LMARGIN",new_y="NEXT"); pdf.ln(2)
        pdf.set_font("Helvetica","B",17); pdf.set_text_color(*C.BODY)
        pdf.multi_cell(0,9,title); pdf.ln(1)
        pdf.set_draw_color(*col); pdf.set_line_width(1.5); pdf.line(15,pdf.get_y(),55,pdf.get_y())
        pdf.ln(8)
        cls._render(pdf, content)

    @classmethod
    def _closing(cls, pdf, title, summary, sections):
        pdf.add_page()
        pdf.set_fill_color(*C.A_LIGHT); pdf.rect(0,0,210,297,"F")
        pdf.set_fill_color(*C.ACCENT); pdf.rect(0,0,210,3,"F")
        su = (summary or "").upper()
        if "NAO LANCAR" in su or "NÃO LANÇAR" in su or "NO-GO" in su:
            v,vc = "NAO LANCAR",C.DANGER
        elif "AJUSTAR" in su:
            v,vc = "AJUSTAR ANTES",C.GOLD
        elif "LANCAR" in su or "LANÇAR" in su:
            v,vc = "LANCAR",C.ACCENT
        else:
            v,vc = "EM ANALISE",C.MUTED
        pdf.set_y(50); pdf.set_font("Helvetica","B",28); pdf.set_text_color(*vc)
        pdf.cell(0,15,v,align="C",new_x="LMARGIN",new_y="NEXT"); pdf.ln(8)
        if summary:
            cs = re.sub(r'VEREDICTO:[^.]*\.','',summary,flags=re.I).strip()
            pdf.set_font("Helvetica","",10); pdf.set_text_color(*C.BODY)
            pdf.set_x(30); pdf.multi_cell(150,6,cls._c(cs)[:350],align="C")
        pdf.ln(12)
        trio = cls._trio(sections)
        bw=55; sx=(210-bw*3-10)/2; y=pdf.get_y()
        for i,(lbl,val) in enumerate(trio):
            x=sx+i*(bw+5)
            bg=C.A_LIGHT if i==1 else C.LIGHT
            pdf.set_fill_color(*bg); pdf.set_draw_color(*(C.ACCENT if i==1 else C.BORDER))
            pdf.set_line_width(0.5); pdf.rounded_rect(x,y,bw,48,4,"DF")
            pdf.set_xy(x+2,y+8); pdf.set_font("Helvetica","B",7); pdf.set_text_color(*C.DIM)
            pdf.cell(bw-4,4,lbl,align="C")
            pdf.set_xy(x+2,y+17); pdf.set_font("Helvetica","B",9); pdf.set_text_color(*C.BODY)
            pdf.multi_cell(bw-4,5,val[:55],align="C")
        pdf.set_y(220); pdf.set_font("Helvetica","B",14); pdf.set_text_color(*C.ACCENT)
        pdf.cell(0,8,"AUGUR",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.set_font("Helvetica","I",10); pdf.set_text_color(*C.DIM)
        pdf.cell(0,6,"Preveja o futuro. Antes que ele aconteca.",align="C")

    @classmethod
    def _back(cls, pdf):
        pdf.add_page()
        pdf.set_fill_color(*C.BG_DARK); pdf.rect(0,0,210,297,"F")
        pdf.set_fill_color(*C.ACCENT); pdf.rect(0,293,210,4,"F")
        pdf.set_y(110); pdf.set_font("Helvetica","B",18); pdf.set_text_color(*C.TEXT)
        pdf.cell(0,10,"AUGUR",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(4); pdf.set_font("Helvetica","",10); pdf.set_text_color(*C.DIM)
        pdf.cell(0,6,"Preveja o futuro. Antes que ele aconteca.",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(20); pdf.set_font("Helvetica","",8)
        pdf.cell(0,5,"augur.itcast.com.br",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.cell(0,5,"contato@itcast.com.br",align="C",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(12); pdf.set_font("Helvetica","",7); pdf.set_text_color(100,100,120); pdf.set_x(30)
        pdf.multi_cell(150,4,"Este relatorio foi gerado por inteligencia artificial. Os resultados representam cenarios possiveis e nao garantem resultados futuros.",align="C")

    @classmethod
    def _render(cls, pdf, content):
        for line in cls._c(content).split("\n"):
            s = line.strip()
            if not s: pdf.ln(3); continue
            if pdf.get_y() > 260:
                pdf.add_page(); pdf.set_fill_color(*C.WHITE); pdf.rect(0,0,210,297,"F")
            if s.startswith("**") and s.endswith("**"):
                pdf.ln(3); pdf.set_font("Helvetica","B",12); pdf.set_text_color(*C.BODY)
                pdf.multi_cell(0,7,s.strip("* ")); pdf.ln(2); continue
            m = re.match(r'\*\*#?\d*\s*(.+?)\*\*', s)
            if m and len(s)<100:
                pdf.ln(3); pdf.set_font("Helvetica","B",11); pdf.set_text_color(*C.PURPLE)
                pdf.multi_cell(0,7,m.group(1).strip()); pdf.ln(1); continue
            if s.startswith(">") or (s.startswith('"') and s.endswith('"')):
                t=s.lstrip('> "').rstrip('"'); ys=pdf.get_y()
                pdf.set_x(20); pdf.set_font("Helvetica","I",9); pdf.set_text_color(80,80,120)
                pdf.set_fill_color(*C.P_LIGHT); pdf.multi_cell(170,5.5,f'"{t}"',fill=True)
                pdf.set_fill_color(*C.PURPLE); pdf.rect(17,ys,2,pdf.get_y()-ys,"F"); pdf.ln(3); continue
            if s[:2] in ("- ","* ","\u2022 "):
                t=s[2:].strip(); pdf.set_font("Helvetica","",9.5); pdf.set_text_color(*C.ACCENT)
                pdf.cell(8,6,"\u25cf"); pdf.set_text_color(*C.BODY); pdf.multi_cell(170,6,t.replace("**","")); pdf.ln(1); continue
            nm = re.match(r'^(\d+)[.)]\s+(.+)', s)
            if nm:
                pdf.set_font("Helvetica","B",10); pdf.set_text_color(*C.ACCENT); pdf.cell(10,6,f"{nm.group(1)}.")
                pdf.set_font("Helvetica","",9.5); pdf.set_text_color(*C.BODY); pdf.multi_cell(168,6,nm.group(2).replace("**","")); pdf.ln(2); continue
            if re.search(r'\d{1,3}\s*%',s) and ('probabilidade' in s.lower() or 'impacto' in s.lower()):
                pdf.set_font("Helvetica","B",9); pdf.set_text_color(*C.GOLD); pdf.multi_cell(0,6,s.replace("**","")); pdf.ln(2); continue
            pdf.set_font("Helvetica","",9.5); pdf.set_text_color(*C.BODY); pdf.multi_cell(0,6,s.replace("**","")); pdf.ln(2)

    @staticmethod
    def _c(t):
        t = re.sub(r'^#{1,6}\s+','',t or '',flags=re.MULTILINE)
        t = re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',t)
        t = t.replace("---","").replace("___","").strip()
        # Sanitizar Unicode para Latin-1 (Helvetica)
        t = t.replace('—', '-').replace('–', '-').replace('‒', '-')
        t = t.replace('‘', "'").replace('’', "'")
        t = t.replace('“', '"').replace('”', '"')
        t = t.replace('…', '...').replace('•', '*')
        t = t.replace('·', '*').replace('‣', '>')
        t = t.replace('→', '->').replace('←', '<-')
        t = t.replace('✓', 'v').replace('✔', 'v')
        t = t.replace('✕', 'x').replace('✖', 'x')
        t = t.replace(' ', ' ').replace('​', '').replace('﻿', '')
        # Fallback: replace any remaining non-latin1 chars
        try:
            t.encode('latin-1')
        except UnicodeEncodeError:
            t = t.encode('latin-1', errors='replace').decode('latin-1')
        return t
    @staticmethod
    def _date(d):
        if not d: return ""
        try: dt=datetime.fromisoformat(d.replace("Z","+00:00")); return dt.strftime("%d/%m/%Y as %H:%M")
        except: return str(d)[:19]
    @staticmethod
    def _scol(t):
        t=t.lower()
        if 'resum' in t: return C.ACCENT
        if 'cenar' in t: return C.PURPLE
        if 'risco' in t or 'fator' in t: return C.DANGER
        if 'recomend' in t: return C.GOLD
        if 'emocio' in t: return (233,30,156)
        if 'comunica' in t: return (255,152,0)
        if 'posicion' in t: return C.PURPLE
        if 'previs' in t: return (29,161,242)
        if 'valor' in t: return C.GOLD
        return C.ACCENT
    @staticmethod
    def _trio(sections):
        ce=ac=ri="Ver relatorio"
        for s in sections:
            t=(s.get("title","")).lower(); c=s.get("content","")
            if 'cenar' in t:
                m=re.search(r'\*\*([^*]{5,50})\*\*',c)
                if m: ce=m.group(1).strip()
            if 'recomend' in t:
                m=re.search(r'\*\*#?\d*\s*([^*]{5,60})\*\*',c) or re.search(r'1[.)]\s+(.{10,60})',c)
                if m: ac=m.group(1).strip()
            if 'risco' in t or 'fator' in t:
                m=re.search(r'\*\*#?\d*\s*([^*]{5,60})\*\*',c) or re.search(r'1[.)]\s+(.{10,60})',c)
                if m: ri=m.group(1).strip()
        return [("CENARIO MAIS PROVAVEL",ce),("ACAO PRIORITARIA",ac),("RISCO PRINCIPAL",ri)]
