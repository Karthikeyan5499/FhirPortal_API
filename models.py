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
    
class FileMetadata(Base):
    """
    SQLAlchemy ORM Model for FileMetadata table
    """
    __tablename__ = "FileMetadata"
    
    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Source = Column(String(200), nullable=False)
    SourceType = Column(String(50), nullable=False)
    FileName = Column(String(300), nullable=False)
    BundleId = Column(String(200), nullable=True)
    FlowType = Column(String(100), nullable=True)
    UploadedBy = Column(String(100), nullable=True)
    Status = Column(String(50), nullable=True)
    ValidationStatus = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<FileMetadata(Id={self.Id}, FileName='{self.FileName}', Status='{self.Status}')>"


class SourceMaster(Base):
    """
    SQLAlchemy ORM Model for SourceMaster table
    """
    __tablename__ = "SourceMaster"
    
    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Source = Column(String(200), nullable=False)
    SourceType = Column(String(100), nullable=False)

    def __repr__(self):
        return f"<SourceMaster(Id={self.Id}, Source='{self.Source}', SourceType='{self.SourceType}')>"