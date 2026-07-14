"""
Collections API Endpoints.

Handles CRUD operations for document collections.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import CurrentUserId, get_collection_repo, get_document_repo
from app.api.v1.schemas.collections import (
    CollectionListResponse,
    CollectionResponse,
    CreateCollectionRequest,
    UpdateCollectionRequest,
)
from app.domain.entities.collection import Collection
from app.infrastructure.repositories.sqlite_collection_repo import SQLiteCollectionRepository
from app.infrastructure.repositories.sqlite_document_repo import SQLiteDocumentRepository

router = APIRouter(prefix="/collections", tags=["Collections"])


def _collection_to_response(c: Collection) -> CollectionResponse:
    return CollectionResponse(
        id=c.id,
        name=c.name,
        description=c.description,
        color=c.color,
        icon=c.icon,
        document_count=c.document_count,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=201,
    summary="Create a collection",
)
async def create_collection(
    request: CreateCollectionRequest,
    user_id: str = Depends(CurrentUserId),
    collection_repo: SQLiteCollectionRepository = Depends(get_collection_repo),
):
    """Create a new collection for organizing papers."""
    collection = Collection(
        user_id=user_id,
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon,
    )
    await collection_repo.create(collection)
    return _collection_to_response(collection)


@router.get(
    "",
    response_model=CollectionListResponse,
    summary="List collections",
)
async def list_collections(
    user_id: str = Depends(CurrentUserId),
    collection_repo: SQLiteCollectionRepository = Depends(get_collection_repo),
):
    """List all collections for the current user."""
    collections = await collection_repo.get_all(user_id)
    return CollectionListResponse(
        collections=[_collection_to_response(c) for c in collections]
    )


@router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="Get collection",
)
async def get_collection(
    collection_id: str,
    user_id: str = Depends(CurrentUserId),
    collection_repo: SQLiteCollectionRepository = Depends(get_collection_repo),
):
    """Retrieve a single collection by ID."""
    collection = await collection_repo.get_by_id(collection_id, user_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _collection_to_response(collection)


@router.patch(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="Update collection",
)
async def update_collection(
    collection_id: str,
    request: UpdateCollectionRequest,
    user_id: str = Depends(CurrentUserId),
    collection_repo: SQLiteCollectionRepository = Depends(get_collection_repo),
):
    """Update collection name, description, color, or icon."""
    collection = await collection_repo.get_by_id(collection_id, user_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if request.name is not None:
        collection.rename(request.name)
    if request.description is not None:
        collection.update_description(request.description)
    if request.color is not None:
        collection.color = request.color
    if request.icon is not None:
        collection.icon = request.icon

    await collection_repo.update(collection)
    return _collection_to_response(collection)


@router.delete(
    "/{collection_id}",
    status_code=204,
    summary="Delete collection",
)
async def delete_collection(
    collection_id: str,
    user_id: str = Depends(CurrentUserId),
    collection_repo: SQLiteCollectionRepository = Depends(get_collection_repo),
):
    """Delete a collection. Documents in the collection are not deleted."""
    deleted = await collection_repo.delete(collection_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Collection not found")
    return None
