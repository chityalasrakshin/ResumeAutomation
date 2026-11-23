from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from docx import Document
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from lxml import etree

from resume_automation.cli import process
from resume_automation.extraction import extract_resume_with_claude
from resume_automation.paths import MASTER_TEMPLATE as MASTER
from resume_automation.pipeline import build_graph
from resume_automation.template_engine import populate_coforge_document


def payload():
    projects = [dict(organization_name=f"Org {i}", project_title=f"Project {i}",
                     role="Engineer", duration=f"January 202{i}", description="Reviewed data.",
                     responsibilities=["Checked records."]) for i in (3, 2, 1)]
    return dict(full_name="Test Candidate", profile_summary=["Builds tools."],
                technical_skills={"Languages": ["Python"]}, certifications=["Certificate A"],
                projects=projects, missing_sections=[], confidence_score=0.9)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.source = self.folder / "input.docx"
        self.data = payload()
        doc = Document()
        doc.add_paragraph("Test Candidate\nBuilds tools.\nPython\nCertificate A")
        for project in self.data["projects"]:
            for value in project.values():
                doc.add_paragraph(value if isinstance(value, str) else value[0])
        doc.save(self.source)

    def test_render(self):
        self.data["projects"][1]["duration"] = ""
        target = self.folder / "out.docx"
        populate_coforge_document(self.data, MASTER, target)
        doc = Document(target)
        self.assertEqual(len(doc.tables), 6)
        skills = doc.tables[1].rows[1].cells[0].paragraphs
        self.assertEqual([(p.text, p.runs[0].bold) for p in skills],
                         [("Languages", True), ("Python", False)])
        master = Document(MASTER).tables[3]
        for i, tbl in enumerate(doc.tables[3:]):
            self.assertTrue(tbl.cell(0, 0).text.endswith(self.data["projects"][i]["organization_name"]))
            self.assertEqual(tbl.rows[4].cells[-1].paragraphs[0].style.name, "List Bullet")
            for xpath in ("./w:tblPr", "./w:tblGrid", "./w:tr/w:tc/w:tcPr"):
                self.assertEqual([etree.tostring(e) for e in tbl._tbl.xpath(xpath)],
                                 [etree.tostring(e) for e in master._tbl.xpath(xpath)])
        self.assertEqual(doc.tables[4].rows[2].cells[1].text, "")
        self.assertEqual(doc.tables[4].rows[2].cells[-1].text, "Project 2")

    def test_automatic_and_repeat(self):
        extractor = Mock(return_value=self.data)
        graph = build_graph(template_path=MASTER, output_dir=self.folder, extractor=extractor)
        status = process(graph, self.source)
        self.assertTrue(status.startswith("Generated "), status)
        self.assertTrue(Path(status.removeprefix("Generated ")).is_file())
        self.assertEqual(process(graph, self.source), status)
        extractor.assert_called_once()

    def test_persistent_review(self):
        self.data["projects"][1]["duration"] = "January 2023"  # belongs to another project
        database = str(self.folder / "state.sqlite")
        with SqliteSaver.from_conn_string(database) as saver:
            graph = build_graph(saver, MASTER, self.folder, lambda _: self.data)
            status = process(graph, self.source)
            self.assertTrue(status.startswith("Review "), status)
            self.assertEqual(list(self.folder.rglob("*Generated.docx")), [])
        with SqliteSaver.from_conn_string(database) as saver:
            graph = build_graph(saver, MASTER, self.folder)
            config = {"configurable": {"thread_id": status.split()[1]}}
            self.assertIn("duration", str(graph.get_state(config).interrupts[0].value["issues"]))
            self.data["projects"][1]["duration"] = ""
            result = graph.invoke(Command(resume={"approved": True, "corrected_payload": self.data}), config)
            self.assertTrue(Path(result["output_docx_path"]).is_file())

    @patch("resume_automation.extraction.Anthropic")
    def test_tool_extraction(self, sdk):
        client = sdk.return_value.__enter__.return_value
        block = Mock(type="tool_use", input=self.data)
        block.name = "export_coforge_resume"
        response = client.messages.create.return_value
        response.stop_reason, response.content = "tool_use", [block]
        result = extract_resume_with_claude(str(self.source), "test")
        self.assertEqual(result["projects"], self.data["projects"])
        kwargs = client.messages.create.call_args.kwargs
        self.assertEqual(kwargs["temperature"], 0.0)
        self.assertEqual(kwargs["tool_choice"]["name"], block.name)
        import json
        block.input = {**self.data, "projects": json.dumps(self.data["projects"])}
        self.assertEqual(extract_resume_with_claude(str(self.source), "test"), result)
        response.stop_reason = "max_tokens"
        with self.assertRaises(ValueError):
            extract_resume_with_claude(str(self.source), "test")
