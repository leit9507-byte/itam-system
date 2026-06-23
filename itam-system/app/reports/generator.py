from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings


class AuditReportGenerator:
    def __init__(self):
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.settings = get_settings()

    def generate(self, audit_result: dict) -> str:
        template = self.env.get_template("audit_report.html")
        html = template.render(result=audit_result)
        output_path = Path(self.settings.audit_report_path)
        output_path.write_text(html, encoding="utf-8")
        return str(output_path.resolve())
