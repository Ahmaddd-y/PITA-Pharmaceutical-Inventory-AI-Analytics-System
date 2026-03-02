import customtkinter as ctk
from tkinter import messagebox
import pandas as pd
import os
from datetime import datetime, timedelta
import threading
from abc import ABC, abstractmethod

# Import the Facade from ai.py
from ai import TrendAnalysisFacade

# ========== THEME CONFIGURATION ========== #
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Enterprise Color Palette
C_BG = "#1a1a1a"       # Main Background
C_SIDE = "#2b2b2b"     # Sidebar
C_CARD = "#333333"     # Card Background
C_ACCENT = "#1f6aa5"   # Primary Blue (Corporate)
C_DANGER = "#b00020"   # Red (Critical)
C_WARN = "#fbc02d"     # Yellow (Warning)
C_SUCCESS = "#388e3c"  # Green (Normal)
C_TEXT = "#ffffff"

INVENTORY_FILE = "inventory.csv"
TRANSACTION_FILE = "transactions.csv"
USERS_FILE = "users.csv"

# ========== ROLE DEFINITIONS ========== #

ROLES = {
    "Manager": ["View", "Restock", "Analysis"],
    "Pharmacist": ["View", "Sale", "Restock"],
    "Inventory Clerk": ["View", "Restock"],
    "Administrator": ["View", "Settings"]
}

# ========== STRATEGY PATTERN CLASSES ========== #

class TransactionStrategy(ABC):
    @abstractmethod
    def execute(self, df, idx, qty, data):
        pass

class SaleStrategy(TransactionStrategy):
    def execute(self, df, idx, qty, data):
        current_qty = df.at[idx, 'quantity']
        if current_qty >= qty:
            df.at[idx, 'quantity'] = current_qty - qty
            return True, "Sale recorded successfully."
        else:
            return False, "Insufficient Stock for this transaction."

class RestockStrategy(TransactionStrategy):
    def execute(self, df, idx, qty, data):
        current_qty = df.at[idx, 'quantity']
        df.at[idx, 'quantity'] = current_qty + qty
        if data.get('supplier'): df.at[idx, 'supplier'] = data['supplier']
        if data.get('expiry'): df.at[idx, 'expiry'] = data['expiry']
        return True, "Restock recorded successfully."

# ========== POPUP: USER MANAGEMENT (ADMIN ONLY) ========== #

class UserManagementDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("User Management Console")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()
        
        # Header
        ctk.CTkLabel(self, text="MANAGE SYSTEM USERS", font=("Roboto", 20, "bold"), text_color=C_ACCENT).pack(pady=20)

        # Input Area
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=10)
        
        self.name_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter Name (e.g., Ahmad)", width=200)
        self.name_entry.pack(side="left", padx=(0, 10))
        
        self.role_var = ctk.StringVar(value="Pharmacist")
        ctk.CTkComboBox(input_frame, values=list(ROLES.keys()), variable=self.role_var, width=150).pack(side="left", padx=10)
        
        ctk.CTkButton(input_frame, text="+ ADD USER", fg_color=C_SUCCESS, width=100, command=self.add_user).pack(side="left", padx=10)

        # User List
        self.user_list_frame = ctk.CTkScrollableFrame(self, fg_color=C_CARD)
        self.user_list_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.load_users()

    def load_users(self):
        # Clear list
        for widget in self.user_list_frame.winfo_children(): widget.destroy()
        
        # Headers
        header = ctk.CTkFrame(self.user_list_frame, fg_color="transparent")
        header.pack(fill="x", pady=5)
        ctk.CTkLabel(header, text="USERNAME", font=("Roboto", 12, "bold"), width=200, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(header, text="ASSIGNED ROLE", font=("Roboto", 12, "bold"), width=150, anchor="w").pack(side="left", padx=10)
        
        try:
            df = pd.read_csv(USERS_FILE)
            for idx, row in df.iterrows():
                self.create_user_row(row['username'], row['role'], idx)
        except Exception:
            pass

    def create_user_row(self, name, role, idx):
        row = ctk.CTkFrame(self.user_list_frame, fg_color=C_SIDE, corner_radius=5)
        row.pack(fill="x", pady=2)
        
        ctk.CTkLabel(row, text=name, font=("Roboto", 12), width=200, anchor="w").pack(side="left", padx=10)
        
        # Role Badge Color
        role_cols = {"Manager": "#e67e22", "Administrator": C_DANGER, "Pharmacist": C_ACCENT, "Inventory Clerk": C_SUCCESS}
        col = role_cols.get(role, "gray")
        
        badge = ctk.CTkLabel(row, text=role.upper(), font=("Roboto", 10, "bold"), text_color="white", fg_color=col, corner_radius=10)
        badge.pack(side="left", padx=10, pady=5)

        # Delete Button
        ctk.CTkButton(row, text="REMOVE", fg_color="transparent", text_color=C_DANGER, width=60, 
                      command=lambda i=idx: self.delete_user(i)).pack(side="right", padx=10)

    def add_user(self):
        name = self.name_entry.get().strip()
        role = self.role_var.get()
        
        if not name:
            messagebox.showerror("Error", "Username cannot be empty.")
            return

        df = pd.read_csv(USERS_FILE)
        new_row = {"username": name, "role": role, "created_at": datetime.now().strftime("%Y-%m-%d")}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(USERS_FILE, index=False)
        
        self.name_entry.delete(0, 'end')
        self.load_users()

    def delete_user(self, idx):
        if messagebox.askyesno("Confirm", "Are you sure you want to remove this user profile?"):
            df = pd.read_csv(USERS_FILE)
            df = df.drop(idx)
            df.to_csv(USERS_FILE, index=False)
            self.load_users()

# ========== POPUP: TRANSACTION ENTRY ========== #

class TransactionDialog(ctk.CTkToplevel):
    def __init__(self, parent, trans_type, existing_drugs):
        super().__init__(parent)
        self.trans_type = trans_type
        self.title(f"{trans_type} Entry")
        self.geometry("450x600" if trans_type == "Restock" else "450x350")
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()
        
        ctk.CTkLabel(self, text=f"RECORD {trans_type.upper()}", font=("Roboto", 20, "bold")).pack(pady=20)

        ctk.CTkLabel(self, text="Drug Name").pack(anchor="w", padx=30)
        self.drug_var = ctk.StringVar()
        self.drug_entry = ctk.CTkComboBox(self, variable=self.drug_var, values=existing_drugs, width=390, height=35)
        self.drug_entry.pack(padx=30, pady=(0, 15))

        ctk.CTkLabel(self, text="Quantity").pack(anchor="w", padx=30)
        self.qty_entry = ctk.CTkEntry(self, width=390, height=35)
        self.qty_entry.pack(padx=30, pady=(0, 15))

        if trans_type == "Restock":
            ctk.CTkLabel(self, text="Supplier (If New/Update)").pack(anchor="w", padx=30)
            self.supp_entry = ctk.CTkEntry(self, width=390, height=35)
            self.supp_entry.pack(padx=30, pady=(0, 15))

            ctk.CTkLabel(self, text="Expiry Date (YYYY-MM-DD)").pack(anchor="w", padx=30)
            self.exp_entry = ctk.CTkEntry(self, width=390, height=35, placeholder_text="2025-12-31")
            self.exp_entry.pack(padx=30, pady=(0, 15))

            ctk.CTkLabel(self, text="Reorder Level (Alert Threshold)").pack(anchor="w", padx=30)
            self.lvl_entry = ctk.CTkEntry(self, width=390, height=35)
            self.lvl_entry.pack(padx=30, pady=(0, 15))

        ctk.CTkButton(self, text="CONFIRM TRANSACTION", fg_color=C_ACCENT, height=45, width=390, 
                      font=("Roboto", 12, "bold"), command=self.submit).pack(pady=30)

    def submit(self):
        data = {
            "drug": self.drug_var.get().strip(),
            "qty": self.qty_entry.get().strip(),
            "supplier": self.supp_entry.get().strip() if self.trans_type == "Restock" else "",
            "expiry": self.exp_entry.get().strip() if self.trans_type == "Restock" else "",
            "reorder": self.lvl_entry.get().strip() if self.trans_type == "Restock" else ""
        }
        if not data["drug"] or not data["qty"]:
            messagebox.showerror("Validation Error", "Drug Name and Quantity are required fields.")
            return
        try:
            int(data["qty"])
            if data["reorder"]: int(data["reorder"])
        except ValueError:
            messagebox.showerror("Validation Error", "Numeric fields required.")
            return
        self.result = data
        self.destroy()

# ========== MAIN SYSTEM ========== #

class PITA_System(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PITA - Pharmaceutical Inventory Management System")
        self.geometry("1280x850")
        
        self.init_database()
        self.current_user_role = None
        self.show_login()

    def init_database(self):
        if not os.path.exists(INVENTORY_FILE):
            pd.DataFrame(columns=["id", "drug", "supplier", "expiry", "quantity", "reorder_level"]).to_csv(INVENTORY_FILE, index=False)
        if not os.path.exists(TRANSACTION_FILE):
            pd.DataFrame(columns=["timestamp", "type", "drug", "quantity", "user"]).to_csv(TRANSACTION_FILE, index=False)
        if not os.path.exists(USERS_FILE):
            # Seed initial dummy users for showcase
            df = pd.DataFrame(columns=["username", "role", "created_at"])
            df = pd.concat([df, pd.DataFrame([
                {"username": "Ahmad", "role": "Pharmacist", "created_at": "2025-01-10"},
                {"username": "Omar", "role": "Inventory Clerk", "created_at": "2025-01-11"}
            ])], ignore_index=True)
            df.to_csv(USERS_FILE, index=False)

    # ========== LOGIN ========== #
    def show_login(self):
        self.clear_window()
        bg_frame = ctk.CTkFrame(self, fg_color=C_BG)
        bg_frame.pack(fill="both", expand=True)

        card = ctk.CTkFrame(bg_frame, fg_color=C_CARD, corner_radius=5)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text="PITA SYSTEM", font=("Roboto", 36, "bold"), text_color=C_ACCENT).pack(pady=(40, 10), padx=80)
        ctk.CTkLabel(card, text="Pharmaceutical Intelligence & Tracking Analysis", font=("Roboto", 12)).pack(pady=(0, 30))
        
        self.role_var = ctk.StringVar(value="Manager")
        ctk.CTkComboBox(card, values=list(ROLES.keys()), variable=self.role_var, width=250, height=40).pack(pady=10)
        
        ctk.CTkButton(card, text="LOGIN", command=self.login, width=250, height=45, fg_color=C_ACCENT, font=("Roboto", 14, "bold")).pack(pady=30)

    def login(self):
        self.current_user_role = self.role_var.get()
        self.build_main_interface()
        self.check_alerts()

    # ========== MAIN UI ========== #
    def build_main_interface(self):
        self.clear_window()
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=C_SIDE)
        self.sidebar.pack(side="left", fill="y")
        
        ctk.CTkLabel(self.sidebar, text="PITA", font=("Roboto", 30, "bold"), text_color=C_ACCENT).pack(pady=(30, 5))
        ctk.CTkLabel(self.sidebar, text=f"ROLE: {self.current_user_role.upper()}", font=("Roboto", 12, "bold"), text_color="gray").pack(pady=(0, 20), padx=20, anchor="w")
        
        perms = ROLES[self.current_user_role]
        
        self.create_nav_btn("Dashboard", self.view_dashboard)
        if "View" in perms: self.create_nav_btn("Inventory Master", self.view_inventory)
        if "Sale" in perms: self.create_nav_btn("Record Sale", lambda: self.open_transaction("Sale"))
        if "Restock" in perms: self.create_nav_btn("Restock Items", lambda: self.open_transaction("Restock"))
        if "Analysis" in perms: self.create_nav_btn("AI Analysis", self.view_analysis)
        
        # === ADMIN SETTINGS LINK ===
        if "Settings" in perms: 
            self.create_nav_btn("User Settings", self.open_user_management)
        
        ctk.CTkButton(self.sidebar, text="LOGOUT", fg_color="transparent", border_width=1, border_color="#555", 
                      command=self.show_login).pack(side="bottom", pady=30, padx=20, fill="x")

        # Main Area
        self.main_area = ctk.CTkFrame(self, fg_color=C_BG)
        self.main_area.pack(side="right", fill="both", expand=True)
        self.view_dashboard()

    def create_nav_btn(self, text, command):
        btn = ctk.CTkButton(self.sidebar, text=text, anchor="w", fg_color="transparent", hover_color=C_CARD, height=50, command=command, font=("Roboto", 14))
        btn.pack(fill="x", padx=10, pady=2)

    def open_user_management(self):
        UserManagementDialog(self)

    # ========== DASHBOARD ========== #
    def view_dashboard(self):
        self.clear_frame(self.main_area)
        self.set_header("Dashboard Overview")
        
        try:
            df = pd.read_csv(INVENTORY_FILE)
            trans_df = pd.read_csv(TRANSACTION_FILE)
        except:
            df = pd.DataFrame(columns=["quantity"])
            trans_df = pd.DataFrame(columns=["type", "timestamp"])

        total_items = len(df)
        total_stock = df['quantity'].sum() if not df.empty else 0
        low_stock_count = len(df[df['quantity'] <= df['reorder_level']]) if not df.empty else 0
        today_str = datetime.now().strftime("%Y-%m-%d")
        sales_today = len(trans_df[(trans_df['type'] == 'Sale') & (trans_df['timestamp'].str.contains(today_str))]) if not trans_df.empty else 0

        grid = ctk.CTkFrame(self.main_area, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=10)
        self.create_kpi_card(grid, "Total SKUs", str(total_items), 0, C_ACCENT)
        self.create_kpi_card(grid, "Total Units", str(total_stock), 1, C_SUCCESS)
        self.create_kpi_card(grid, "Low Stock Alerts", str(low_stock_count), 2, C_DANGER if low_stock_count > 0 else "#7f8c8d")
        self.create_kpi_card(grid, "Transactions Today", str(sales_today), 3, "#8e44ad")

        ctk.CTkLabel(self.main_area, text="System Actions", font=("Roboto", 16, "bold")).pack(anchor="w", padx=20, pady=(30, 10))
        action_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        action_frame.pack(fill="x", padx=20)
        
        if "Analysis" in ROLES[self.current_user_role]:
            ctk.CTkButton(action_frame, text="Generate Business Report (AI)", fg_color="#e67e22", height=50, font=("Roboto", 14, "bold"), command=self.view_analysis).pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkButton(action_frame, text="View Critical Alerts", fg_color=C_DANGER, height=50, font=("Roboto", 14, "bold"), command=self.check_alerts).pack(side="left", fill="x", expand=True, padx=(10, 0))

    def create_kpi_card(self, parent, title, value, col, color):
        card = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=5)
        card.grid(row=0, column=col, padx=10, pady=10, sticky="ew")
        parent.grid_columnconfigure(col, weight=1)
        ctk.CTkLabel(card, text=title.upper(), font=("Roboto", 11, "bold"), text_color="#aaaaaa").pack(pady=(20, 0))
        ctk.CTkLabel(card, text=value, font=("Roboto", 36, "bold"), text_color=color).pack(pady=(5, 20))

    # ========== INVENTORY VIEW ========== #
    def view_inventory(self):
        self.clear_frame(self.main_area)
        self.set_header("Inventory Master")
        try:
            df = pd.read_csv(INVENTORY_FILE)
        except:
            df = pd.DataFrame()
        
        table_frame = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        header_frame = ctk.CTkFrame(table_frame, fg_color=C_CARD, height=45)
        header_frame.pack(fill="x", pady=(0, 5))
        widths = [200, 150, 120, 80, 100, 150]
        headers = ["Drug Name", "Supplier", "Expiry", "Qty", "Reorder Level", "Status"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(header_frame, text=h.upper(), font=("Roboto", 12, "bold"), width=widths[i], anchor="w").pack(side="left", padx=5)

        if not df.empty:
            for index, row in df.iterrows():
                row_frame = ctk.CTkFrame(table_frame, fg_color=C_SIDE if index % 2 == 0 else C_BG, corner_radius=0)
                row_frame.pack(fill="x", pady=1)
                qty = float(row['quantity'])
                reorder = float(row['reorder_level'])
                status_text = "OK"
                status_col = C_SUCCESS
                if qty <= reorder:
                    status_text = "LOW STOCK"
                    status_col = C_DANGER
                vals = [row['drug'], row['supplier'], row['expiry'], str(row['quantity']), str(row['reorder_level']), status_text]
                for i, v in enumerate(vals):
                    txt_col = status_col if i == 5 else "#dddddd"
                    font = ("Roboto", 12, "bold") if i == 5 else ("Roboto", 12)
                    ctk.CTkLabel(row_frame, text=v, width=widths[i], anchor="w", text_color=txt_col, font=font).pack(side="left", padx=5)

    # ========== TRANSACTIONS ========== #
    def open_transaction(self, trans_type):
        df = pd.read_csv(INVENTORY_FILE)
        existing_drugs = df['drug'].tolist() if not df.empty else []
        dialog = TransactionDialog(self, trans_type, existing_drugs)
        self.wait_window(dialog)
        if dialog.result:
            self.process_transaction(trans_type, dialog.result)

    def process_transaction(self, trans_type, data):
        df = pd.read_csv(INVENTORY_FILE)
        drug_name = data['drug']
        qty = int(data['qty'])
        mask = df['drug'].str.lower() == drug_name.lower()
        
        if not df[mask].empty:
            idx = df[mask].index[0]
            strategies = {"Sale": SaleStrategy(), "Restock": RestockStrategy()}
            strategy = strategies.get(trans_type)
            if strategy:
                success, message = strategy.execute(df, idx, qty, data)
                if success:
                    df.to_csv(INVENTORY_FILE, index=False)
                    self.log_history(trans_type, drug_name, qty)
                    messagebox.showinfo("Success", message)
                else:
                    messagebox.showerror("Error", message)
                    return
        else:
            if trans_type == "Restock":
                if self.current_user_role == "Manager":
                    if not data['supplier'] or not data['expiry'] or not data['reorder']:
                        messagebox.showwarning("Incomplete Data", "Full details required for new items.")
                        return
                    new_row = {"id": len(df)+1, "drug": drug_name, "supplier": data['supplier'], "expiry": data['expiry'], "quantity": qty, "reorder_level": int(data['reorder'])}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(INVENTORY_FILE, index=False)
                    self.log_history("Restock (New)", drug_name, qty)
                    messagebox.showinfo("New Item", f"'{drug_name}' added to Master Inventory.")
                else:
                    messagebox.showerror("Access Denied", "Only Managers can add NEW items.")
            else:
                messagebox.showerror("Error", "Item not found.")
        self.check_alerts()
        self.view_dashboard()

    def log_history(self, trans_type, drug, qty):
        log_df = pd.read_csv(TRANSACTION_FILE)
        new_row = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": trans_type, "drug": drug, "quantity": qty, "user": self.current_user_role}
        log_df = pd.concat([log_df, pd.DataFrame([new_row])], ignore_index=True)
        log_df.to_csv(TRANSACTION_FILE, index=False)

    # ========== AI ========== #
    def view_analysis(self):
        self.clear_frame(self.main_area)
        self.set_header("AI Business Intelligence")
        textbox = ctk.CTkTextbox(self.main_area, font=("Consolas", 14), fg_color=C_CARD)
        textbox.pack(fill="both", expand=True, padx=20, pady=20)
        textbox.insert("0.0", "Consulting AI model... please wait...")
        
        def run_ai():
            try:
                trans_df = pd.read_csv(TRANSACTION_FILE)
                inv_df = pd.read_csv(INVENTORY_FILE)
                ai_facade = TrendAnalysisFacade(model_type="cloud")
                result = ai_facade.get_prediction(trans_df, inv_df)
                textbox.delete("0.0", "end")
                textbox.insert("0.0", result)
            except Exception as e:
                textbox.insert("end", f"\nError: {e}")
        threading.Thread(target=run_ai).start()

    # ========== HELPERS ========== #
    def set_header(self, text):
        ctk.CTkLabel(self.main_area, text=text.upper(), font=("Roboto", 24, "bold"), text_color=C_TEXT).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkFrame(self.main_area, height=2, fg_color=C_ACCENT).pack(fill="x", padx=20, pady=(0, 20))

    def check_alerts(self):
        df = pd.read_csv(INVENTORY_FILE)
        if df.empty: return
        alerts = []
        low_stock = df[df['quantity'] <= df['reorder_level']]
        for _, row in low_stock.iterrows():
            alerts.append(f"[CRITICAL] LOW STOCK: {row['drug']} (Qty: {row['quantity']})")
        if alerts: messagebox.showwarning("System Notifications", "\n".join(alerts))

    def clear_window(self):
        for widget in self.winfo_children(): widget.destroy()

    def clear_frame(self, frame):
        for widget in frame.winfo_children(): widget.destroy()

if __name__ == "__main__":
    app = PITA_System()
    app.mainloop()