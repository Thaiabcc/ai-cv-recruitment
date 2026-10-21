from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal


class CareerContent(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(default='', max_length=200)
    summary: str = Field(default='', max_length=3000)
    education: str = Field(default='', max_length=10000)
    skills: str = Field(default='', max_length=10000)
    experience: str = Field(default='', max_length=10000)
    projects: str = Field(default='', max_length=10000)

    @field_validator('*')
    @classmethod
    def printable_text(cls, value):
        if any(ord(char) < 32 and char not in '\n\r\t' for char in value):
            raise ValueError('Nội dung chứa ký tự điều khiển không hợp lệ.')
        return value


class CVDocument(CareerContent):
    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(default='', max_length=254)
    phone: str = Field(default='', max_length=50)
    address: str = Field(default='', max_length=500)
    languages: str = Field(default='', max_length=3000)
    certifications: str = Field(default='', max_length=5000)
    interests: str = Field(default='', max_length=2000)


class DesignOptions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    template_id: Literal['monochrome', 'lavender', 'editorial', 'gradient', 'forest', 'portrait', 'minimal'] = 'monochrome'
    photo_id: int | None = Field(default=None, gt=0)


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    design: DesignOptions | None = None


class AIRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    instructions: str = Field(default='', max_length=2000)
    consent: bool = False
    design: DesignOptions | None = None


class SaveVersion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document: CVDocument
    design: DesignOptions | None = None
