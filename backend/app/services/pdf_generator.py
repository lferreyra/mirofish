"""
AUGUR — Gerador de PDF Profissional
Gera relatório em PDF com capa, sumário, seções formatadas e rodapé.
Requer: pip install fpdf2 --break-system-packages
"""
import json
import os
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False
    logger.warning("fpdf2 não instalado. PDF profissional indisponível. Instale com: pip install fpdf2")


class AugurPDF(FPDF):
    """PDF customizado com header/footer AUGUR."""
    
    def __init__(self, report_title: str = "Relatório de Previsão", client_name: str = ""):
        super().__init__()
        self.report_title = report_title
        self.client_name = client_name
        self._page_title = ""
        self.set_auto_page_break(auto=True, margin=25)
    
    def header(self):
        if self.page_no() == 1:
            return  # Capa não tem header
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(130, 130, 150)
        self.cell(0, 8, f"AUGUR — {self.report_title}", align="L")
        self.ln(2)
        self.set_draw_color(0, 229, 195)
        self.set_line_width(0.5)
        self.line(10, 14, self.w - 10, 14)
        self.ln(8)
    
    def footer(self):
        if self.page_no() == 1:
            return  # Capa não tem footer
        self.set_y(-20)
        self.set_draw_color(200, 200, 210)
        self.set_line_width(0.2)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(3)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(150, 150, 170)
        self.cell(0, 5, f"Página {self.page_no() - 1}", align="C")


