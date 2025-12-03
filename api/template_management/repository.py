from app.database import get_connection

class TemplateRepository:

    @staticmethod
    def get_template(template_name: str) -> str | None:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT TemplateContent 
        FROM LiquidTemplates 
        WHERE TemplateName = ?
        """

        cursor.execute(query, template_name)
        row = cursor.fetchone()

        return row[0] if row else None

    @staticmethod
    def save_template(template_name: str, template_content: str):
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        MERGE LiquidTemplates AS target
        USING (SELECT ? AS TemplateName) AS source
        ON (target.TemplateName = source.TemplateName)
        WHEN MATCHED THEN
            UPDATE SET TemplateContent = ?, UpdatedOn = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (TemplateName, TemplateContent) VALUES (?, ?);
        """

        cursor.execute(query, (template_name, template_content, template_name, template_content))
        conn.commit()
