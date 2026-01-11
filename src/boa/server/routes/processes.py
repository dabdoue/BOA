"""
BOA Process Routes
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from boa.db.repository import ProcessRepository, NotFoundError
from boa.spec.loader import load_process_spec, SpecLoadError
from boa.spec.validators import SpecValidationError
from boa.server.deps import get_db
from boa.server.schemas import (
    ProcessCreate,
    ProcessUpdate,
    ProcessResponse,
    ProcessDetailResponse,
)

router = APIRouter(prefix="/processes", tags=["processes"])


@router.post("", response_model=ProcessDetailResponse, status_code=status.HTTP_201_CREATED)
def create_process(
    data: ProcessCreate,
    db: Session = Depends(get_db),
) -> ProcessDetailResponse:
    """Create a new process."""
    repo = ProcessRepository(db)
    
    # Validate spec
    try:
        spec = load_process_spec(data.spec_yaml)
        spec_parsed = spec.model_dump()
    except (SpecLoadError, SpecValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid specification: {e}",
        )
    
    process = repo.create_from_spec(
        spec_yaml=data.spec_yaml,
        spec_parsed=spec_parsed,
        name=data.name,
        description=data.description,
    )
    
    db.commit()
    
    return ProcessDetailResponse.model_validate(process)


@router.get("", response_model=List[ProcessResponse])
def list_processes(
    name: str | None = None,
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[ProcessResponse]:
    """List processes."""
    repo = ProcessRepository(db)
    
    if name:
        processes = repo.list_versions(name, active_only=active_only)
    else:
        processes = repo.list(active_only=active_only, limit=limit, offset=offset)
    
    return [ProcessResponse.model_validate(p) for p in processes]


@router.get("/{process_id}", response_model=ProcessDetailResponse)
def get_process(
    process_id: UUID,
    db: Session = Depends(get_db),
) -> ProcessDetailResponse:
    """Get process by ID."""
    repo = ProcessRepository(db)
    
    try:
        process = repo.get_or_raise(process_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process {process_id} not found",
        )
    
    return ProcessDetailResponse.model_validate(process)


@router.put("/{process_id}", response_model=ProcessDetailResponse)
def update_process(
    process_id: UUID,
    data: ProcessUpdate,
    db: Session = Depends(get_db),
) -> ProcessDetailResponse:
    """Update a process (creates new version if spec changed)."""
    repo = ProcessRepository(db)
    
    try:
        process = repo.get_or_raise(process_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process {process_id} not found",
        )
    
    if data.spec_yaml:
        # Create new version
        try:
            spec = load_process_spec(data.spec_yaml)
            spec_parsed = spec.model_dump()
        except (SpecLoadError, SpecValidationError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid specification: {e}",
            )
        
        process = repo.create_version(
            name=process.name,
            spec_yaml=data.spec_yaml,
            spec_parsed=spec_parsed,
            description=data.description or process.description,
        )
    else:
        # Just update description
        if data.description is not None:
            process.description = data.description
        process = repo.update(process)
    
    db.commit()
    
    return ProcessDetailResponse.model_validate(process)


@router.delete("/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_process(
    process_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    """Soft delete a process (mark inactive)."""
    repo = ProcessRepository(db)
    
    try:
        process = repo.get_or_raise(process_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process {process_id} not found",
        )
    
    process.is_active = False
    repo.update(process)
    db.commit()

