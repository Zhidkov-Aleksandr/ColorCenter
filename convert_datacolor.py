import pyodbc
import json
import socket
import re

def get_connection():
    computer_name = socket.gethostname()
    drivers = ['{ODBC Driver 17 for SQL Server}', '{ODBC Driver 13 for SQL Server}', '{SQL Server Native Client 11.0}', '{SQL Server}']
    server_variants = [r'.\SQLEXPRESS', rf'{computer_name}\SQLEXPRESS', r'localhost\SQLEXPRESS', r'(local)\SQLEXPRESS']
    
    for driver in drivers:
        for server in server_variants:
            try:
                conn_str = f'DRIVER={driver};SERVER={server};DATABASE=YDatacolorLab;Trusted_Connection=yes;Timeout=2;'
                return pyodbc.connect(conn_str)
            except pyodbc.Error:
                continue
    raise Exception("Не удалось подключиться к SQL Server.")

def clean_guid(text):
    if not text: return ""
    return re.sub(r'\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?\|?', '', text).strip()

def convert():
    print("Подключение к базе данных Datacolor...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"Ошибка: {e}")
        return

    # --- 1. ЗАГРУЖАЕМ ВСЕ КАТАЛОГИ ---
    cursor.execute("SELECT ID_CARD, CODE_CARD, DESCRIPTION FROM YMITYADM.COLOR_CARDS")
    all_catalogs = {}
    for row in cursor.fetchall():
        card_id = int(row[0])
        code = str(row[1]).strip() if row[1] else ""
        desc = str(row[2]).strip() if row[2] else code
        all_catalogs[card_id] = desc

    # --- 2. РАЗДЕЛЯЕМ БАЗЫ 45013 И ПИГМЕНТЫ ---
    cursor.execute("SELECT ID_COMPONENT, CODE_COMPONENT, DESCRIPTION, DENSITY FROM YMITYADM.COMPONENTS")
    colorants = {}
    base_ids = {}

    for row in cursor.fetchall():
        c_id = int(row[0])
        code = str(row[1]).strip() if row[1] else ""
        desc = str(row[2]).strip() if row[2] else code
        density = float(row[3]) if row[3] is not None else 1.0

        # Ищем строго 45013, чтобы не захватить другие базы (например, 45014)
        if '45013' in code or '45013' in desc:
            base_ids[c_id] = "45013-91x Seri (Белая)" if "91" in code or "91" in desc else "45013-00x Seri (Прозрачная)"
        else:
            colorants[c_id] = {"code": code, "desc": desc, "sg": density}

    # Резервный поиск, если 45013 не найдено
    if not base_ids:
        for c_id, data in colorants.items():
            if '4501' in data['code'] or '4501' in data['desc']:
                base_ids[c_id] = "45013-91x Seri (Белая)" if "91" in data['code'] or "91" in data['desc'] else "45013-00x Seri (Прозрачная)"
        # Удаляем найденные базы из пигментов
        for b_id in base_ids.keys():
            colorants.pop(b_id, None)

    print(f"Используем ID баз: {list(base_ids.keys())}")

    # --- 3. НАХОДИМ ВСЕ ФОРМУЛЫ 4501 И БЕРЕМ САМЫЕ СВЕЖИЕ СТАНДАРТЫ ---
    base_id_str = ",".join(map(str, base_ids.keys()))
    
    # ДОБАВЛЕНО: f.STATUS = 'V' (только утвержденные) и f.ID_POS_SPECIFIC IS NULL (без локальных правок)
    cursor.execute(f"""
        SELECT f.ID_FORMULA, f.CODE_REF_COLOR, fc.ID_COMPONENT
        FROM YMITYADM.FORMULAS f
        JOIN YMITYADM.FORMULA_COMPONENTS fc ON f.ID_FORMULA = fc.ID_FORMULA
        WHERE fc.ID_COMPONENT IN ({base_id_str})
          AND f.STATUS = 'V'
          AND f.ID_POS_SPECIFIC IS NULL
        ORDER BY f.DATE_MODIFY ASC, f.ID_FORMULA ASC
    """)
    
    formulas_by_ref = {}
    for row in cursor.fetchall():
        f_id, ref_color, b_id = int(row[0]), str(row[1]).strip(), int(row[2])
        formulas_by_ref[ref_color] = {"id": f_id, "base": base_ids[b_id], "components": []}

    formulas_by_id = {data["id"]: data for data in formulas_by_ref.values()}
    print(f"Найдено уникальных (проверенных) рецептов: {len(formulas_by_id)}")

    # --- 4. ЗАГРУЖАЕМ ПИГМЕНТЫ ДЛЯ ПОБЕДИВШИХ ФОРМУЛ ---
    cursor.execute(f"""
        SELECT ID_FORMULA, ID_COMPONENT, QUANTITY
        FROM YMITYADM.FORMULA_COMPONENTS
        WHERE ID_COMPONENT NOT IN ({base_id_str})
    """)
    
    for row in cursor.fetchall():
        f_id = int(row[0])
        if f_id in formulas_by_id:
            comp_id = int(row[1])
            qty = float(row[2]) if row[2] is not None else 0.0
            formulas_by_id[f_id]["components"].append([comp_id, qty])

    # --- 5. ПРИВЯЗЫВАЕМ К ЦВЕТАМ И ФИЛЬТРУЕМ ПУСТЫЕ КАТАЛОГИ ---
    colors = {}
    colors_in_card = {}
    valid_catalogs = {}
    
    for card_id, card_name in all_catalogs.items():
        cursor.execute("SELECT ID_COLOR, CODE_COLOR, DESCRIPTION, CODE_REF_COLOR FROM YMITYADM.COLORS WHERE ID_CARD = ?", (card_id,))
        color_ids_for_this_card = []
        
        for row in cursor.fetchall():
            c_id, c_code = int(row[0]), str(row[1]).strip() if row[1] else ""
            c_desc = str(row[2]).strip() if row[2] else c_code
            ref_color = str(row[3]).strip()

            if ref_color in formulas_by_ref:
                colors[c_id] = {
                    "code": c_code,
                    "name": clean_guid(c_desc),
                    "base_name": formulas_by_ref[ref_color]["base"],
                    "formula": formulas_by_ref[ref_color]["components"]
                }
                color_ids_for_this_card.append(c_id)
                
        if color_ids_for_this_card:
            colors_in_card[card_id] = color_ids_for_this_card
            valid_catalogs[card_id] = card_name

    # --- 6. СОХРАНЯЕМ ФИНАЛЬНЫЙ JSON ---
    final_db = {
        "catalogs": valid_catalogs, 
        "colors_in_card": colors_in_card,
        "colors": colors, 
        "colorants": colorants
    }
    with open('datacolor.json', 'w', encoding='utf-8') as f:
        json.dump(final_db, f, ensure_ascii=False, indent=2)
    
    print(f"УСПЕХ! Сгенерирован datacolor.json.")
    print(f"Загружено каталогов с цветами: {len(valid_catalogs)}")
    print(f"Всего цветов загружено: {len(colors)}")

if __name__ == "__main__":
    convert()
