#!/usr/bin/env python3
"""
BenzDream Landing Page Auto-Updater v2.0
새 어프로치북 HTML 파일명을 인자로 받아 BenzDream_Landing.html 카드를 자동 추가/교체한다.

Usage:
  python3 update_landing.py MY26_CClass_C200_AV_AMG_20260219.html

파일명 규칙: MY[연식]_[차종]_[모델번호]_[트림...키워드]_[YYYYMMDD].html
"""

import sys, re, os
from datetime import datetime

BASE_URL = "https://mb-hansdream.co.kr/"

REPLACE_MAP = {
    "AV": "AVANTGARDE", "AVG": "AVANTGARDE",
    "AMG": "AMG Line", "AMG43": "AMG 43", "AMG53": "AMG 53", "AMG63": "AMG 63",
    "EX": "EXCLUSIVE", "EXC": "EXCLUSIVE",
    "SWB": "SWB", "LWB": "LWB", "4M": "4MATIC",
}

MODEL_DISPLAY = {
    "EClass": "E-Class", "CClass": "C-Class", "SClass": "S-Class",
    "GLC": "GLC", "GLCCoupe": "GLC Coupé", "GLE": "GLE", "GLECoupe": "GLE Coupé",
    "GLS": "GLS", "GClass": "G-Class", "CLECoupe": "CLE Coupé",
    "CLECabriolet": "CLE Cabriolet", "CLA": "CLA", "AClass": "A-Class",
    "Maybach": "Maybach", "EQS": "EQS", "EQA": "EQA", "EQB": "EQB", "EQE": "EQE",
}

CHIP_MAP = {
    "EClass": "E-Class · MY26", "CClass": "C-Class · MY26", "SClass": "S-Class · MY26",
    "GLC": "GLC · MY26", "GLCCoupe": "GLC Coupé · MY26",
    "GLE": "GLE · MY26", "GLECoupe": "GLE Coupe · MY26",
    "GLS": "GLS · MY26", "GClass": "G-Class · MY26",
    "CLECoupe": "CLE Coupé · MY26", "CLECabriolet": "CLE Cabriolet · MY26",
    "CLA": "CLA · MY26", "AClass": "A-Class · MY26",
    "Maybach": "Maybach · MY26",
    "EQS": "EQS · MY26", "EQA": "EQA · MY26", "EQB": "EQB · MY26", "EQE": "EQE · MY26",
}

SECTION_MAP = {
    "EClass":       "<!-- SEDAN CLASS -->",
    "CClass":       "<!-- SEDAN CLASS -->",
    "SClass":       "<!-- SEDAN CLASS -->",
    "CLA":          "<!-- SEDAN CLASS -->",
    "AClass":       "<!-- SEDAN CLASS -->",
    "Maybach":      "<!-- SEDAN CLASS -->",
    "GLC":          "<!-- SUV CLASS -->",
    "GLCCoupe":     "<!-- SUV CLASS -->",
    "GLE":          "<!-- SUV CLASS -->",
    "GLECoupe":     "<!-- SUV CLASS -->",
    "GLS":          "<!-- SUV CLASS -->",
    "GClass":       "<!-- SUV CLASS -->",
    "CLECoupe":     "<!-- COUPE / CABRIOLET CLASS -->",
    "CLECabriolet": "<!-- COUPE / CABRIOLET CLASS -->",
    "EQS":          "<!-- EV CLASS -->",
    "EQA":          "<!-- EV CLASS -->",
    "EQB":          "<!-- EV CLASS -->",
    "EQE":          "<!-- EV CLASS -->",
}


def fmt_model(s):
    """C200 → C 200, GLC220d → GLC 220d"""
    return re.sub(r'([A-Za-z]+)(\d)', r'\1 \2', s)


