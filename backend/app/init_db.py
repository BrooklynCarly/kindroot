"""
Database initialization script for resources system.
Run this once to create the database tables.
"""
from app.database import engine
from app.models import Base, Resource, Tag, Category
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Create all database tables."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")
    
    # Add some default categories
    from app.database import SessionLocal
    db = SessionLocal()
    
    default_categories = [
        {"name": "Early Intervention", "description": "Resources for early childhood intervention services"},
        {"name": "Therapy Services", "description": "Speech, occupational, and behavioral therapy resources"},
        {"name": "Educational Resources", "description": "School support and educational materials"},
        {"name": "Support Groups", "description": "Parent support groups and communities"},
        {"name": "Financial Assistance", "description": "Funding and financial support resources"},
        {"name": "Medical Resources", "description": "Healthcare providers and medical information"},
        {"name": "Legal Resources", "description": "Legal rights and advocacy resources"},
        {"name": "Community Activities", "description": "Social activities and recreation programs"},
        {"name": "Products", "description": "Helpful products and tools for families"},
        {"name": "Tests", "description": "Diagnostic tests and assessment resources"},
        {"name": "Apps", "description": "Mobile and web applications for families"},
    ]
    
    for cat_data in default_categories:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            category = Category(**cat_data)
            db.add(category)
            logger.info(f"Added category: {cat_data['name']}")
    
    db.commit()
    db.close()
    logger.info("Default categories added!")

if __name__ == "__main__":
    init_db()
