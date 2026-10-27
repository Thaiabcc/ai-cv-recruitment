from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from typing import Literal
import base64
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts import current_user, mutation_guard, profile_output
from app.config import settings
from app.cv_schemas import AIRequest, CVDocument, DraftRequest, SaveVersion
from app.cv_design import MAX_PHOTO_BYTES, TEMPLATES, own_photo, resolve_design, store_photo
from app.database import get_db
from app.ai import generate_career, availability, provider_model
from app.models import CV, Profile, User

router = APIRouter(prefix='/api/cvs', tags=['CVs'])


def own_cv(cv_id: int, user_id: int, db: Session):
    cv = db.scalar(select(CV).where(CV.id == cv_id, CV.user_id == user_id))
    if not cv:
        raise HTTPException(404, 'Không tìm thấy phiên bản CV.')
    return cv


def saved_profile(user, db):
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        raise HTTPException(409, 'Hãy lưu hồ sơ ứng viên trước khi tạo CV.')
    snapshot = profile_output(profile)
    snapshot['email'] = user.email
    return snapshot


def document_from_profile(snapshot):
    return CVDocument(**{key: snapshot.get(key, '') for key in CVDocument.model_fields
                         if key not in ('title', 'summary')}, title=snapshot.get('desired_position', ''))


def summary(cv):
    return {'id': cv.id, 'title': cv.content['document'].get('title', ''),
            'created_at': cv.created_at.isoformat() + 'Z', 'origin': cv.content['origin'],
            'parent_id': cv.content.get('parent_id'),
            'design': cv.content.get('design', {'template_id': 'forest', 'photo_id': None})}


def detail(cv):
    return {**summary(cv), 'document': cv.content['document'], 'model': cv.content.get('model')}


def persist(db, user_id, snapshot, document, origin, parent_id=None, design=None):
    cv = CV(user_id=user_id, profile_snapshot=snapshot,
            content={'schema_version': 1, 'document': document.model_dump(), 'origin': origin,
                     'parent_id': parent_id, 'model': provider_model() if origin in ('gemini', 'ollama') else None,
                     'design': design or {'template_id': 'forest', 'photo_id': None}})
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return detail(cv)


@router.get('/status')
def status(user: User = Depends(current_user)):
    return availability()


@router.get('/templates')
def templates(user: User = Depends(current_user)):
    return TEMPLATES


