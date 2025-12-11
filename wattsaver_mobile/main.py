import flet as ft
import json
import os
import requests
from bill_parser import BillParser

# REPLACE WITH YOUR REPO URL
GITHUB_DATA_URL = "https://raw.githubusercontent.com/papajimm/wattsaver-mobile/main/wattsaver_mobile/assets/providers.json"

def main(page: ft.Page):
    page.title = "WattSaver Mobile"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10
    page.scroll = ft.ScrollMode.ADAPTIVE

    # --- STATE ---
    # Residential
    providers_res = []
    gas_providers_res = []
    
    # Business
    providers_bus = []
    gas_providers_bus = []

    reg_charges = {}
    gas_reg_charges = {}
    
    current_elec_kwh = 0
    current_gas_kwh = 0
    current_days = 30
    detected_provider = "Unknown"
    
    # Mode: "residential" or "business"
    current_mode = "residential"

    parser = BillParser()

    # --- LOAD DATA ---
    def load_data(from_json_string=None):
        nonlocal providers_res, gas_providers_res, providers_bus, gas_providers_bus, reg_charges, gas_reg_charges
        try:
            data = None
            if from_json_string:
                data = json.loads(from_json_string)
            else:
                # Load Local
                path = "assets/providers.json" 
                if not os.path.exists(path):
                    path = "wattsaver_mobile/assets/providers.json"
                
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
            
            if data:
                # Residential
                providers_res = data.get("providers", [])
                gas_providers_res = data.get("gas_providers", [])
                
                # Business
                providers_bus = data.get("providers_business", [])
                gas_providers_bus = data.get("gas_providers_business", [])
                
                reg_charges = data.get("regulated_charges", {})
                gas_reg_charges = reg_charges.get("gas_reg_charges", {})
                return True
        except Exception as e:
            print(f"Data load error: {e}")
            return False
        return False

    load_data()

    # --- CLOUD SYNC ---
    def fetch_online_data(e):
        btn_refresh.text = "Syncing..."
        btn_refresh.disabled = True
        page.update()
        
        try:
            r = requests.get(GITHUB_DATA_URL)
            if r.status_code == 200:
                success = load_data(r.text)
                if success:
                    page.snack_bar = ft.SnackBar(ft.Text("Data Updated from Cloud!"))
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("Failed to parse Cloud Data."))
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"Cloud Error: {r.status_code}"))
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Connection Error: {ex}"))
        
        page.snack_bar.open = True
        btn_refresh.text = "Cloud Sync ☁"
        btn_refresh.disabled = False
        
        # Refresh UI
        refresh_current_view()
        page.update()

    # --- LOGIC HELPERS ---
    def calculate_regulated_charges_elec(kwh, days):
        # NOTE: Business regulated charges are different from Residential!
        # For this MVP, we are using the RESIDENTIAL formula for both, 
        # or we return 0 if business logic is unknown/complex.
        # Let's keep using the same formula for now but be aware it's an approximation for Business.
        if not reg_charges: return 0
        kva = 8
        admie = (reg_charges.get("admie_monopasiko", 0.00999) * kwh) + 0.5
        deddie = (reg_charges.get("deddie_monopasiko_energy", 0.00339) * kwh) + \
                 (reg_charges.get("deddie_monopasiko_power", 6.21) * kva * (days/365))
        etmear = reg_charges.get("etmear", 0.017) * kwh
        
        yko = 0
        remaining_kwh = kwh
        period_factor = days / 120
        tiers = reg_charges.get("yko_tiers", [])
        if not tiers: 
            tiers = [{"limit": 1600, "rate": 0.0069},{"limit": 2000, "rate": 0.050},{"limit": 99999, "rate": 0.085}]
        
        for tier in tiers:
            limit = tier["limit"] * period_factor
            rate = tier["rate"]
            if remaining_kwh <= 0: break
            chunk = min(remaining_kwh, limit)
            yko += chunk * rate
            remaining_kwh -= chunk
            
        return admie + deddie + etmear + yko

    def calculate_regulated_charges_gas(kwh, days):
        if not gas_reg_charges: return 0
        fixed = gas_reg_charges.get("fixed_network_charge_per_month", 0.85) * (days / 30)
        variable = gas_reg_charges.get("variable_network_charge_per_kwh", 0.003) * kwh
        etd = gas_reg_charges.get("etd_per_kwh", 0.002) * kwh
        eph = gas_reg_charges.get("eph_per_kwh", 0.005) * kwh
        return fixed + variable + etd + eph

    # --- UI COMPONENTS ---
    
    # 1. Slider Sections
    lbl_elec_val = ft.Text("0 kWh", weight=ft.FontWeight.BOLD, size=16)
    lbl_gas_val = ft.Text("0 kWh", weight=ft.FontWeight.BOLD, size=16)

    def on_elec_slider_change(e):
        val = int(e.control.value)
        lbl_elec_val.value = f"{val} kWh"
        nonlocal current_elec_kwh
        current_elec_kwh = val
        update_table("electricity")
        page.update()

    def on_gas_slider_change(e):
        val = int(e.control.value)
        lbl_gas_val.value = f"{val} kWh"
        nonlocal current_gas_kwh
        current_gas_kwh = val
        update_table("gas")
        page.update()

    slider_elec = ft.Slider(min=0, max=2000, divisions=200, label="{value}", on_change=on_elec_slider_change)
    slider_gas = ft.Slider(min=0, max=2000, divisions=200, label="{value}", on_change=on_gas_slider_change)

    # 2. Results List
    results_col_elec = ft.Column(scroll=ft.ScrollMode.ADAPTIVE)
    results_col_gas = ft.Column(scroll=ft.ScrollMode.ADAPTIVE)

    def create_card(res, is_detected=False):
        p = res["data"]
        card_color = "#444746"
        border = None
        if is_detected:
            card_color = "#0D47A1"
            border = ft.border.all(2, "#90CAF9")

        return ft.Container(
            padding=10,
            border_radius=10,
            bgcolor=card_color,
            border=border,
            content=ft.Column([
                ft.Row([
                    ft.Text(p["name"], weight=ft.FontWeight.BOLD, size=16, color="white" if is_detected else None),
                    ft.Container(
                        content=ft.Text(f"{res['total']:.2f} €", weight=ft.FontWeight.BOLD, size=18, color="#66BB6A"),
                        alignment=ft.alignment.center_right,
                        expand=True
                    )
                ]),
                ft.Text(f"{p['program']} | {res['price_disp']} /kWh", size=12, italic=True),
                ft.Divider(height=5, color="transparent"),
                ft.Row([
                    ft.Text(f"Energy: {res['energy_cost']:.2f}€", size=12),
                    ft.Text(f"Regulated: {res['reg_cost']:.2f}€", size=12),
                    ft.Text(f"Fixed: {res['fixed_disp']}", size=12),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ])
        )

    def get_current_providers(energy_type):
        if current_mode == "residential":
            if energy_type == "electricity": return providers_res
            else: return gas_providers_res
        else: # Business
            if energy_type == "electricity": return providers_bus
            else: return gas_providers_bus

    def update_table(energy_type):
        target_col = results_col_elec if energy_type == "electricity" else results_col_gas
        target_col.controls.clear()
        
        kwh = current_elec_kwh if energy_type == "electricity" else current_gas_kwh
        vat_rate = reg_charges.get("vat", 0.06)
        
        reg_cost = 0
        if energy_type == "electricity":
            reg_cost = calculate_regulated_charges_elec(kwh, current_days)
        else:
            reg_cost = calculate_regulated_charges_gas(kwh, current_days)
            vat_rate = gas_reg_charges.get("vat", 0.06)

        results = []
        
        # Get correct list based on mode
        current_providers = get_current_providers(energy_type)
        
        for p in current_providers:
            final_price = p["price_kwh"] * (1 - p.get("discount_percent", 0))
            energy_val = kwh * final_price
            fixed_val = (p["monthly_fee"] / 30) * current_days
            cost_energy_total = energy_val + fixed_val
            total_pre_vat = cost_energy_total + reg_cost
            vat_val = total_pre_vat * vat_rate
            total_final = total_pre_vat + vat_val
            
            is_det = (detected_provider.lower() in p["name"].lower())

            results.append({
                "data": p,
                "price_disp": f"{final_price:.3f}€",
                "fixed_disp": f"{fixed_val:.1f}€",
                "energy_cost": cost_energy_total,
                "reg_cost": reg_cost,
                "vat": vat_val,
                "total": total_final,
                "is_detected": is_det
            })
            
        results.sort(key=lambda x: (not x["is_detected"], x["total"]))
        
        for res in results:
            target_col.controls.append(create_card(res, res["is_detected"]))
            
        if not results:
             target_col.controls.append(ft.Text(f"No {current_mode} providers found.", italic=True))
        
        target_col.update()

    def refresh_current_view():
        update_table("electricity")
        update_table("gas")

    # 3. Mode Switch & File Picker
    def on_mode_change(e):
        nonlocal current_mode
        current_mode = "business" if e.control.value else "residential"
        lbl_mode.value = "Business Mode" if current_mode == "business" else "Residential Mode"
        refresh_current_view()
        page.update()

    switch_mode = ft.Switch(label="", value=False, on_change=on_mode_change)
    lbl_mode = ft.Text("Residential Mode", weight=ft.FontWeight.BOLD)

    def on_dialog_result(e: ft.FilePickerResultEvent):
        if e.files:
            file_path = e.files[0].path
            if file_path:
                res = parser.parse_bill(file_path)
                if "error" in res:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Error: {res['error']}"))
                    page.snack_bar.open = True
                    page.update()
                    return

                nonlocal current_days, detected_provider, current_elec_kwh, current_gas_kwh
                current_days = res.get("days", 30)
                detected_provider = res.get("provider_detected", "Unknown")
                bill_type = res.get("bill_type", "electricity")
                consumption = res.get("total_kwh", 0)

                if bill_type == "gas":
                    current_gas_kwh = consumption
                    slider_gas.value = consumption
                    lbl_gas_val.value = f"{consumption} kWh"
                    tabs.selected_index = 1
                else:
                    current_elec_kwh = consumption
                    slider_elec.value = consumption
                    lbl_elec_val.value = f"{consumption} kWh"
                    tabs.selected_index = 0
                
                status_text.value = f"Detected: {detected_provider} ({bill_type}) | {consumption} kWh"
                refresh_current_view()
                page.update()

    file_picker = ft.FilePicker(on_result=on_dialog_result)
    page.overlay.append(file_picker)

    # --- LAYOUT ASSEMBLY ---
    
    status_text = ft.Text("Waiting for input...", italic=True, color="#BDBDBD")

    # Add Refresh Button
    btn_refresh = ft.ElevatedButton("Cloud Sync ☁", on_click=fetch_online_data, bgcolor="#d35400", color="white")

    tab_elec = ft.Container(
        content=ft.Column([
            ft.Text("Electricity Consumption", size=14),
            ft.Row([slider_elec, lbl_elec_val], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            results_col_elec
        ]),
        padding=10
    )

    tab_gas = ft.Container(
        content=ft.Column([
            ft.Text("Gas Consumption", size=14),
            ft.Row([slider_gas, lbl_gas_val], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            results_col_gas
        ]),
        padding=10
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="Electricity ⚡", content=tab_elec),
            ft.Tab(text="Gas 🔥", content=tab_gas),
        ],
        expand=1,
    )

    header = ft.Container(
        padding=10,
        bgcolor="#444746",
        border_radius=10,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.BOLT, color="yellow"),
                ft.Text("WattSaver Ultimate", size=20, weight=ft.FontWeight.BOLD),
            ]),
            status_text,
            ft.Divider(),
            ft.Row([ft.Row([switch_mode, lbl_mode]),
                btn_refresh
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            ft.ElevatedButton("Import PDF Bill", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: file_picker.pick_files(allow_multiple=False, allowed_extensions=["pdf"])),
            ft.Text("Note: Live scraping is disabled on mobile.", size=10, color="#BDBDBD", text_align=ft.TextAlign.CENTER)
        ])
    )

    page.add(header, tabs)
    
    # Init
    refresh_current_view()

if __name__ == "__main__":
    ft.app(target=main)
