#models.py 
from sqlalchemy import Column, Integer, String
# Assuming Base is defined in your root database.py
from database import Base 

class TemplateConfig(Base):
    """
    SQLAlchemy ORM Model for the TemplateConfig table.
    """
    __tablename__ = "TemplateConfig"
    
    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    HieSource = Column(String(200), nullable=False)
    SourceType = Column(String(50), nullable=False)
    LiquidTemplate = Column(String(255), nullable=False, unique=True)
    AzureStoragePath = Column(String(500), nullable=False)

    def __repr__(self):
        return f"<TemplateConfig(Id={self.Id}, Template='{self.LiquidTemplate}')>"