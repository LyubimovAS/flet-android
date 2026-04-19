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
    if not os.path.exists(JSON_FILE) and "GCP_SERVICE_ACCOUNT_KEY" in os.environ:
        try:
            with open(JSON_FILE, "w") as f:
                f.write(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
        except: pass
    if not os.path.exists(JSON_FILE): return None
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, SCOPE)
        return gspread.authorize(creds)
    except: return None

def main(page: ft.Page):
    page.title = "MOM: Улік завдань"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 450
    page.window_height = 800
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    client = get_client()
    spreadsheet = None
    if client:
        try: spreadsheet = client.open(SHEET_NAME)
        except: pass

    state = {"worksheet": None, "data": []}

    def save_changes(row_idx, status, money, materials, closed_1c):
        row_num = row_idx + 2
        try:
            state["worksheet"].update_cell(row_num, 4, status)
            state["worksheet"].update_cell(row_num, 5, str(money).replace('.', ','))
            state["worksheet"].update_cell(row_num, 6, materials)
            state["worksheet"].update_cell(row_num, 7, "так" if closed_1c else "ні")
            show_stores(state["worksheet"].title)
        except: pass

    # --- ЭКРАН РЕДАКТИРОВАНИЯ ЗАДАНИЯ ---
    def show_task_edit(task_idx, task, sheet_title):
        page.clean()
        page.add(
            ft.Text(f"Магазин №{task.get('№')}", size=20, weight="bold"),
            ft.Divider(),
            status_dd := ft.Dropdown(label="Статус", value=str(task.get('Статус виконання', 'в процесі')),
                options=[ft.dropdown.Option("виконано"), ft.dropdown.Option("в процесі"), ft.dropdown.Option("не виконано")]),
            money_tf := ft.TextField(label="Витрати", value=str(task.get('Витрати', '0'))),
            mat_tf := ft.TextField(label="Матеріали", value=str(task.get('Матеріали', '')), multiline=True),
            one_c_sw := ft.Switch(label="Закриття в 1С", value=(str(task.get('Закриття в 1С')) == "так")),
            ft.ElevatedButton("Зберегти зміни", 
                              on_click=lambda _: save_changes(task_idx, status_dd.value, money_tf.value, mat_tf.value, one_c_sw.value),
                              width=300, height=50, bgcolor="blue50"),
            ft.OutlinedButton("Повернутися до завдань", 
                              on_click=lambda _: show_stores(sheet_title), 
                              width=300, height=50)
        )
        page.update()

    # --- ЭКРАН СПИСКА МАГАЗИНОВ И ЗАДАНИЙ ---
    def show_stores(sheet_title):
        page.clean()
        try:
            state["worksheet"] = spreadsheet.worksheet(sheet_title)
            state["data"] = state["worksheet"].get_all_records()
            stores = sorted(list(set(str(d['№']) for d in state["data"] if d.get('№'))))
            
            page.add(
                ft.Text(sheet_title, size=22, weight="bold"),
                ft.ElevatedButton("Повернутися до вибору дати", 
                                  on_click=lambda _: show_sheets_list(), 
                                  width=300, height=45),
                ft.Divider()
            )
            
            for s_id in stores:
                page.add(ft.Container(content=ft.Text(f"Магазин №{s_id}", weight="bold"), bgcolor="blue100", padding=10, border_radius=5))
                for i, t in [(i, d) for i, d in enumerate(state["data"]) if str(d['№']) == s_id]:
                    raw_s = str(t.get('Статус виконання', '')).strip().lower()
                    clr = "green100" if raw_s == "виконано" else "yellow100" if raw_s == "в процесі" else "red100"
                    page.add(ft.Container(
                        content=ft.ListTile(title=ft.Text(str(t.get('Опис робіт', 'Без опису')), size=14),
                            subtitle=ft.Text(f"Статус: {raw_s}"),
                            on_click=lambda e, idx=i, item=t: show_task_edit(idx, item, sheet_title)),
                        bgcolor=clr, border_radius=10, margin=ft.margin.only(bottom=5)))
        except: page.add(ft.Text("Помилка завантаження"))
        page.update()

    # --- ГЛАВНЫЙ ЭКРАН (ВЫБОР ДАТЫ) ---
    def show_sheets_list():
        page.clean()
        page.add(ft.Text("Звіти та Кошторис", size=24, weight="bold", text_align="center"), ft.Divider(height=20))
        if not spreadsheet:
            page.add(ft.Text("Помилка підключення!", color="red")); page.update(); return

        try:
            all_sheets = spreadsheet.worksheets()
            all_sheets.reverse()
            for ws in all_sheets:
                data = ws.get_all_records()
                
                # Считаем витрати
                total_spent = 0
                for row in data:
                    try:
                        v = str(row.get('Витрати', '0')).replace(',', '.')
                        total_spent += float(v) if v else 0
                    except: pass
                
                # Читаем бюджет из H2
                try:
                    budget_val = ws.cell(2, 8).value
                    budget = float(str(budget_val).replace(',', '.')) if budget_val else 0
                except: budget = 0

                # Считаем залишок и пишем в I2
                remainder = budget - total_spent
                try:
                    ws.update_cell(2, 9, str(remainder).replace('.', ','))
                except: pass
                
                rem_color = "green" if remainder >= 0 else "red"

                page.add(
                    ft.Container(
                        width=380,
                        padding=15,
                        bgcolor="white",
                        border=ft.border.all(1, "blue200"),
                        border_radius=12,
                        on_click=lambda e, t=ws.title: show_stores(t),
                        content=ft.Column([
                            ft.Text(ws.title, size=18, weight="bold"),
                            ft.Row([
                                ft.Text(f"Витрати: {total_spent:.2f}", size=14, color="grey700"),
                                ft.Text(f"Залишок: {remainder:.2f}", size=14, weight="bold", color=rem_color)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ])
                    )
                )
        except Exception as e:
            page.add(ft.Text(f"Помилка: {e}"))
        page.update()

    show_sheets_list()

if __name__ == "__main__":
    ft.app(target=main)