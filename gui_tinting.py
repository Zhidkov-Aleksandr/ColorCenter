import json
import sys
import os
import tempfile
import re
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# --- ЛОГИКА БАЗЫ ДАННЫХ ---

# Справочник пигментов Innovatint
PIGMENT_DESC_INNOVATINT = {
    "302": "SEDIPAN SCU Oxford blue 4 kg RU паста колеровочная кобальтово-синяя",
    "306": "SEDIPAN SCU Alfa blue 6 kg RU паста колеровочная лазурно-синяя",
    "326": "SEDIPAN SCU Fresh green 6 kg RU паста колеровочная салатово-зеленая",
    "328": "SEDIPAN SCU Dark green 4 kg RU паста колеровочная темная зеленая",
    "312": "SEDIPAN SCU Standard black 4 kg RU паста колеровочная темная черная",
    "338": "SEDIPAN SCU Bright red 4 kg RU паста колеровочная яркая красная",
    "339": "SEDIPAN SCU Crimson red 4 kg RU паста колеровочная малиново-красная",
    "333": "SEDIPAN SCU Maroon red 6 kg RU паста колеровочная темная бордовая",
    "363": "SEDIPAN SCU Midnight violet 4 kg RU паста колеровочная темная фиолетовая",
    "353": "SEDIPAN SCU Standard white 6 kg RU паста колеровочная белая",
    "341": "SEDIPAN SCU Yellow brown 6 kg RU паста колеровочная коричнево-желтая",
    "345": "SEDIPAN SCU Soft orange 6 kg RU паста колеровочная желто-оранжевая",
    "346": "SEDIPAN SCU Lemon yellow 6 kg RU паста колеровочная лимонно-желтая",
    "349": "SEDIPAN SCU Standard orange 4 kg RU паста колеровочная оранжевая",
    "309": "SEDIPAN SCU Dark blue 4 kg RU паста колеровочная темная синяя"
}

# Справочник пигментов Datacolor
PIGMENT_DESC_DATACOLOR = {
    "400LP31": "зеленовато-желтый банка 3,5 кг",
    "400LP32": "красно-желтый банка 3,5 кг",
    "400LP33": "ярко-желтый банка 3,5 кг",
    "400LP34N": "оранжевый банка 3,5 кг",
    "400LP35": "розовый банка 3,5 кг",
    "400LP36": "оксидно-красный банка 3,5 кг",
    "400LP37": "бордовый банка 3,5 кг",
    "400LP38": "синий банка 3,5 кг",
    "400LP39": "черная банка 3,5 кг",
    "400LP40": "зеленый банка 3,5 кг",
    "400LP41": "оранжево-желтый банка 3,5 кг",
    "400LP47": "фиолетовый банка 3,5 кг",
    "400LP55": "красный банка 3,5 кг",
    "400LP61": "желтый банка 3,5 кг",
    "400LP64": "оранжевый банка 3,5 кг",
    "400LP30": "белый банка 3,5 кг"
}

def load_innovatint(filepath):
    colors_in_card, colors, colorants, products_to_base, base_names = {}, {}, {}, {}, {}
    try:
        with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or ';;' not in line: continue
                parts = line.split(';;', 1)
                meta = parts[0].split(';')
                table_name = meta[1].lower()
                data = json.loads(parts[1])

                if table_name == 'colourincard':
                    cid, col_id = data.get('COLOURCARDID'), data.get('COLOURID')
                    if cid is not None: colors_in_card.setdefault(cid, []).append(col_id)
                elif table_name == 'colour':
                    cid = data.get('COLOURID')
                    if cid is not None: colors.setdefault(cid, {})['code'] = data.get('COLOURCODE', '')
                elif table_name == 'colname':
                    cid = data.get('COLOURID')
                    if cid is not None: colors.setdefault(cid, {})['name'] = data.get('COLOURNAME', '')
                elif table_name == 'abstractbase':
                    abid = data.get('ABASEID')
                    if abid is not None: base_names[abid] = data.get('ABASECODE', '')
                elif table_name == 'formula':
                    cid = data.get('COLOURID')
                    if cid is not None:
                        abid = data.get('ABASEID')
                        if abid is not None: products_to_base[cid] = abid
                        try:
                            f_data = json.loads(data.get('CNTINFORMULA', ''))
                            if len(f_data) == 2:
                                colors.setdefault(cid, {})['formula'] = list(zip(f_data[0], f_data[1]))
                        except: pass
                elif table_name == 'colorant':
                    cnt_id = data.get('CNTID')
                    if cnt_id is not None:
                        code = str(data.get('CNTCODE', ''))
                        desc = PIGMENT_DESC_INNOVATINT.get(code, data.get('DESCRIPTION', "Паста колеровочная"))
                        sg = float(data.get('SPECIFICGRAVITY', 1.0))
                        colorants[cnt_id] = {'code': code, 'desc': desc, 'sg': sg}
    except Exception as e:
        print("Ошибка загрузки Innovatint:", e)
        return None, None, None, None

    final_products = {}
    for cid, abid in products_to_base.items():
        base_code = base_names.get(abid, str(abid))
        suffix = " ЭМАЛЬ" if "605" in str(base_code) else ""
        final_products[cid] = f"{base_code}{suffix}"

    return colors_in_card, colors, colorants, final_products

