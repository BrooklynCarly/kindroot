from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import httpx

from app.database import get_db
from app.models import Resource, Tag, Category
from app.schemas import (
    ResourceCreate, ResourceUpdate, ResourceResponse, ResourceListResponse,
    TagCreate, TagResponse, CategoryCreate, CategoryResponse, LinkCheckResponse
)
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/resources", tags=["resources"])

# ============================================================================
# PUBLIC ENDPOINTS (Consumer Frontend)
# ============================================================================

@router.get("", response_model=ResourceListResponse)
async def list_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    tags: Optional[str] = None,
    featured_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    List resources with pagination, filtering, and search.
    Public endpoint for consumer frontend.
    """
    query = db.query(Resource)
    
    # Apply filters
    if category:
        query = query.filter(Resource.category == category)
    
    if featured_only:
        query = query.filter(Resource.is_featured == True)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Resource.title.ilike(search_term)) |
            (Resource.short_description.ilike(search_term)) |
            (Resource.long_description.ilike(search_term))
        )
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        query = query.join(Resource.tags).filter(Tag.name.in_(tag_list))
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    query = query.order_by(Resource.created_at.desc())
    offset = (page - 1) * page_size
    resources = query.offset(offset).limit(page_size).all()
    
    return ResourceListResponse(
        total=total,
        page=page,
        page_size=page_size,
        resources=resources
    )

@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single resource by ID.
    Increments view count.
    Public endpoint for consumer frontend.
    """
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with id {resource_id} not found"
        )
    
    # Increment view count
    resource.view_count += 1
    db.commit()
    db.refresh(resource)
    
    return resource

@router.get("/{resource_id}/related", response_model=List[ResourceResponse])
async def get_related_resources(
    resource_id: int,
    limit: int = Query(4, ge=1, le=12),
    db: Session = Depends(get_db)
):
    """
    Get related resources based on category and tags.
    Public endpoint for consumer frontend.
    """
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with id {resource_id} not found"
        )
    
    # Get resource tag IDs
    tag_ids = [tag.id for tag in resource.tags]
    
    # Find related resources (same category or shared tags)
    query = db.query(Resource).filter(
        Resource.id != resource_id
    )
    
    # Prioritize resources with matching tags, then same category
    if tag_ids:
        query = query.join(Resource.tags).filter(Tag.id.in_(tag_ids))
    else:
        query = query.filter(Resource.category == resource.category)
    
    related = query.order_by(Resource.view_count.desc()).limit(limit).all()
    
    # If we don't have enough, add some from the same category
    if len(related) < limit and tag_ids:
        remaining = limit - len(related)
        category_resources = db.query(Resource).filter(
            Resource.category == resource.category,
            Resource.id != resource_id,
            Resource.id.notin_([r.id for r in related])
        ).limit(remaining).all()
        related.extend(category_resources)
    
    return related

@router.get("/categories/list", response_model=List[str])
async def list_categories(db: Session = Depends(get_db)):
    """
    Get all unique resource categories.
    Public endpoint for consumer frontend.
    """
    categories = db.query(Resource.category).distinct().all()
    return [cat[0] for cat in categories]

@router.get("/tags/list", response_model=List[TagResponse])
async def list_tags(db: Session = Depends(get_db)):
    """
    Get all tags.
    Public endpoint for consumer frontend.
    """
    tags = db.query(Tag).order_by(Tag.name).all()
    return tags

# ============================================================================
# ADMIN ENDPOINTS (Protected)
# ============================================================================

@router.post("", response_model=ResourceResponse)
async def create_resource(
    resource: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new resource.
    Admin only endpoint.
    """
    # Create resource
    db_resource = Resource(
        title=resource.title,
        category=resource.category,
        short_description=resource.short_description,
        long_description=resource.long_description,
        link=resource.link,
        thumbnail=resource.thumbnail,
        is_featured=resource.is_featured
    )
    
    # Handle tags
    for tag_name in resource.tag_names:
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.add(tag)
        db_resource.tags.append(tag)
    
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    
    return db_resource

@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: int,
    resource: ResourceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing resource.
    Admin only endpoint.
    """
    db_resource = db.query(Resource).filter(Resource.id == resource_id).first()
    
    if not db_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with id {resource_id} not found"
        )
    
    # Update fields
    update_data = resource.model_dump(exclude_unset=True)
    tag_names = update_data.pop("tag_names", None)
    
    for field, value in update_data.items():
        setattr(db_resource, field, value)
    
    # Update tags if provided
    if tag_names is not None:
        db_resource.tags.clear()
        for tag_name in tag_names:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
            db_resource.tags.append(tag)
    
    db_resource.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_resource)
    
    return db_resource

@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a resource.
    Admin only endpoint.
    """
    db_resource = db.query(Resource).filter(Resource.id == resource_id).first()
    
    if not db_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with id {resource_id} not found"
        )
    
    db.delete(db_resource)
    db.commit()
    
    return {"status": "success", "message": f"Resource {resource_id} deleted"}

@router.post("/{resource_id}/duplicate", response_model=ResourceResponse)
async def duplicate_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Duplicate an existing resource.
    Admin only endpoint.
    """
    original = db.query(Resource).filter(Resource.id == resource_id).first()
    
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with id {resource_id} not found"
        )
    
    # Create duplicate
    duplicate = Resource(
        title=f"{original.title} (Copy)",
        category=original.category,
        short_description=original.short_description,
        long_description=original.long_description,
        link=original.link,
        thumbnail=original.thumbnail,
        is_featured=False
    )
    
    # Copy tags
    for tag in original.tags:
        duplicate.tags.append(tag)
    
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    
    return duplicate

@router.post("/{resource_id}/check-link", response_model=LinkCheckResponse)
async def check_resource_link(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Check if a resource link is working.
    Admin only endpoint.
    """
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with id {resource_id} not found"
        )
    
    # Check the link
    link_status = "working"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(resource.link, follow_redirects=True)
            if response.status_code >= 400:
                link_status = "broken"
    except Exception:
        link_status = "broken"
    
    # Update resource
    resource.link_status = link_status
    resource.last_checked = datetime.utcnow()
    db.commit()
    
    return LinkCheckResponse(
        resource_id=resource.id,
        link=resource.link,
        status=link_status,
        checked_at=resource.last_checked
    )

@router.post("/check-all-links")
async def check_all_links(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Check all resource links.
    Admin only endpoint.
    """
    resources = db.query(Resource).all()
    results = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for resource in resources:
            link_status = "working"
            try:
                response = await client.head(resource.link, follow_redirects=True)
                if response.status_code >= 400:
                    link_status = "broken"
            except Exception:
                link_status = "broken"
            
            resource.link_status = link_status
            resource.last_checked = datetime.utcnow()
            
            results.append({
                "resource_id": resource.id,
                "title": resource.title,
                "link": resource.link,
                "status": link_status
            })
    
    db.commit()
    
    return {
        "status": "success",
        "total_checked": len(results),
        "results": results
    }

# ============================================================================
# CATEGORY MANAGEMENT (Admin Only)
# ============================================================================

@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new category.
    Admin only endpoint.
    """
    # Check if category already exists
    existing = db.query(Category).filter(Category.name == category.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category.name}' already exists"
        )
    
    db_category = Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    return db_category

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all categories.
    Admin only endpoint.
    """
    categories = db.query(Category).order_by(Category.name).all()
    return categories
