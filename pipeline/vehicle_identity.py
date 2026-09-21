"""Stable commission identifiers; never infer identity from model or color."""
import math
import re


def commission_id(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, bool):
        raise ValueError('Invalid commission number')
    text = str(value).strip()
    if not text or text.lower() in ('nan', 'none', 'null'):
        return None
    # Excel numeric cells may be read as 123456789.0. Preserve text leading zeros.
    if re.fullmatch(r'\d+\.0+', text):
        text = text.split('.')[0]
    return text


def normalize_interior_color(value):
    """Translate the English ARTICO labels used by the stock export."""
    if value is None:
        return ''
    text = str(value).strip()
    lower = text.lower()
    if lower == 'artico man-made leather beige':
        return '베이지 인조가죽'
    if lower == 'black artico man-made leather':
        return '블랙 인조가죽'
    return text
