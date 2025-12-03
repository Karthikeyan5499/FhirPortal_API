from app.api.template_management.repository import TemplateRepository
from app.common.exceptions import NotFoundException

class TemplateService:

    @staticmethod
    def get_template(name: str):
        content = TemplateRepository.get_template(name)
        if not content:
            raise NotFoundException(f"Template '{name}' not found.")
        return {"templateName": name, "templateContent": content}

    @staticmethod
    def save_template(name: str, content: str):
        TemplateRepository.save_template(name, content)
        return {"status": "success", "templateName": name}
