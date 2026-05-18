import os
import re

from django.core.exceptions import ValidationError


SAFE_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё0-9\s\-'.]+$")
SAFE_PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,20}$")

ALLOWED_DOCUMENT_EXTENSIONS = {
    'doc',
    'docx',
    'pdf',
    'xls',
    'xlsx',
    'odt',
    'ods',
    'txt',
    'rtf',
    'csv',
}

ALLOWED_DOCUMENT_MIME_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.oasis.opendocument.text',
    'application/vnd.oasis.opendocument.spreadsheet',
    'text/plain',
    'text/csv',
    'application/rtf',
}


def normalize_text(value):
    return ' '.join((value or '').strip().split())


def validate_required_text(value, field_name='Поле'):
    if not normalize_text(value):
        raise ValidationError(f'{field_name} не может быть пустым.')


def validate_safe_name(value):
    value = normalize_text(value)
    validate_required_text(value, 'Значение')
    if not SAFE_NAME_RE.fullmatch(value):
        raise ValidationError('Используйте буквы, цифры, пробелы, дефис, точку или апостроф.')


def validate_phone(value):
    value = normalize_text(value)
    if value and not SAFE_PHONE_RE.fullmatch(value):
        raise ValidationError('Введите телефон в корректном формате.')


def validate_document_extension(file_obj):
    extension = os.path.splitext(file_obj.name)[1].lower().lstrip('.')
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        allowed = ', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))
        raise ValidationError(f'Недопустимый формат файла. Разрешены: {allowed}.')


def validate_document_mime(file_obj):
    content_type = getattr(file_obj, 'content_type', '')
    if content_type and content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        raise ValidationError('Тип файла не соответствует списку разрешенных документов.')
