from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime

# Tag Schemas
class TagBase(BaseModel):
    name: str = Field(..., max_length=50)

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Category Schemas
class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Resource Schemas
class ResourceBase(BaseModel):
    title: str = Field(..., max_length=255)
    category: str = Field(..., max_length=100)
    short_description: str = Field(..., max_length=500)
    long_description: str
    link: str = Field(..., max_length=500)
    thumbnail: Optional[str] = Field(None, max_length=500)
    is_featured: bool = False

class ResourceCreate(ResourceBase):
    tag_names: List[str] = []

class ResourceUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    short_description: Optional[str] = Field(None, max_length=500)
    long_description: Optional[str] = None
    link: Optional[str] = Field(None, max_length=500)
    thumbnail: Optional[str] = Field(None, max_length=500)
    is_featured: Optional[bool] = None
    tag_names: Optional[List[str]] = None

class ResourceResponse(ResourceBase):
    id: int
    view_count: int
    link_status: str
    last_checked: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = []
    
    class Config:
        from_attributes = True

class ResourceListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    resources: List[ResourceResponse]

class LinkCheckResponse(BaseModel):
    resource_id: int
    link: str
    status: str
    checked_at: datetime
