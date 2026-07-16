from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_db
from app.api.schemas import (
    DatasetFieldMappingInput,
    DatasetFieldMappingResponse,
    DatasetMappingsUpdate,
    DatasetSchemaResponse,
    MappingPreviewRequest,
    MappingPreviewResponse,
    NormalizedPreviewRecordResponse,
    SourceFieldSchemaResponse,
)
from app.db.models import UploadedDataset
from app.uploads.mapping import (
    MappingDefinition,
    MappingLockedError,
    MappingValidationError,
    OPTIONAL_TARGET_FIELDS,
    REQUIRED_TARGET_FIELDS,
    TARGET_FIELDS,
    get_dataset_mappings,
    inspect_dataset_schema,
    mapping_definitions_from_models,
    preview_dataset_records,
    replace_dataset_mappings,
    validate_mapping_definitions,
)
from app.uploads.parser import UploadParseError

router = APIRouter(
    prefix="/uploads/{dataset_id}",
    tags=["dataset field mappings"],
)


@router.get("/schema", response_model=DatasetSchemaResponse)
def get_dataset_schema(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> DatasetSchemaResponse:
    dataset = get_dataset_or_404(db, dataset_id)
    try:
        fields = inspect_dataset_schema(dataset)
    except UploadParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DatasetSchemaResponse(
        dataset_id=dataset.id,
        fields=[SourceFieldSchemaResponse(**field.__dict__) for field in fields],
        target_fields=list(TARGET_FIELDS),
        required_target_fields=list(REQUIRED_TARGET_FIELDS),
        optional_target_fields=list(OPTIONAL_TARGET_FIELDS),
    )


@router.get("/mappings", response_model=list[DatasetFieldMappingResponse])
def list_dataset_mappings(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> list[DatasetFieldMappingResponse]:
    get_dataset_or_404(db, dataset_id)
    return [
        DatasetFieldMappingResponse.model_validate(mapping)
        for mapping in get_dataset_mappings(db, dataset_id)
    ]


@router.put("/mappings", response_model=list[DatasetFieldMappingResponse])
def save_dataset_mappings(
    dataset_id: int,
    update: DatasetMappingsUpdate,
    db: Session = Depends(get_db),
) -> list[DatasetFieldMappingResponse]:
    try:
        with db.begin():
            dataset = get_dataset_or_404(db, dataset_id)
            schema = inspect_dataset_schema(dataset)
            definitions = validate_mapping_definitions(
                definitions_from_inputs(update.mappings),
                {field.source_field for field in schema},
            )
            mappings = replace_dataset_mappings(db, dataset, definitions, schema)
    except MappingLockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MappingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UploadParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [DatasetFieldMappingResponse.model_validate(mapping) for mapping in mappings]


@router.post("/mapping-preview", response_model=MappingPreviewResponse)
def preview_dataset_mapping(
    dataset_id: int,
    request: MappingPreviewRequest,
    db: Session = Depends(get_db),
) -> MappingPreviewResponse:
    dataset = get_dataset_or_404(db, dataset_id)
    try:
        schema = inspect_dataset_schema(dataset)
        if request.mappings is None:
            definitions = mapping_definitions_from_models(
                get_dataset_mappings(db, dataset_id)
            )
        else:
            definitions = definitions_from_inputs(request.mappings)

        definitions = validate_mapping_definitions(
            definitions,
            {field.source_field for field in schema},
        )
        previews, warnings = preview_dataset_records(dataset, definitions, request.limit)
    except MappingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UploadParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MappingPreviewResponse(
        dataset_id=dataset.id,
        records=[
            NormalizedPreviewRecordResponse(
                record_number=preview.record_number,
                timestamp=preview.normalized.timestamp,
                source_system=preview.normalized.source_system,
                event_type=preview.normalized.event_type,
                username=preview.normalized.username,
                source_ip=preview.normalized.source_ip,
                destination_ip=preview.normalized.destination_ip,
                asset=preview.normalized.asset,
                action=preview.normalized.action,
                outcome=preview.normalized.outcome,
                severity=preview.normalized.severity,
                mitre_technique_id=preview.normalized.mitre_technique_id,
                message=preview.normalized.message,
            )
            for preview in previews
        ],
        warnings=warnings,
    )


def definitions_from_inputs(
    inputs: list[DatasetFieldMappingInput],
) -> list[MappingDefinition]:
    return [
        MappingDefinition(
            source_field=item.source_field,
            target_field=item.target_field,
            transformation_type=item.transformation_type,
            default_value=item.default_value,
        )
        for item in inputs
        if item.target_field is not None and item.target_field.strip()
    ]


def get_dataset_or_404(db: Session, dataset_id: int) -> UploadedDataset:
    dataset = db.get(
        UploadedDataset,
        dataset_id,
        options=[selectinload(UploadedDataset.files)],
    )
    if dataset is None:
        raise HTTPException(status_code=404, detail="Uploaded dataset not found")
    return dataset