def parse_filename(filename):
    stem = filename.replace(".html", "")
    parts = stem.split("_")
    year = parts[0]
    model_key = parts[1]
    date_str = parts[-1]
    trim_parts = parts[2:-1]

    model_num = fmt_model(trim_parts[0]) if trim_parts else ""
    trim_keywords = trim_parts[1:]
    trim_display = [REPLACE_MAP.get(t, fmt_model(t)) for t in trim_keywords]

    if len(trim_display) >= 2:
        trim_str = f"{trim_display[0]} vs {' vs '.join(trim_display[1:])}"
    elif len(trim_display) == 1:
        trim_str = trim_display[0]
    else:
        trim_str = model_num

    return {
        "filename": filename,
        "model_key": model_key,
        "model_num": model_num,
        "class_name": MODEL_DISPLAY.get(model_key, model_key),
        "chip": CHIP_MAP.get(model_key, model_key + " · MY26"),
        "trim_str": trim_str,
        "section": SECTION_MAP.get(model_key, "<!-- SEDAN CLASS -->"),
        "url": BASE_URL + filename,
    }


def make_card(info):
    return (
        f'      <a href="{info["url"]}" target="_blank" class="ab-card">\n'
        f'        <div class="ab-chip">{info["chip"]}</div>\n'
        f'        <p class="ab-model">{info["model_num"]}</p>\n'
        f'        <p class="ab-trim">{info["trim_str"]}</p>\n'
        f'        <div class="ab-arrow">열람하기 →</div>\n'
        f'      </a>'
    )


def update_landing(landing_path, new_filename):
    with open(landing_path, "r", encoding="utf-8") as f:
        content = f.read()

    info = parse_filename(new_filename)
    new_card = make_card(info)

    # 1. 같은 파일명 카드가 이미 있으면 교체
    if new_filename in content:
        pattern = r'<a href="[^"]*' + re.escape(new_filename) + r'"[^>]*>.*?</a>'
        m = re.search(pattern, content, re.DOTALL)
        if m:
            content = content[:m.start()] + new_card + content[m.end():]
            print(f"✅ [UPDATE] 기존 카드 교체: {new_filename}")
            with open(landing_path, "w", encoding="utf-8") as f:
                f.write(content)
            return

    # 2. 같은 chip의 "준비중" coming 카드 교체
    chip_base = info["chip"].replace(" · MY26", "")
    coming_pattern = r'<div class="ab-card coming">.*?</div>\s*</div>'
    for m in re.finditer(r'<div class="ab-card coming">.*?(?=<a href|<div class="ab-card)', content, re.DOTALL):
        if chip_base in m.group():
            content = content[:m.start()] + new_card + "\n" + content[m.end():]
            print(f"✅ [REPLACE] 준비중 카드 교체: {chip_base}")
            with open(landing_path, "w", encoding="utf-8") as f:
                f.write(content)
            return

    # 3. 해당 섹션의 approach-grid 첫 줄 뒤에 삽입
    section_comment = info["section"]
    sec_pos = content.find(section_comment)

    if sec_pos != -1:
        grid_pos = content.find('<div class="approach-grid">', sec_pos)
        if grid_pos != -1:
            insert_pos = content.find('\n', grid_pos) + 1
            content = content[:insert_pos] + new_card + "\n" + content[insert_pos:]
            print(f"✅ [INSERT] 섹션에 카드 추가: {section_comment}")
            with open(landing_path, "w", encoding="utf-8") as f:
                f.write(content)
            return

    # 4. EV 섹션 등 섹션 자체가 없으면 신규 섹션 추가 (상담 섹션 바로 위)
    anchor = '<section class="reveal">\n  <h2 class="sec-title">상담 연결하기</h2>'
    insert_pos = content.find(anchor)
    if insert_pos == -1:
        insert_pos = len(content) - 200
    new_section = (
        f'\n  {section_comment}\n'
        f'  <div class="class-label">{info["class_name"]}</div>\n'
        f'  <div class="approach-grid">\n'
        f'{new_card}\n'
        f'  </div>\n'
    )
    content = content[:insert_pos] + new_section + content[insert_pos:]
    print(f"✅ [NEW SECTION] 새 섹션 생성 후 카드 추가: {section_comment}")
    with open(landing_path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 update_landing.py <filename.html>")
        sys.exit(1)
    landing = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BenzDream_Landing.html")
    if not os.path.exists(landing):
        print(f"❌ Landing page not found: {landing}")
        sys.exit(1)
    update_landing(landing, sys.argv[1])
    print(f"🚀 Landing page updated → push 후 반영됩니다.")
