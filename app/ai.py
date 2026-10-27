"""Explicit provider selection; never silently sends local requests to the cloud."""
import json
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from app.config import settings
from app.cv_schemas import CareerContent
from app.gemini import SYSTEM_PROMPT


def _post(url, **kwargs):
    with httpx.Client(timeout=httpx.Timeout(settings.ollama_timeout_seconds, connect=5), trust_env=False) as client:
        return client.post(url, **kwargs)


def provider_model():
    return settings.ollama_model if settings.ai_provider == 'ollama' else settings.gemini_model


def local_url():
    url = urlsplit(settings.ollama_base_url)
    if (url.scheme != 'http' or url.hostname not in ('localhost', '127.0.0.1', '::1')
            or url.username or url.password or url.query or url.fragment or url.path not in ('', '/')):
        raise HTTPException(503, 'OLLAMA_BASE_URL phải là địa chỉ HTTP localhost, không có đường dẫn.')
    return settings.ollama_base_url.rstrip('/')


def availability():
    if settings.ai_provider == 'gemini':
        return {'provider': 'gemini', 'model': provider_model(),
                'ai_available': bool(settings.gemini_api_key.get_secret_value())}
    try:
        with httpx.Client(timeout=3, trust_env=False) as client:
            response = client.get(local_url() + '/api/tags')
            response.raise_for_status()
            names = {item.get('name') for item in response.json()['models']}
        ready = settings.ollama_model in names
        return {'provider': 'ollama', 'model': provider_model(), 'ai_available': ready,
                'message': 'Ollama local sẵn sàng.' if ready else 'Chưa có model. Chạy ollama pull ' + settings.ollama_model}
    except (httpx.HTTPError, ValueError, KeyError, TypeError, HTTPException):
        return {'provider': 'ollama', 'model': provider_model(), 'ai_available': False,
                'message': 'Không kết nối được Ollama local. Hãy mở Ollama và kiểm tra cấu hình.'}


def generate_career(profile, instructions, previous=None):
    if settings.ai_provider == 'gemini':
        from app.gemini import generate_career as generate
        return generate(profile, instructions, previous)
    career = {key: profile.get(key, '') for key in
              ('education', 'skills', 'experience', 'projects', 'desired_position', 'wishes')}
    payload = {'career_profile': career, 'editing_request': instructions}
    if previous:
        payload['previous_cv'] = {key: previous.get(key, '') for key in CareerContent.model_fields}
    prompt = json.dumps(payload, ensure_ascii=False)
    # Conservative byte budget for Vietnamese + system/template overhead; never silently
    # trim career facts to fit the user's 8192-token context window.
    if len((SYSTEM_PROMPT + prompt).encode('utf-8')) > 12000:
        raise HTTPException(422, 'Nội dung quá dài cho ngữ cảnh Ollama 8192 token. Hãy rút gọn hồ sơ hoặc yêu cầu chỉnh sửa; chưa lưu phiên bản mới.')
    schema = CareerContent.model_json_schema()
    schema['required'] = list(CareerContent.model_fields)
    try:
        response = _post(local_url() + '/api/chat', json={
            'model': settings.ollama_model, 'stream': False, 'format': schema,
            'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                         {'role': 'user', 'content': prompt}],
            'options': {'temperature': 0, 'num_ctx': 8192, 'num_predict': 3072}})
    except httpx.TimeoutException:
        raise HTTPException(504, 'Ollama phản hồi quá lâu. Chưa lưu phiên bản mới; hãy thử lại với nội dung ngắn hơn.')
    except httpx.RequestError:
        raise HTTPException(503, 'Không kết nối được Ollama local. Hãy mở Ollama rồi thử lại.')
    if response.status_code == 404:
        raise HTTPException(503, 'Chưa tìm thấy model Ollama. Chạy ollama pull ' + settings.ollama_model)
    if response.is_error:
        raise HTTPException(503, 'Ollama chưa xử lý được yêu cầu. Kiểm tra model và bộ nhớ máy.')
    try:
        data = response.json()
        if data.get('done') is not True or data.get('done_reason') != 'stop':
            raise ValueError('Incomplete output')
        raw = json.loads(data['message']['content'])
        if not isinstance(raw, dict) or set(raw) != set(CareerContent.model_fields):
            raise ValueError('Unexpected fields')
        result = CareerContent.model_validate(raw)
        if not any(result.model_dump().values()):
            raise ValueError('Empty output')
        return result
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, 'Nội dung Ollama chưa hợp lệ hoặc bị cắt ngắn. Chưa lưu phiên bản mới.')