def load_datacolor(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        catalogs = {int(k): v for k, v in data.get('catalogs', {}).items()}
        colors_in_card = {int(k): v for k, v in data.get('colors_in_card', {}).items()}
        colors = {int(k): v for k, v in data.get('colors', {}).items()}
        colorants = {int(k): v for k, v in data.get('colorants', {}).items()}

        products = {}
        for cid, cdata in colors.items():
            products[cid] = cdata.get('base_name', 'Не определена')

        return catalogs, colors_in_card, colors, colorants, products
    except Exception as e:
        print("Ошибка загрузки Datacolor:", e)
        return None, None, None, None, None

# --- ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ---

class TintingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ЛАКИ ДА КРАСКИ  +7 (985) 265-45-33")
        # Уменьшена общая высота окна до 600 пикселей
        self.root.geometry("971x600")
        self.root.configure(bg="#f5f5f7")

        self.target_catalogs_innovatint = {
            12: ">>> [12] Полиуретановый RAL K7 <<<",
            20: ">>> [20] Полиуретановый SAYERLACK <<<",
            23: ">>> [23] Полиуретановый NCS 1950 <<<",
            1: "Акриловый RAL K7", 2: "Акриловый CS Renner", 5: "Акриловый NCS 1950",
            13: "Полиуретановый Monicolor (ГЛЯНЕЦ)", 14: "Полиуретановый RAL K7 (ГЛЯНЕЦ)",
            15: "Полиуретановый NCS 1950 (ГЛЯНЕЦ)", 16: "Полиуретановый CS Renner (ГЛЯНЕЦ)",
            17: "Полиуретановый SAYERLACK (ГЛЯНЕЦ)", 19: "Полиуретановый RAL K7, паст 30%",
            21: "Полиуретановый CS Renner", 22: "Полиуретановый Monicolor",
            24: "Полиуретановый RAL K7 (SPUT-601)", 25: "Полиуретановый NCS 1950 (SPUT-601)",
            26: "Полиуретановый Dulux", 27: "Полиуретановый CS Renner (SPUT-601)",
            28: "Полиуретановый Monicolor (SPUT-601)", 31: "Полиуретановый SAYERLACK (SPUT-601)",
            33: "Полиуретановый ICA", 34: "Полиуретановый ICA (SPUT-601)",
            35: "Полиуретановый Dulux (SPUT-601)", 36: "Акриловый Monicolor"
        }

        self.available_colors_for_cat = []
        self.current_formula = []
        
        self.current_base_weight = 0.0
        self.current_pigments_weight_kg = 0.0
        self.current_total_weight = 0.0
        self.current_display_base_name = ""

        self.setup_styles()
        self.build_ui()
        self.load_system()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", font=("Segoe UI", 11), rowheight=35)
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))
        style.configure("Action.TButton", font=("Segoe UI", 13, "bold"), background="#007AFF", foreground="white")

    def build_ui(self):
        # Сужен фрейм заголовка (убрана жесткая высота)
        header = tk.Frame(self.root, bg="#1a252f")
        header.pack(fill=tk.X)
        # Шрифта заголовка уменьшен до 16, отступы pady уменьшены до 10
        tk.Label(header, text="КОЛЕРОВОЧНЫЙ ЦЕНТР", bg="#1a252f", fg="white", font=("Segoe UI", 16, "bold"), pady=10).pack()

        # Уплотнен контейнер (pady уменьшен до 5)
        container = tk.Frame(self.root, bg="#f5f5f7", padx=30, pady=5)
        container.pack(fill=tk.BOTH, expand=True)

        sys_frame = tk.Frame(container, bg="#f5f5f7")
        # Уменьшен отступ pady до 5
        sys_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(sys_frame, text="ВЫБОР СИСТЕМЫ:", font=("Segoe UI", 10, "bold"), bg="#f5f5f7", fg="#c0392b").pack(side=tk.LEFT)
        self.cb_system = ttk.Combobox(sys_frame, width=30, state="readonly", font=("Segoe UI", 12, "bold"))
        self.cb_system['values'] = ["Система Innovatint", "Система Datacolor"]
        self.cb_system.current(0)
        # Уменьшен отступ padx до 5
        self.cb_system.pack(side=tk.LEFT, padx=5)
        self.cb_system.bind('<<ComboboxSelected>>', lambda e: self.load_system())

        tk.Label(container, text="ВЫБОР КАТАЛОГА:", font=("Segoe UI", 10, "bold"), bg="#f5f5f7", fg="#7f8c8d").pack(anchor="w")
        self.cb_catalog = ttk.Combobox(container, width=80, state="readonly", font=("Segoe UI", 11))
        # Уменьшен отступ pady до 10
        self.cb_catalog.pack(fill=tk.X, pady=(2, 10))
        self.cb_catalog.bind('<<ComboboxSelected>>', self.on_catalog_select)

        row2 = tk.Frame(container, bg="#f5f5f7")
        # Уменьшен отступ pady до 2
        row2.pack(fill=tk.X, pady=2)

        search_sub = tk.Frame(row2, bg="#f5f5f7")
        search_sub.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(search_sub, text="ПОИСК ЦВЕТА:", font=("Segoe UI", 10, "bold"), bg="#f5f5f7", fg="#7f8c8d").pack(anchor="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.on_search_change)
        self.entry_search = ttk.Entry(search_sub, textvariable=self.search_var, font=("Segoe UI", 12))
        # Уплотнено: pady=2, padx=(0, 5)
        self.entry_search.pack(fill=tk.X, pady=2, padx=(0, 5))

        # Блок выбора пропорции (для прозрачных баз)
        ratio_sub = tk.Frame(row2, bg="#f5f5f7")
        # Уменьшен отступ padx до 5
        ratio_sub.pack(side=tk.LEFT, padx=5)
        self.lbl_ratio = tk.Label(ratio_sub, text="ПРОПОРЦИЯ (Прозр.):", font=("Segoe UI", 10, "bold"), bg="#f5f5f7", fg="#7f8c8d")
        self.lbl_ratio.pack(anchor="w")
        self.ratio_var = tk.StringVar(value="70/30")
        self.cb_ratio = ttk.Combobox(ratio_sub, textvariable=self.ratio_var, values=["70/30", "80/20"], state=tk.DISABLED, width=12, font=("Segoe UI", 12, "bold"))
        # Уменьшен отступ pady до 2
        self.cb_ratio.pack(pady=2)
        self.cb_ratio.bind('<<ComboboxSelected>>', self.update_table)

        weight_sub = tk.Frame(row2, bg="#f5f5f7")
        weight_sub.pack(side=tk.RIGHT)
        self.lbl_weight_title = tk.Label(weight_sub, text="ВЕС (КГ):", font=("Segoe UI", 10, "bold"), bg="#f5f5f7", fg="#7f8c8d")
        self.lbl_weight_title.pack(anchor="w")
        self.weight_var = tk.StringVar(value="1.00")
        self.weight_var.trace_add('write', self.update_table)
        self.entry_weight = ttk.Entry(weight_sub, textvariable=self.weight_var, width=15, font=("Segoe UI", 14, "bold"), justify="center")
        # Уменьшен отступ pady до 2
        self.entry_weight.pack(pady=2)

        res_frame = tk.Frame(container, bg="#f5f5f7")
        # Уменьшен отступ pady до 5
        res_frame.pack(fill=tk.X, pady=(5, 0))
        self.btn_copy = tk.Button(res_frame, text="📋 КОПИРОВАТЬ ДЛЯ БАЗЫ", font=("Segoe UI", 9, "bold"), bg="#dcdde1", fg="#7f8c8d", relief=tk.FLAT, state=tk.DISABLED, command=self.copy_to_clipboard)
        self.btn_copy.pack(side=tk.LEFT)

        tk.Label(res_frame, text="    ВЫБРАННЫЙ ЦВЕТ:", font=("Segoe UI", 10, "bold"), bg="#f5f5f7", fg="#7f8c8d").pack(side=tk.LEFT)
        
        self.cb_color = ttk.Combobox(container, state="readonly", font=("Segoe UI", 12))
        # Уменьшен отступ pady до 5
        self.cb_color.pack(fill=tk.X, pady=(2, 5))
        self.cb_color.bind('<<ComboboxSelected>>', self.update_table)

        self.lbl_product = tk.Label(container, text="БАЗА: ---", font=("Segoe UI", 15, "bold"), bg="#f5f5f7", fg="#e67e22")
        # Уменьшен отступ pady до 2
        self.lbl_product.pack(pady=2)

        cols = ("code", "name", "qty")
        # ВАЖНО: Высота таблицы (height) уменьшена с 8 до 5 строк
        self.tree = ttk.Treeview(container, columns=cols, show="headings", height=5)
        self.tree.heading("code", text="КОД")
        self.tree.heading("name", text="НАИМЕНОВАНИЕ ПИГМЕНТА")
        self.tree.heading("qty", text="ВЕС (ГРАММЫ)")
        self.tree.column("code", width=100, anchor="center")
        self.tree.column("name", width=550)
        self.tree.column("qty", width=150, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.btn_print = ttk.Button(container, text="🖨 ПЕЧАТЬ ЗАДАНИЯ", style="Action.TButton", command=self.print_task)
        # Уплотнены отступы кнопки: pady=10, ipady=8
        self.btn_print.pack(fill=tk.X, pady=(10, 0), ipady=8)

    def load_system(self):
        system_choice = self.cb_system.get()
        self.clear_table()
        self.cb_catalog.set('')
        self.cb_color.set('')
        self.search_var.set('')
        self.cb_ratio.config(state=tk.DISABLED)

        if system_choice == "Система Innovatint":
            res = load_innovatint('innovatint.db')
            if res[0] is not None:
                self.colors_in_card, self.colors, self.colorants, self.products = res
                sorted_cats = []
                favs = [12, 20, 23]
                for k in favs: sorted_cats.append(self.target_catalogs_innovatint[k])
                for k, v in self.target_catalogs_innovatint.items():
                    if k not in favs: sorted_cats.append(f"[{k}] {v}")
                self.cb_catalog['values'] = sorted_cats
            else:
                messagebox.showerror("Ошибка", "Файл innovatint.db не найден!")

        elif system_choice == "Система Datacolor":
            res = load_datacolor('datacolor.json')
            if res[0] is not None:
                catalogs, self.colors_in_card, self.colors, self.colorants, self.products = res
                favs_dc = [6, 7, 14, 81]
                sorted_cats = []
                for k in favs_dc:
                    if k in catalogs:
                        sorted_cats.append(f">>> [{k}] {catalogs[k]} <<<")
                for k, v in catalogs.items():
                    if k not in favs_dc:
                        sorted_cats.append(f"[{k}] {v}")
                self.cb_catalog['values'] = sorted_cats
            else:
                messagebox.showerror("Ошибка", "Файл datacolor.json не найден!")

    def on_catalog_select(self, event):
        sel = self.cb_catalog.get()
        try:
            cat_id = int(re.search(r'\[(\d+)\]', sel).group(1))
        except:
            return

        col_ids = self.colors_in_card.get(cat_id, [])
        self.available_colors_for_cat = []
        for c_id in col_ids:
            c = self.colors.get(c_id, {})
            c_code = c.get('code', '').strip()
            c_name = c.get('name', '').strip()
            
            clean_code = re.sub(r'\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?\|?', '', c_code).strip()
            clean_name = re.sub(r'\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?\|?', '', c_name).strip()
            
            # УМНАЯ ОЧИСТКА ДУБЛЕЙ (Учитывает пробелы, регистр и вложенность слов)
            cc_compare = clean_code.upper().replace(" ", "")
            cn_compare = clean_name.upper().replace(" ", "")
            
            if cc_compare == cn_compare:
                clean_text = clean_code
            elif cn_compare.startswith(cc_compare):
                clean_text = clean_name
            elif cc_compare.startswith(cn_compare):
                clean_text = clean_code
            else:
                clean_text = f"{clean_code} {clean_name}"
                
            clean_text = ' '.join(clean_text.split()).strip()
            self.available_colors_for_cat.append({'id': c_id, 'text': clean_text})
            
        self.entry_search.delete(0, tk.END)
        self.filter_colors()

    def on_search_change(self, *args):
        self.filter_colors()

    def filter_colors(self):
        query = self.search_var.get().lower()
        filtered = [c for c in self.available_colors_for_cat if query in c['text'].lower()]
        vals = [f"[{c['id']}] {c['text']}" for c in filtered]
        self.cb_color['values'] = vals
        if vals:
            self.cb_color.current(0)
            self.update_table()
        else:
            self.cb_color.set('')
            self.clear_table()

    def clear_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        self.lbl_product.config(text="БАЗА: ---")
        self.lbl_weight_title.config(text="ВЕС (КГ):")
        self.current_base_weight = 0.0
        self.current_pigments_weight_kg = 0.0
        self.current_total_weight = 0.0
        self.current_display_base_name = ""
        self.btn_copy.config(state=tk.DISABLED, bg="#dcdde1", fg="#7f8c8d")

    def update_table(self, *args):
        for i in self.tree.get_children(): self.tree.delete(i)
        sel = self.cb_color.get()
        if not sel: 
            self.btn_copy.config(state=tk.DISABLED, bg="#dcdde1", fg="#7f8c8d")
            return
            
        try:
            input_weight = float(self.weight_var.get().replace(',', '.'))
        except:
            input_weight = 0.0

        color_id = int(sel.split(']')[0][1:])
        base_name = self.products.get(color_id, "Не определена")
        system_choice = self.cb_system.get()
        
        # Определяем тип базы
        if system_choice == "Система Datacolor":
            if any(x in base_name.upper() for x in ["00", "CLEAR", "TR", "ПРОЗРАЧ"]):
                is_clear_base = True
                self.current_display_base_name = "БАЗА: 45013-00x Seri"
            else:
                is_clear_base = False
                self.current_display_base_name = "БАЗА: 45013-91x Seri"
        else:
            is_clear_base = any(x in base_name.upper() for x in ["500", "520", "650 CLEAR"])
            self.current_display_base_name = f"БАЗА: {base_name}"

        # Управление интерфейсом в зависимости от типа базы
        if is_clear_base:
            self.lbl_weight_title.config(text="ОБЩИЙ ВЕС (КГ):")
            if system_choice == "Система Datacolor":
                self.cb_ratio.config(state="readonly")
        else:
            self.lbl_weight_title.config(text="ВЕС ОСНОВЫ (КГ):")
            self.cb_ratio.config(state=tk.DISABLED)

        formula = self.colors.get(color_id, {}).get('formula', [])
        
        # --- МАТЕМАТИКА ---
        if system_choice == "Система Datacolor":
            raw_total_pigment = sum(base_qty for p_id, base_qty in formula)

            if is_clear_base:
                # Читаем пропорцию из списка
                ratio_str = self.ratio_var.get()
                if ratio_str == "80/20":
                    base_fraction, pigment_fraction = 0.80, 0.20
                else:
                    base_fraction, pigment_fraction = 0.70, 0.30

                self.current_total_weight = input_weight
                self.current_pigments_weight_kg = input_weight * pigment_fraction
                self.current_base_weight = input_weight * base_fraction
            else:
                self.current_base_weight = input_weight
                self.current_pigments_weight_kg = (input_weight * raw_total_pigment) / 1000
                self.current_total_weight = self.current_base_weight + self.current_pigments_weight_kg

        else:
            # Математика Innovatint (через SG)
            total_pigment_weight_rate = sum(base_qty * self.colorants.get(p_id, {}).get('sg', 1.0) for p_id, base_qty in formula)
            if is_clear_base:
                self.current_total_weight = input_weight
                self.current_base_weight = input_weight / (1 + total_pigment_weight_rate / 1000) if total_pigment_weight_rate else input_weight
                self.current_pigments_weight_kg = self.current_total_weight - self.current_base_weight
            else:
                self.current_base_weight = input_weight
                self.current_pigments_weight_kg = (input_weight * total_pigment_weight_rate) / 1000
                self.current_total_weight = self.current_base_weight + self.current_pigments_weight_kg

        self.current_formula = []

        for p_id, base_qty in formula:
            pigment = self.colorants.get(p_id, {})
            p_code = pigment.get('code', '???')
            p_sg = pigment.get('sg', 1.0)
            
            # Подставляем русские названия из словарей
            if system_choice == "Система Datacolor" and p_code in PIGMENT_DESC_DATACOLOR:
                p_desc = PIGMENT_DESC_DATACOLOR[p_code]
            else:
                p_desc = pigment.get('desc', 'Паста')

            # Расчет веса конкретного пигмента
            if system_choice == "Система Datacolor":
                if is_clear_base and raw_total_pigment > 0:
                    # Раскидываем 30% (или 20%) пропорционально составу
                    pigment_weight_g = (base_qty / raw_total_pigment) * (self.current_pigments_weight_kg * 1000)
                else:
                    pigment_weight_g = base_qty * self.current_base_weight
            else:
                pigment_weight_g = base_qty * self.current_base_weight * p_sg

            self.current_formula.append((p_code, p_desc, f"{pigment_weight_g:.2f}"))

        self.current_formula.sort(key=lambda x: x[0])

        for p_code, p_desc, calc_qty in self.current_formula:
            self.tree.insert("", tk.END, values=(p_code, p_desc, calc_qty))

        # Формируем текст с пропорцией для заголовка
        ratio_text = f" ({self.ratio_var.get()})" if (system_choice == "Система Datacolor" and is_clear_base) else ""
        
        self.lbl_product.config(text=f"{self.current_display_base_name}{ratio_text}   |   ВЕС ОСНОВЫ: {self.current_base_weight:.3f} кг   |   ВЕС ПИГМЕНТОВ: {self.current_pigments_weight_kg:.3f} кг")

        if self.current_total_weight > 0:
            self.btn_copy.config(state=tk.NORMAL, bg="#27ae60", fg="white")
        else:
            self.btn_copy.config(state=tk.DISABLED, bg="#dcdde1", fg="#7f8c8d")

    def copy_to_clipboard(self):
        sel = self.cb_color.get()
        if not sel: return
        color_name = sel.split('] ', 1)[-1] 
        text_to_copy = f"{color_name} - {self.current_total_weight:.3f} кг"
        
        # Добавляем пропорцию при копировании, если это прозрачная база Datacolor
        if self.cb_system.get() == "Система Datacolor" and "45013-00" in self.current_display_base_name:
            text_to_copy += f" ({self.ratio_var.get()})"
            
        self.root.clipboard_clear()
        self.root.clipboard_append(text_to_copy)
        self.root.update()

    def print_task(self):
        color_info = self.cb_color.get()
        catalog_info = self.cb_catalog.get().replace('>>>', '').replace('<<<', '').strip()
        if not color_info or not self.current_formula: return

        today = datetime.now().strftime("%d.%m.%Y %H:%M")
        ratio_text = f" ({self.ratio_var.get()})" if (self.cb_system.get() == "Система Datacolor" and "45013-00" in self.current_display_base_name) else ""

        content = "============================================================\n"
        content += "                   ЗАДАНИЕ НА КОЛЕРОВКУ\n"
        content += "============================================================\n\n"
        content += f"ДАТА:          {today}\n"
        content += f"СИСТЕМА:       {self.cb_system.get()}\n"
        content += f"КАТАЛОГ:       {catalog_info}\n"
        content += f"ЦВЕТ:          {color_info}\n"
        content += f"{self.current_display_base_name}{ratio_text}\n\n"
        content += f"ВЕС ОСНОВЫ:    {self.current_base_weight:.3f} кг\n"
        content += f"ВЕС ПИГМЕНТОВ: {self.current_pigments_weight_kg:.3f} кг\n"
        content += f"ОБЩИЙ ВЕС:     {self.current_total_weight:.3f} кг\n\n"
        content += f"{'КОД':<8} {'НАИМЕНОВАНИЕ ПИГМЕНТА':<40} {'ВЕС (гр)':<10}\n"
        content += f"{'-' * 65}\n"

        for c, d, q in self.current_formula:
            content += f"[{str(c):^6}]  {str(d)[:38]:<40}  >> {str(q):>8} <<\n"

        content += f"\n{'-' * 65}\n"
        content += f"Клиент: __________________________     \n\n"
        content += "                                       +-----------------------+\n"
        content += "                                       |                       |\n"
        content += "                                       |      ДЛЯ ВЫКРАСА      |\n"
        content += "                                       |        (5x5 см)       |\n"
        content += "                                       |                       |\n"
        content += "                                       +-----------------------+\n"

        fd, path = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        if sys.platform == "win32": os.startfile(path, "print")

if __name__ == "__main__":
    root = tk.Tk()
    app = TintingApp(root)
    root.mainloop()