class PDFGenerator:
    """Gera PDF profissional a partir de um Report."""
    
    # Cores AUGUR
    ACCENT = (0, 229, 195)
    PURPLE = (124, 111, 247)
    DANGER = (255, 90, 90)
    GOLD = (245, 166, 35)
    TEXT = (30, 30, 50)
    MUTED = (100, 100, 130)
    BG_LIGHT = (245, 245, 250)
    
    @classmethod
    def generate(cls, report_data: Dict[str, Any], output_path: str, client_name: str = "") -> str:
        """
        Gera PDF profissional do relatório.
        
        Args:
            report_data: dados do relatório (outline, sections, etc)
            output_path: caminho do arquivo PDF
            client_name: nome do cliente (opcional, para personalização)
        
        Returns:
            caminho do PDF gerado
        """
        if not HAS_FPDF:
            raise RuntimeError("fpdf2 não instalado. Execute: pip install fpdf2 --break-system-packages")
        
        outline = report_data.get("outline", {})
        title = outline.get("title", "Relatório de Previsão")
        summary = outline.get("summary", "")
        sections = outline.get("sections", [])
        created_at = report_data.get("completed_at") or report_data.get("created_at", "")
        
        pdf = AugurPDF(report_title=title, client_name=client_name)
        pdf.set_title(title)
        pdf.set_author("AUGUR by itcast")
        
        # ═══ CAPA ═══
        cls._add_cover(pdf, title, summary, created_at, client_name)
        
        # ═══ SUMÁRIO ═══
        cls._add_toc(pdf, sections)
        
        # ═══ SEÇÕES ═══
        for i, section in enumerate(sections):
            sec_title = section.get("title", f"Seção {i+1}")
            sec_content = section.get("content", "")
            if not sec_content.strip():
                continue
            cls._add_section(pdf, i + 1, sec_title, sec_content)
        
        # ═══ CONTRA-CAPA ═══
        cls._add_back_cover(pdf)
        
        # Salvar
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pdf.output(output_path)
        logger.info(f"PDF gerado: {output_path} ({pdf.page_no()} páginas)")
        return output_path
    
    @classmethod
    def _add_cover(cls, pdf: AugurPDF, title: str, summary: str, created_at: str, client_name: str):
        """Página de capa profissional."""
        pdf.add_page()
        
        # Background accent bar
        pdf.set_fill_color(*cls.ACCENT)
        pdf.rect(0, 0, 8, 297, "F")
        
        # Logo area
        pdf.set_y(60)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*cls.ACCENT)
        pdf.cell(0, 10, "AUGUR", align="C", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*cls.MUTED)
        pdf.cell(0, 6, "Plataforma de Previsão de Mercado por IA", align="C", new_x="LMARGIN", new_y="NEXT")
        
        # Linha decorativa
        pdf.ln(15)
        pdf.set_draw_color(*cls.ACCENT)
        pdf.set_line_width(1)
        pdf.line(60, pdf.get_y(), 150, pdf.get_y())
        pdf.ln(15)
        
        # Título
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(*cls.TEXT)
        # Word wrap manual para título grande
        pdf.multi_cell(0, 12, title, align="C")
        pdf.ln(10)
        
        # Summary
        if summary:
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*cls.MUTED)
            pdf.multi_cell(0, 7, cls._clean_md(summary), align="C")
        
        # Client name
        if client_name:
            pdf.ln(20)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*cls.MUTED)
            pdf.cell(0, 6, f"Preparado para: {client_name}", align="C", new_x="LMARGIN", new_y="NEXT")
        
        # Date
        pdf.set_y(250)
        date_str = ""
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                date_str = dt.strftime("%d/%m/%Y às %H:%M")
            except:
                date_str = str(created_at)[:19]
        
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*cls.MUTED)
        pdf.cell(0, 5, f"Gerado em {date_str}" if date_str else "", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, "AUGUR by itcast · augur.itcast.com.br", align="C")
    
    @classmethod
    def _add_toc(cls, pdf: AugurPDF, sections: list):
        """Sumário."""
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*cls.TEXT)
        pdf.cell(0, 12, "Sumário", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        pdf.set_draw_color(*cls.ACCENT)
        pdf.set_line_width(0.8)
        pdf.line(10, pdf.get_y(), 60, pdf.get_y())
        pdf.ln(10)
        
        for i, section in enumerate(sections):
            title = section.get("title", f"Seção {i+1}")
            content = section.get("content", "")
            if not content.strip():
                continue
            
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*cls.ACCENT)
            pdf.cell(10, 8, f"{i+1:02d}")
            
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*cls.TEXT)
            pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(5)
    
    @classmethod
    def _add_section(cls, pdf: AugurPDF, num: int, title: str, content: str):
        """Adiciona uma seção ao PDF."""
        pdf.add_page()
        
        # Section number + title
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*cls.ACCENT)
        pdf.cell(0, 6, f"SEÇÃO {num:02d}", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*cls.TEXT)
        pdf.multi_cell(0, 9, title)
        pdf.ln(3)
        
        # Accent line
        pdf.set_draw_color(*cls.ACCENT)
        pdf.set_line_width(0.8)
        pdf.line(10, pdf.get_y(), 50, pdf.get_y())
        pdf.ln(8)
        
        # Content — parse markdown-like formatting
        cls._render_content(pdf, content)
    
    @classmethod
    def _render_content(cls, pdf: AugurPDF, content: str):
        """Renderiza conteúdo markdown-like em PDF."""
        content = cls._clean_md(content)
        lines = content.split("\n")
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                pdf.ln(3)
                continue
            
            # Bold headings (** **)
            if stripped.startswith("**") and stripped.endswith("**"):
                text = stripped.strip("*").strip()
                pdf.ln(3)
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(*cls.TEXT)
                pdf.multi_cell(0, 7, text)
                pdf.ln(2)
                continue
            
            # Blockquote (>)
            if stripped.startswith(">"):
                text = stripped.lstrip("> ").strip('"').strip()
                pdf.set_fill_color(*cls.BG_LIGHT)
                pdf.set_draw_color(*cls.PURPLE)
                x = pdf.get_x()
                y = pdf.get_y()
                pdf.set_x(x + 5)
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(80, 80, 120)
                pdf.multi_cell(pdf.w - 30, 6, f'"{text}"', fill=True)
                # Left border
                pdf.set_line_width(1.5)
                pdf.line(x + 3, y, x + 3, pdf.get_y())
                pdf.ln(3)
                continue
            
            # Bullet points (- or •)
            if stripped.startswith("- ") or stripped.startswith("• "):
                text = stripped[2:].strip()
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*cls.TEXT)
                pdf.cell(8, 6, "•")
                pdf.multi_cell(pdf.w - 28, 6, cls._inline_bold(pdf, text))
                continue
            
            # Numbered items (1. 2. etc)
            num_match = re.match(r'^(\d+)\.\s+(.+)', stripped)
            if num_match:
                num = num_match.group(1)
                text = num_match.group(2)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(*cls.ACCENT)
                pdf.cell(10, 6, f"{num}.")
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*cls.TEXT)
                pdf.multi_cell(pdf.w - 30, 6, text)
                pdf.ln(1)
                continue
            
            # Regular paragraph
            # Handle inline bold
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*cls.TEXT)
            # Simple bold handling
            text = stripped
            if "**" in text:
                text = text.replace("**", "")
            pdf.multi_cell(0, 6, text)
            pdf.ln(1)
    
    @classmethod
    def _add_back_cover(cls, pdf: AugurPDF):
        """Contra-capa."""
        pdf.add_page()
        
        pdf.set_fill_color(*cls.ACCENT)
        pdf.rect(0, 0, 8, 297, "F")
        
        pdf.set_y(100)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*cls.TEXT)
        pdf.cell(0, 10, "AUGUR", align="C", new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*cls.MUTED)
        pdf.cell(0, 7, "Preveja o futuro. Antes que ele aconteça.", align="C", new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(20)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "augur.itcast.com.br", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, "contato@itcast.com.br", align="C", new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(180, 180, 200)
        pdf.multi_cell(0, 5, 
            "Este relatório foi gerado por inteligência artificial com base em simulações de opinião pública. "
            "Os resultados representam cenários possíveis e não garantem resultados futuros. "
            "Recomenda-se utilizar estas previsões como complemento a outras análises de mercado.", 
            align="C"
        )
    
    @staticmethod
    def _clean_md(text: str) -> str:
        """Remove formatação markdown pesada."""
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = text.replace("---", "").replace("___", "")
        return text.strip()
    
    @staticmethod
    def _inline_bold(pdf, text: str) -> str:
        """Remove ** markers — fpdf2 não suporta inline bold em multi_cell."""
        return text.replace("**", "")
