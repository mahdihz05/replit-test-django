import csv
import io
import re
import zipfile
from xml.etree import ElementTree
from django.db.models import Q

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from communication.models import Contact


PHONE_PATTERN = re.compile(r'^\+?\d{10,15}$')
SYSTEM_FIELDS = {'name', 'phone', 'email', 'company', 'city', 'tags'}


def normalize_phone(value):
    value = re.sub(r'[\s()-]', '', str(value or '').strip())
    if value.startswith('0098'):
        value = '+98' + value[4:]
    elif value.startswith('09'):
        value = '+98' + value[1:]
    elif value.startswith('9') and len(value) == 10:
        value = '+98' + value
    return value


def validate_contact_data(data):
    errors = []
    phone = normalize_phone(data.get('phone'))
    email = str(data.get('email') or '').strip().lower()
    if not phone and not email:
        errors.append('شماره موبایل یا ایمیل الزامی است')
    if phone and not PHONE_PATTERN.match(phone):
        errors.append('شماره موبایل نامعتبر است')
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors.append('ایمیل نامعتبر است')
    data['phone'] = phone
    data['email'] = email
    return errors


def _xlsx_column_index(reference):
    letters = ''.join(char for char in reference if char.isalpha())
    result = 0
    for char in letters.upper():
        result = result * 26 + ord(char) - 64
    return result - 1


def _read_xlsx(file_obj):
    """Read the first XLSX worksheet using only Python's standard library."""
    file_obj.seek(0)
    with zipfile.ZipFile(file_obj) as archive:
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            root = ElementTree.fromstring(archive.read('xl/sharedStrings.xml'))
            shared = [''.join(node.itertext()) for node in root]
        sheet_names = sorted(name for name in archive.namelist() if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'))
        if not sheet_names:
            return []
        root = ElementTree.fromstring(archive.read(sheet_names[0]))
        parsed_rows = []
        for row in root.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
            values = {}
            for cell in row.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                index = _xlsx_column_index(cell.attrib.get('r', 'A1'))
                cell_type = cell.attrib.get('t')
                value_node = cell.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                if cell_type == 'inlineStr':
                    inline = cell.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is')
                    value = ''.join(inline.itertext()) if inline is not None else ''
                else:
                    value = value_node.text if value_node is not None else ''
                    if cell_type == 's' and value:
                        value = shared[int(value)]
                values[index] = value
            width = max(values.keys(), default=-1) + 1
            parsed_rows.append([values.get(index, '') for index in range(width)])
    if not parsed_rows:
        return []
    headers = [str(item or '').strip() for item in parsed_rows[0]]
    return [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in parsed_rows[1:]]


def read_import_file(file_obj, file_type):
    file_obj.seek(0)
    if file_type == 'csv':
        raw = file_obj.read()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8-sig')
        return list(csv.DictReader(io.StringIO(raw)))
    if file_type == 'xlsx':
        try:
            return _read_xlsx(file_obj)
        except (zipfile.BadZipFile, ElementTree.ParseError, KeyError, ValueError) as exc:
            raise ValidationError('فایل XLSX معتبر نیست') from exc
    if file_type == 'xls':
        raise ValidationError('فرمت قدیمی XLS پشتیبانی نمی‌شود؛ فایل را به XLSX یا CSV تبدیل کنید')
    raise ValidationError('فقط فایل CSV یا Excel مجاز است')


def map_row(row, mapping):
    data, custom = {}, {}
    for source, target in mapping.items():
        value = row.get(source, '')
        if target in SYSTEM_FIELDS:
            data[target] = value
        elif target.startswith('custom_fields.'):
            custom[target.split('.', 1)[1]] = value
    data['custom_fields'] = custom
    if isinstance(data.get('tags'), str):
        data['tags'] = [tag.strip() for tag in data['tags'].split(',') if tag.strip()]
    return data


def analyze_rows(workspace, rows, mapping):
    result = {'total': len(rows), 'valid': 0, 'invalid': 0, 'duplicates': 0, 'errors': [], 'preview': []}
    seen = set()
    for index, row in enumerate(rows, start=2):
        data = map_row(row, mapping)
        errors = validate_contact_data(data)
        identity = data.get('phone') or data.get('email')
        duplicate = bool(identity and identity in seen)
        if identity:
            seen.add(identity)
        if not duplicate and identity:
            duplicate_query = Q(phone=data['phone']) if data.get('phone') else Q(email=data['email'])
            duplicate = Contact.objects.filter(workspace=workspace).filter(duplicate_query).exists()
        if duplicate:
            result['duplicates'] += 1
        elif errors:
            result['invalid'] += 1
            result['errors'].append({'row': index, 'errors': errors})
        else:
            result['valid'] += 1
        if len(result['preview']) < 10:
            result['preview'].append({'row': index, 'data': data, 'errors': errors, 'duplicate': duplicate})
    return result
