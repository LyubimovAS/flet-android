import flet as ft
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# --- НАСТРОЙКИ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "credentials.json")
SHEET_NAME = "Prog_zvit" 
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_client():
    if not os.path.exists(JSON_FILE):
        return None
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, SCOPE)
        return gspread.authorize(creds)
    except:
        return None

def main(page: ft.Page):
    page.title = "MOM: Улік завдань"
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # Подключение
    client = get_client()
    spreadsheet = None
    if client:
        try:
            spreadsheet = client.open(SHEET_NAME)
        except:
            pass

    state = {"worksheet": None, "data": []}

    def save_changes(row_idx, status, money, materials, closed_1c):
        row_num = row_idx + 2
        try:
            state["worksheet"].update_cell(row_num, 4, status)
            state["worksheet"].update_cell(row_num, 5, money)
            state["worksheet"].update_cell(row_num, 6, materials)
            state["worksheet"].update_cell(row_num, 7, "так" if closed_1c else "ні")
            
            page.snack_bar = ft.SnackBar(ft.Text("Збережено!"))
            page.snack_bar.open = True
            show_stores(state["worksheet"].title)
        except Exception as e:
            print(f"Помилка збереження: {e}")

    def show_task_edit(task_idx, task, sheet_title):
        page.clean()
        
        status_dd = ft.Dropdown(
            label="Статус виконання",
            value=str(task.get('Статус виконання', 'в процесі')),
            options=[
                ft.dropdown.Option("виконано"), 
                ft.dropdown.Option("в процесі"), 
                ft.dropdown.Option("не фарбуємо")
            ]
        )
        money_tf = ft.TextField(label="Витрати", value=str(task.get('Витрати', '0')))
        mat_tf = ft.TextField(label="Матеріали", value=str(task.get('Матеріали', '')), multiline=True)
        one_c_sw = ft.Switch(label="Закриття в 1С", value=(str(task.get('Закриття в 1С')) == "так"))

        page.add(
            ft.Text(f"Магазин №{task.get('№')}", size=20, weight="bold"),
            ft.Text(f"Завдання: {task.get('Опис робіт', '-')}", size=16),
            status_dd, money_tf, mat_tf, one_c_sw,
            ft.ElevatedButton("Зберегти", on_click=lambda _: save_changes(
                task_idx, status_dd.value, money_tf.value, mat_tf.value, one_c_sw.value
            )),
            ft.TextButton("Назад", on_click=lambda _: show_stores(sheet_title))
        )
        page.update()

    def show_stores(sheet_title):
        page.clean()
        page.add(ft.ProgressBar(), ft.Text("Завантаження..."))
        page.update()

        try:
            state["worksheet"] = spreadsheet.worksheet(sheet_title)
            state["data"] = state["worksheet"].get_all_records()
            stores = sorted(list(set(str(d['№']) for d in state["data"] if d.get('№'))))
            
            page.clean()
            page.add(ft.Text(f"Лист: {sheet_title}", size=22, weight="bold"))
            
            for s_id in stores:
                store_tasks = [(i, d) for i, d in enumerate(state["data"]) if str(d['№']) == s_id]
                page.add(ft.Container(content=ft.Text(f"Магазин №{s_id}", weight="bold"), bgcolor="blue100", padding=10, border_radius=5))
                for i, t in store_tasks:
                    page.add(ft.ListTile(
                        title=ft.Text(str(t.get('Опис робіт', 'Без опису'))),
                        subtitle=ft.Text(f"Статус: {t.get('Статус виконання', '-')}"),
                        on_click=lambda e, idx=i, item=t: show_task_edit(idx, item, sheet_title)
                    ))
        except Exception as e:
            page.add(ft.Text(f"Помилка: {e}"))

        page.add(ft.Divider(), ft.ElevatedButton("До списку дат", on_click=lambda _: show_sheets_list()))
        page.update()

    def show_sheets_list():
        page.clean()
        if not spreadsheet:
            page.add(ft.Text("Не вдалося підключитися. Додайте пошту з JSON в доступ таблиці!", color="red", size=16))
            page.update()
            return

        try:
            all_sheets = spreadsheet.worksheets()
            page.add(ft.Text("Оберіть дату:", size=24, weight="bold"))
            for ws in all_sheets:
                page.add(ft.ListTile(
                    title=ft.Text(ws.title),
                    on_click=lambda e, title=ws.title: show_stores(title)
                ))
        except Exception as e:
            page.add(ft.Text(f"Помилка списку: {e}"))
        page.update()

    show_sheets_list()

if __name__ == "__main__":
    ft.app(target=main)