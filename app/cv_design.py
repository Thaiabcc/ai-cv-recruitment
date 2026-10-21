import hashlib
from io import BytesIO

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import CVPhoto

TEMPLATES = [
    {'id': 'monochrome', 'name': 'Monochrome', 'description': 'Mẫu 01 · Đen–xám, nhãn mũi tên', 'requires_photo': False},
    {'id': 'lavender', 'name': 'Lavender', 'description': 'Mẫu 02 · Khối màu tím, ảnh bo góc', 'requires_photo': True},
    {'id': 'editorial', 'name': 'Editorial', 'description': 'Mẫu 03 · Banner xám, ảnh vuông', 'requires_photo': False},
    {'id': 'gradient', 'name': 'Gradient', 'description': 'Mẫu 04 · Cột xanh–tím, ảnh tròn', 'requires_photo': True},
]
MAX_PHOTO_BYTES = 3 * 1024 * 1024


def own_photo(photo_id, user_id, db):
    photo = db.scalar(select(CVPhoto).where(CVPhoto.id == photo_id, CVPhoto.user_id == user_id))
    if not photo:
        raise HTTPException(404, 'Không tìm thấy ảnh của tài khoản này.')
    return photo


def resolve_design(options, user_id, db, fallback=None):
    design = options.model_dump() if options is not None else dict(fallback or {'template_id': 'monochrome', 'photo_id': None})
    if design['template_id'] in ('portrait', 'lavender', 'gradient'):
        if not design.get('photo_id'):
            raise HTTPException(422, 'Mẫu này cần ảnh chân dung. Hãy tải ảnh lên trước.')
        own_photo(design['photo_id'], user_id, db)
    elif design['template_id'] in ('monochrome', 'editorial') and design.get('photo_id'):
        own_photo(design['photo_id'], user_id, db)
    else:
        design['photo_id'] = None
    return design


def store_photo(raw, user_id, db):
    if not raw or len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(413, 'Ảnh phải có dung lượng từ 1 byte đến 3 MB.')
    try:
        with Image.open(BytesIO(raw)) as source:
            if source.format not in ('JPEG', 'PNG', 'WEBP') or getattr(source, 'n_frames', 1) != 1:
                raise ValueError('Unsupported photo')
            if source.width * source.height > 16_000_000 or min(source.size) < 64:
                raise ValueError('Photo dimensions out of range')
            source.load()
            image = ImageOps.exif_transpose(source).convert('RGBA')
            image = ImageOps.fit(image, (720, 720), method=Image.Resampling.LANCZOS)
            background = Image.new('RGB', image.size, 'white')
            background.paste(image, mask=image.getchannel('A'))
            output = BytesIO()
            background.save(output, format='JPEG', quality=90)
            normalized = output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, 'Ảnh không hợp lệ. Chọn JPG, PNG hoặc WebP tĩnh, tối thiểu 64 px và tối đa 16 triệu pixel.')
    digest = hashlib.sha256(normalized).hexdigest()
    existing = db.scalar(select(CVPhoto).where(CVPhoto.user_id == user_id, CVPhoto.sha256 == digest))
    if existing:
        return existing
    photo = CVPhoto(user_id=user_id, data=normalized, sha256=digest)
    db.add(photo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(select(CVPhoto).where(CVPhoto.user_id == user_id, CVPhoto.sha256 == digest))
    db.refresh(photo)
    return photo
