"""
Database models for Duties of the Hearts translation project.

The book structure is:
- Chapters (e.g., "Introduction of the Author", "First Treatise on Unity")
- Some chapters have Sections (e.g., "Introduction", unnamed sections)
- All sections contain Paragraphs (the actual Hebrew text)
- Each Paragraph can have multiple Translations (different prompts/versions)
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()


class Chapter(Base):
    """
    Represents a chapter in the book.
    Example: "Introduction of the Author", "First Treatise on Unity"
    """
    __tablename__ = 'chapters'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False, unique=True)
    chapter_number = Column(Integer, nullable=False, unique=True)  # Order in the book
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sections = relationship("Section", back_populates="chapter", cascade="all, delete-orphan", order_by="Section.section_number")
    paragraphs = relationship("Paragraph", back_populates="chapter", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chapter(number={self.chapter_number}, title='{self.title}')>"


class Section(Base):
    """
    Represents a section within a chapter.
    Some chapters have sections, some don't.
    Example: "Introduction" section in "First Treatise on Unity"
    """
    __tablename__ = 'sections'
    
    id = Column(Integer, primary_key=True)
    chapter_id = Column(Integer, ForeignKey('chapters.id'), nullable=False)
    title = Column(String(500), nullable=True)  # Can be empty string or None
    section_number = Column(Integer, nullable=False)  # Order within chapter (1-indexed)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chapter = relationship("Chapter", back_populates="sections")
    paragraphs = relationship("Paragraph", back_populates="section", cascade="all, delete-orphan", order_by="Paragraph.paragraph_number")
    
    # Ensure section_number is unique within a chapter
    __table_args__ = (
        UniqueConstraint('chapter_id', 'section_number', name='_chapter_section_uc'),
    )
    
    def __repr__(self):
        return f"<Section(chapter_id={self.chapter_id}, number={self.section_number}, title='{self.title}')>"


class Paragraph(Base):
    """
    Represents a single paragraph of original Hebrew text.
    Always belongs to a chapter, and optionally to a section.
    """
    __tablename__ = 'paragraphs'
    
    id = Column(Integer, primary_key=True)
    chapter_id = Column(Integer, ForeignKey('chapters.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)  # NULL for sectionless chapters
    paragraph_number = Column(Integer, nullable=False)  # Order within section/chapter (1-indexed)
    text = Column(Text, nullable=False)  # Original Hebrew text
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chapter = relationship("Chapter", back_populates="paragraphs")
    section = relationship("Section", back_populates="paragraphs")
    translations = relationship("Translation", back_populates="paragraph", cascade="all, delete-orphan")
    
    # Ensure paragraph_number is unique within a section (or chapter if sectionless)
    __table_args__ = (
        UniqueConstraint('section_id', 'paragraph_number', name='_section_paragraph_uc'),
    )
    
    def __repr__(self):
        text_preview = self.text[:50] + '...' if len(self.text) > 50 else self.text
        return f"<Paragraph(id={self.id}, chapter_id={self.chapter_id}, section_id={self.section_id}, text='{text_preview}')>"


class Translation(Base):
    """
    Represents a translation of a paragraph.
    Multiple translations can exist for the same paragraph (different prompts/versions).
    """
    __tablename__ = 'translations'
    
    id = Column(Integer, primary_key=True)
    paragraph_id = Column(Integer, ForeignKey('paragraphs.id'), nullable=False)
    prompt_name = Column(String(200), nullable=False)  # Name/identifier for the prompt used
    translated_text = Column(Text, nullable=False)  # Modern Hebrew translation
    model = Column(String(100), nullable=True)  # e.g., "gpt-4", "gpt-3.5-turbo"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    paragraph = relationship("Paragraph", back_populates="translations")
    
    # Ensure we don't duplicate translations for the same paragraph/prompt combination
    __table_args__ = (
        UniqueConstraint('paragraph_id', 'prompt_name', name='_paragraph_prompt_uc'),
    )
    
    def __repr__(self):
        text_preview = self.translated_text[:50] + '...' if len(self.translated_text) > 50 else self.translated_text
        return f"<Translation(paragraph_id={self.paragraph_id}, prompt='{self.prompt_name}', text='{text_preview}')>"


def init_db(db_url='sqlite:///duties_of_the_hearts.db'):
    """
    Initialize the database and create all tables.
    
    Args:
        db_url: Database connection string. Defaults to SQLite file.
                Can be changed to PostgreSQL later, e.g.:
                'postgresql://user:password@localhost/dbname'
    
    Returns:
        tuple: (engine, Session class)
    """
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session
