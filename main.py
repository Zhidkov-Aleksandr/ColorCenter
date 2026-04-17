import json
import sys

def load_database(filepath):
    # Словари для хранения связей и данных
    collections = {}      # ID коллекции -> Название
    cards = {}            # ID каталога -> Название
    card_in_coll = {}     # ID каталога -> ID коллекции
    colors_in_card = {}   # ID каталога -> список ID цветов
    
    colors = {}           # ID цвета -> {code, name, formula}
    colorants = {}        # ID пигмента -> {code, desc}

    print("Загрузка базы данных, пожалуйста, подождите...")
    try:
        with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
            for line in f:
                line = line.strip()
                # Пропускаем строки без данных (сплиттер внутри базы: ;;)
                if not line or ';;' not in line:
                    continue

                parts = line.split(';;', 1)
                if len(parts) != 2:
                    continue
                
                meta = parts[0].split(';')
                if len(meta) < 2:
                    continue

                table_name = meta[1].lower()
                try:
                    data = json.loads(parts[1])
                except json.JSONDecodeError:
                    continue

                # Извлечение данных по соответствующим таблицам
                if table_name == 'cardcollection':
                    collections[data.get('CARDCOLLECTIONID')] = data.get('COLLECTIONNAME', 'Без названия')
                elif table_name == 'colourcard':
                    cards[data.get('COLOURCARDID')] = data.get('CARDNAME', 'Без названия')
                elif table_name == 'cardincollection':
                    card_in_coll[data.get('COLOURCARDID')] = data.get('CARDCOLLECTIONID')
                elif table_name == 'colourincard':
                    cid = data.get('COLOURCARDID')
                    col_id = data.get('COLOURID')
                    if cid is not None and col_id is not None:
                        colors_in_card.setdefault(cid, []).append(col_id)
                elif table_name == 'colour':
                    cid = data.get('COLOURID')
                    if cid is not None:
                        colors.setdefault(cid, {})['code'] = data.get('COLOURCODE', '')
                elif table_name == 'colname':
                    cid = data.get('COLOURID')
                    if cid is not None:
                        colors.setdefault(cid, {})['name'] = data.get('COLOURNAME', '')
                elif table_name == 'formula':
                    cid = data.get('COLOURID')
                    if cid is not None:
                        try:
                            # CNTINFORMULA содержит JSON массив с пигментами и их количеством
                            formula_str = data.get('CNTINFORMULA', '')
                            if formula_str:
                                f_data = json.loads(formula_str)
                                if len(f_data) == 2:
                                    colors.setdefault(cid, {})['formula'] = list(zip(f_data[0], f_data[1]))
                        except Exception:
                            pass
                elif table_name == 'colorant':
                    cnt_id = data.get('CNTID')
                    if cnt_id is not None:
                        colorants[cnt_id] = {
                            'code': data.get('CNTCODE', ''),
                            'desc': data.get('DESCRIPTION', '')
                        }
    except FileNotFoundError:
        print(f"Файл '{filepath}' не найден!")
        sys.exit(1)

    # Формируем итоговый список каталогов
    catalogs = {}
    catalog_colors = {}
    
    # Если есть коллекции, объединяем цвета из каталогов по коллекциям
    if collections and card_in_coll:
        catalogs = collections
        for card_id, col_ids in colors_in_card.items():
            coll_id = card_in_coll.get(card_id)
            if coll_id is not None:
                catalog_colors.setdefault(coll_id, []).extend(col_ids)
    else:
        # Иначе используем colourcard (как отдельные каталоги)
        catalogs = cards
        catalog_colors = colors_in_card

    return catalogs, catalog_colors, colors, colorants

def main():
    db_file = 'innovatint.db'
    catalogs, catalog_colors, colors, colorants = load_database(db_file)

    if not catalogs:
        print("Каталоги не найдены в базе.")
        return

    while True:
        print("\n" + "="*50)
        print(" ДОСТУПНЫЕ КАТАЛОГИ (CARD COLLECTIONS)")
        print("="*50)
        for cat_id, cat_name in catalogs.items():
            print(f" [{cat_id}] {cat_name}")
        
        cat_input = input("\nВведите ID каталога (или 'q' для выхода): ")
        if cat_input.lower() == 'q':
            break
            
        try:
            selected_cat_id = int(cat_input)
            if selected_cat_id not in catalogs:
                print("-> Ошибка: неверный ID каталога.")
                continue
        except ValueError:
            print("-> Ошибка: введите числовой ID.")
            continue

        col_ids = catalog_colors.get(selected_cat_id, [])
        if not col_ids:
            print("-> В этом каталоге нет цветов.")
            continue

        # Создаем словарь доступных цветов для поиска
        available_colors = {}
        for c_id in col_ids:
            cdata = colors.get(c_id, {})
            c_name = cdata.get('name', 'Без названия')
            c_code = cdata.get('code', 'Без кода')
            available_colors[c_id] = f"{c_code} - {c_name}"

        print(f"\n--- Выбран каталог: {catalogs[selected_cat_id]} ---")
        search = input("Введите код или название цвета для поиска (или нажмите Enter, чтобы показать первые 30): ").strip().lower()

        matches = []
        for c_id, text in available_colors.items():
            if search in text.lower():
                matches.append((c_id, text))

        if not search:
            matches = matches[:30]  # Чтобы не забивать консоль тысячами цветов

        if not matches:
            print("-> Цвета по вашему запросу не найдены.")
            continue

        print("\nНАЙДЕННЫЕ ЦВЕТА:")
        for c_id, text in matches:
            print(f" [{c_id}] {text}")

        color_input = input("\nВведите ID нужного цвета: ")
        try:
            color_id = int(color_input)
            if color_id not in [m[0] for m in matches]:
                print("-> Ошибка: ID не из списка.")
                continue
        except ValueError:
            print("-> Ошибка: введите числовой ID.")
            continue

        # Ввод количества основы
        base_amount_input = input("\nВведите количество основы (например, 1.0 для 1 литра или 2.5): ").replace(',', '.')
        try:
            base_amount = float(base_amount_input)
        except ValueError:
            print("-> Ошибка: неверный формат количества.")
            continue

        # Вывод рецептуры
        cdata = colors.get(color_id, {})
        formula = cdata.get('formula', [])
        
        if not formula:
            print(f"-> Для цвета '{available_colors[color_id]}' нет формулы пигментов в базе.")
            continue

        print("\n" + "*"*50)
        print(f" РЕЦЕПТ ДЛЯ ЦВЕТА: {available_colors[color_id]}")
        print(f" КОЛИЧЕСТВО ОСНОВЫ: {base_amount}")
        print("*"*50)
        print("Пигменты к добавлению:")
        
        for cnt_id, amount in formula:
            pigment = colorants.get(cnt_id, {})
            p_code = pigment.get('code', f'ID:{cnt_id}')
            p_desc = pigment.get('desc', 'Неизвестный пигмент')
            if not p_desc:
                p_desc = p_code
            
            # В базе значения хранятся для стандартной 1 единицы основы
            # Мы умножаем пропорционально введенному количеству
            calc_amount = amount * base_amount
            print(f" - [{p_code}] {p_desc}: {calc_amount:.4f}")
        print("*"*50 + "\n")

if __name__ == "__main__":
    main()