@router.post('/photos', status_code=201, dependencies=[Depends(mutation_guard)])
async def upload_photo(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_PHOTO_BYTES:
            raise HTTPException(413, 'Ảnh vượt quá 3 MB. Hãy chọn ảnh nhỏ hơn.')
        raw.extend(chunk)
    photo = store_photo(bytes(raw), user.id, db)
    return {'id': photo.id, 'url': f'/api/cvs/photos/{photo.id}'}


@router.get('/photos/{photo_id}')
def get_photo(photo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    photo = own_photo(photo_id, user.id, db)
    return Response(photo.data, media_type='image/jpeg', headers={'Content-Disposition': 'inline; filename="portrait.jpg"'})


@router.get('')
def list_cvs(before_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(CV).where(CV.user_id == user.id)
    if before_id is not None:
        query = query.where(CV.id < before_id)
    versions = db.scalars(query.order_by(CV.id.desc()).limit(31)).all()
    return {'items': [summary(cv) for cv in versions[:30]],
            'next_before_id': versions[29].id if len(versions) > 30 else None}


@router.post('/draft', status_code=201, dependencies=[Depends(mutation_guard)])
def draft(data: DraftRequest = Body(default=DraftRequest()), user: User = Depends(current_user), db: Session = Depends(get_db)):
    snapshot = saved_profile(user, db)
    design = resolve_design(data.design, user.id, db)
    return persist(db, user.id, snapshot, document_from_profile(snapshot), 'profile', design=design)


def require_consent(data):
    if not data.consent:
        raise HTTPException(422, 'Cần đồng ý xử lý nội dung nghề nghiệp bằng AI đã cấu hình.')


@router.post('/generate', status_code=201, dependencies=[Depends(mutation_guard)])
def generate(data: AIRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_consent(data)
    snapshot = saved_profile(user, db)
    design = resolve_design(data.design, user.id, db)
    content = generate_career(snapshot, data.instructions)
    document = document_from_profile(snapshot).model_copy(update=content.model_dump())
    return persist(db, user.id, snapshot, document, settings.ai_provider, design=design)


@router.post('/preview', dependencies=[Depends(mutation_guard)])
def preview(data: SaveVersion, representation: Literal['pdf', 'images'] = 'pdf',
            start_page: int = Query(default=0, ge=0),
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.cv_export import export_pdf
    design = resolve_design(data.design, user.id, db)
    photo = own_photo(design['photo_id'], user.id, db).data if design['photo_id'] else None
    content = export_pdf(data.document, design['template_id'], photo)
    if representation == 'images':
        import pymupdf
        with pymupdf.open(stream=content, filetype='pdf') as pdf:
            stop = min(start_page + 8, len(pdf))
            pages = [{'number': i + 1, 'image': base64.b64encode(pdf[i].get_pixmap(
                matrix=pymupdf.Matrix(1.25, 1.25), alpha=False).tobytes('png')).decode('ascii')}
                     for i in range(start_page, stop)]
            return {'pages': pages, 'total_pages': len(pdf), 'next_page': stop if stop < len(pdf) else None}
    return Response(content, media_type='application/pdf', headers={
        'Content-Disposition': 'inline; filename="cv-preview.pdf"'})


@router.get('/{cv_id}')
def get_cv(cv_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return detail(own_cv(cv_id, user.id, db))


@router.post('/{cv_id}/versions', status_code=201, dependencies=[Depends(mutation_guard)])
def save_version(cv_id: int, data: SaveVersion, user: User = Depends(current_user), db: Session = Depends(get_db)):
    parent = own_cv(cv_id, user.id, db)
    design = resolve_design(data.design, user.id, db, parent.content.get('design'))
    return persist(db, user.id, parent.profile_snapshot, data.document, 'manual', parent.id, design)


@router.post('/{cv_id}/revise', status_code=201, dependencies=[Depends(mutation_guard)])
def revise(cv_id: int, data: AIRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    parent = own_cv(cv_id, user.id, db)
    require_consent(data)
    if not data.instructions:
        raise HTTPException(422, 'Hãy nhập yêu cầu chỉnh sửa CV.')
    design = resolve_design(data.design, user.id, db, parent.content.get('design'))
    content = generate_career(parent.profile_snapshot, data.instructions, parent.content['document'])
    document = CVDocument.model_validate(parent.content['document']).model_copy(update=content.model_dump())
    return persist(db, user.id, parent.profile_snapshot, document, settings.ai_provider, parent.id, design)


@router.get('/{cv_id}/export/{file_format}')
def export(cv_id: int, file_format: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cv = own_cv(cv_id, user.id, db)
    if file_format not in ('pdf', 'docx'):
        raise HTTPException(404, 'Chỉ hỗ trợ PDF và DOCX.')
    from app.cv_export import export_docx, export_pdf
    document = CVDocument.model_validate(cv.content['document'])
    design = resolve_design(None, user.id, db, cv.content.get('design'))
    photo = own_photo(design['photo_id'], user.id, db).data if design['photo_id'] else None
    try:
        content = export_pdf(document, design['template_id'], photo) if file_format == 'pdf' else export_docx(document, design['template_id'], photo)
    except (OSError, ValueError):
        raise HTTPException(503, 'Chưa thể xuất tài liệu. Kiểm tra cấu hình font Unicode của ứng dụng.')
    mime = 'application/pdf' if file_format == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    return Response(content, media_type=mime, headers={
        'Content-Disposition': f'attachment; filename="cv-{cv.id}.{file_format}"'})
