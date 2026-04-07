import importlib
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.locale import get_language_instruction, get_locale, set_locale, t


services_pkg = types.ModuleType("app.services")
services_pkg.__path__ = [str(BACKEND_ROOT / "app" / "services")]
sys.modules.setdefault("app.services", services_pkg)

fake_zep_tools = types.ModuleType("app.services.zep_tools")
fake_zep_tools.ZepToolsService = type("ZepToolsService", (), {})
fake_zep_tools.SearchResult = type("SearchResult", (), {})
fake_zep_tools.InsightForgeResult = type("InsightForgeResult", (), {})
fake_zep_tools.PanoramaResult = type("PanoramaResult", (), {})
fake_zep_tools.InterviewResult = type("InterviewResult", (), {})
sys.modules.setdefault("app.services.zep_tools", fake_zep_tools)

report_agent_module = importlib.import_module("app.services.report_agent")
ReportAgent = report_agent_module.ReportAgent
PLAN_SYSTEM_PROMPT = report_agent_module.PLAN_SYSTEM_PROMPT
SECTION_SYSTEM_PROMPT_TEMPLATE = report_agent_module.SECTION_SYSTEM_PROMPT_TEMPLATE


class LocaleAndReportAgentTests(unittest.TestCase):
    def tearDown(self):
        set_locale("en")

    def test_locale_defaults_to_english_without_context(self):
        set_locale(None)

        self.assertEqual(get_locale(), "en")
        self.assertEqual(get_language_instruction(), "Please respond in English.")

    def test_locale_normalizes_accept_language_header(self):
        app = Flask(__name__)

        with app.test_request_context(headers={"Accept-Language": "en-US,en;q=0.9"}):
            self.assertEqual(get_locale(), "en")

    def test_report_agent_default_outline_tracks_active_locale(self):
        agent = ReportAgent(
            graph_id="graph-1",
            simulation_id="sim-1",
            simulation_requirement="Summarize the impact.",
            llm_client=SimpleNamespace(),
            zep_tools=SimpleNamespace(),
        )

        set_locale("en")
        outline_en = agent._build_default_outline()
        self.assertEqual(outline_en.title, t("report.defaultOutlineTitle"))
        self.assertEqual(outline_en.sections[0].title, t("report.defaultSectionTitle1"))

        set_locale("zh")
        outline_zh = agent._build_default_outline()
        self.assertEqual(outline_zh.title, t("report.defaultOutlineTitle"))
        self.assertEqual(outline_zh.sections[0].title, t("report.defaultSectionTitle1"))

    def test_report_prompts_follow_ui_language_not_source_language(self):
        set_locale("en")
        agent = ReportAgent(
            graph_id="graph-1",
            simulation_id="sim-1",
            simulation_requirement="彩色 G 标志测试舆情预测",
            llm_client=SimpleNamespace(),
            zep_tools=SimpleNamespace(),
        )

        plan_prompt = PLAN_SYSTEM_PROMPT.format(
            report_language_instruction=agent._get_report_language_instruction(),
        )
        section_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title="Simulation Prediction Report",
            report_summary="Summary",
            simulation_requirement="彩色 G 标志测试舆情预测",
            section_title="Core Findings",
            tools_description=agent._get_tools_description(),
            report_language_instruction=agent._get_report_language_instruction(),
            quote_style_instruction=agent._get_quote_style_instruction(),
        )

        self.assertIn("Please respond in English.", plan_prompt)
        self.assertIn("Required Output Language: Please respond in English.", section_prompt)
        self.assertNotIn("If the simulation requirements and source materials are in Chinese", section_prompt)
        self.assertIn("Available tools:", agent._get_tools_description())
        self.assertNotIn("可用工具", agent._get_tools_description())


if __name__ == "__main__":
    unittest.main()
