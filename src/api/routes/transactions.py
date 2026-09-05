"""
Transaction upload, validation, and dataset endpoints for SUS.

Provides:
- POST /transactions/upload — upload a transaction CSV dataset
- POST /transactions/validate — validate a transaction CSV without storing
- GET  /transactions/datasets — list stored datasets
- GET  /transactions/datasets/{dataset_id} — get dataset metadata
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.api.schemas.transactions import (
    DatasetListResponse,
    DatasetMetadataResponse,
    TransactionUploadResponse,
    TransactionValidationResponse,
)
from src.database.session import get_db
from src.services.dataset_manager import DatasetManager
from src.services.transaction_data_provider import CSVTransactionDataProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])

# Maximum upload size: 100 MB
MAX_UPLOAD_SIZE = 100 * 1024 * 1024

# Module-level manager (no in-memory state — all state is in DB)
dataset_manager = DatasetManager()


def _ds_to_response(ds) -> DatasetMetadataResponse:
    """Convert a Dataset ORM object to API response (no filesystem paths)."""
    return DatasetMetadataResponse(
        dataset_id=ds.dataset_id,
        original_filename=ds.original_filename,
        data_source_type=ds.data_source_type,
        row_count=ds.row_count,
        merchant_count=ds.merchant_count,
        min_transaction_date=ds.min_transaction_date,
        max_transaction_date=ds.max_transaction_date,
        validation_status=ds.validation_status,
        created_at=ds.created_at.isoformat() if ds.created_at else "",
    )


@router.post("/upload", response_model=TransactionUploadResponse)
async def upload_transaction_csv(
    file: UploadFile = File(..., description="Transaction CSV file"),
    window_labels_file: Optional[UploadFile] = File(
        None, description="Optional window labels CSV file"
    ),
    db: Session = Depends(get_db),
) -> TransactionUploadResponse:
    """Upload a transaction CSV dataset for use in investigations.

    The uploaded file is stored in the configured upload directory with a
    unique dataset ID. Metadata is persisted to the database.
    Returns the dataset ID which can be used when running an investigation.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=422, detail="No filename provided")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail="File must be a CSV (.csv extension required)",
        )

    # Read file content with size limit
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        )

    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    # Read optional window labels
    wl_content = None
    wl_filename = None
    if window_labels_file is not None:
        wl_content = await window_labels_file.read()
        wl_filename = window_labels_file.filename
        if len(wl_content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Window labels file too large",
            )

    # Validate before storing
    try:
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="wb"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        provider = CSVTransactionDataProvider(
            transactions_path=tmp_path,
            source_name=f"upload:{file.filename}",
        )
        validation = provider.validate()

        # Clean up temp file
        os.unlink(tmp_path)

        if not validation.is_valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Transaction CSV failed validation",
                    "validation": validation.to_dict(),
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Validation failed during upload")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while validating the uploaded file.",
        )

    # Store the dataset (DB-backed metadata)
    try:
        ds = dataset_manager.store_dataset(
            db=db,
            transactions_content=content,
            original_filename=file.filename,
            window_labels_content=wl_content,
            window_labels_filename=wl_filename,
            row_count=validation.total_rows,
            merchant_count=validation.metadata.get("unique_merchants"),
            min_transaction_date=validation.metadata.get("date_range_start"),
            max_transaction_date=validation.metadata.get("date_range_end"),
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to store dataset")
        raise HTTPException(
            status_code=500,
            detail="Failed to store dataset",
        )

    logger.info("Dataset uploaded: %s (%s)", ds.dataset_id, file.filename)

    return TransactionUploadResponse(
        dataset_id=ds.dataset_id,
        original_filename=ds.original_filename,
        source_name=f"upload:{file.filename}",
        row_count=ds.row_count,
        merchant_count=ds.merchant_count,
    )


@router.post("/validate", response_model=TransactionValidationResponse)
async def validate_transaction_csv(
    file: UploadFile = File(..., description="Transaction CSV file to validate"),
) -> TransactionValidationResponse:
    """Validate a transaction CSV without storing it.

    Returns validation results including row counts, errors, warnings,
    and metadata (unique merchants, date range, amount stats).
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="File must be a CSV")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        )

    # Write to temp file for validation
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        provider = CSVTransactionDataProvider(
            transactions_path=tmp_path,
            source_name=f"validate:{file.filename}",
        )
        result = provider.validate()
    finally:
        os.unlink(tmp_path)

    return TransactionValidationResponse(
        is_valid=result.is_valid,
        total_rows=result.total_rows,
        valid_rows=result.valid_rows,
        error_count=len(result.errors),
        warning_count=len(result.warnings),
        errors=result.errors,
        warnings=result.warnings,
        unique_merchants=result.metadata.get("unique_merchants"),
        date_range_start=result.metadata.get("date_range_start"),
        date_range_end=result.metadata.get("date_range_end"),
        amount_min=result.metadata.get("amount_min"),
        amount_max=result.metadata.get("amount_max"),
    )


# -----------------------------------------------------------------------
# Dataset read-only endpoints
# -----------------------------------------------------------------------


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets(
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> DatasetListResponse:
    """List stored datasets with metadata.

    Returns dataset metadata only — no raw transaction contents or
    server filesystem paths are exposed.
    """
    repo_datasets = dataset_manager.list_datasets(db, limit=limit, offset=offset)
    total = len(repo_datasets)  # TODO: use count if pagination needed

    # Recount properly
    from src.repositories.dataset_repository import DatasetRepository
    ds_repo = DatasetRepository(db)
    total = ds_repo.count_datasets()

    items = [_ds_to_response(ds) for ds in repo_datasets]

    return DatasetListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetMetadataResponse)
async def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
) -> DatasetMetadataResponse:
    """Get metadata for a specific dataset.

    Returns dataset metadata only — no raw transaction contents or
    server filesystem paths are exposed.
    """
    ds = dataset_manager.get_dataset(db, dataset_id)
    if ds is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_id}' not found",
        )
    return _ds_to_response(ds)
