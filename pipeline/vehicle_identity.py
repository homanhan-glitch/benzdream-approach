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
