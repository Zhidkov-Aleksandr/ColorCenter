import pyodbc
import json
import socket

def get_connection():
    computer_name = socket.gethostname()
    drivers = [
        '{ODBC Driver 17 for SQL Server}',
        '{ODBC Driver 13 for SQL Server}',
        '{SQL Server Native Client 11.0}',
        '{SQL Server}'
    ]
    server_variants = [
        r'.\SQLEXPRESS',
        rf'{computer_name}\SQLEXPRESS',
        r'localhost\SQLEXPRESS',
        r'(local)\SQLEXPRESS'
    ]
    
    for driver in drivers:
        for server in server_variants:
            try:
                conn_str = (
                    f'DRIVER={driver};'
                    f'SERVER={server};'
                    f'DATABASE=YDatacolorLab;'
                    'Trusted_Connection=yes;'
                    'Timeout=2;'
                )
                return pyodbc.connect(conn_str)
            except pyodbc.Error:
                continue
    raise Exception("Не удалось подключиться к SQL Server.")

# Универсальный конвертер для обхода ошибки "Object is not JSON serializable"
def json_safe_converter(obj):
    return str(obj)

def dump_db_structure():
    try:
        conn = get_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return

    print("Подключено! Собираем структуру базы данных...")
    
    # Получаем список всех таблиц в схеме YMITYADM
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'YMITYADM'")
    tables = [row[0] for row in cursor.fetchall()]
    
    db_dump = {}
    
    for table in tables:
        try:
            # Берем структуру и 5 примеров строк
            cursor.execute(f"SELECT TOP 5 * FROM YMITYADM.[{table}]")
            columns = [col[0] for col in cursor.description]
            
            rows = []
            for row in cursor.fetchall():
                # Собираем строку в словарь вида {"ИМЯ_КОЛОНКИ": "ЗНАЧЕНИЕ"}
                row_dict = dict(zip(columns, row))
                rows.append(row_dict)
                
            db_dump[table] = {
                "columns": columns,
                "sample_data": rows
            }
            print(f"Успешно прочитана таблица: {table}")
        except Exception as e:
            print(f"Пропущена таблица {table}: {e}")

    # Сохраняем в JSON
    with open('db_structure.json', 'w', encoding='utf-8') as f:
        json.dump(db_dump, f, ensure_ascii=False, indent=2, default=json_safe_converter)
        
    print("\nГОТОВО! Файл db_structure.json успешно создан.")

if __name__ == "__main__":
    dump_db_structure()