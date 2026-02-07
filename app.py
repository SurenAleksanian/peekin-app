import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta

# --- 1. CONFIG (Must be the very first command) ---
st.set_page_config(page_title="PeekIn", layout="wide")

DB_FILE = "finance.db"

# --- DATABASE INIT ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            amount INTEGER,
            day_of_month INTEGER,
            is_active INTEGER
        )
    ''')
    c.execute('SELECT count(*) FROM expenses')
    if c.fetchone()[0] == 0:
        demo = [
            ('Rent / Mortgage', 1200, 5, 1),
            ('Car Loan', 400, 20, 1),
            ('Netflix & Subs', 15, 1, 1),
            ('Groceries & Food', 600, 0, 1)
        ]
        c.executemany('INSERT INTO expenses (name, amount, day_of_month, is_active) VALUES (?, ?, ?, ?)', demo)
        conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql('SELECT * FROM expenses', conn)
    conn.close()
    df["is_active"] = df["is_active"].astype(bool)
    return df

def save_data(edited_df):
    conn = sqlite3.connect(DB_FILE)
    if "id" in edited_df.columns:
        save_df = edited_df.drop(columns=["id"])
    else:
        save_df = edited_df.copy()
    
    save_df["is_active"] = save_df["is_active"].fillna(True).astype(int)
    save_df["amount"] = save_df["amount"].fillna(0).astype(int)
    save_df["day_of_month"] = save_df["day_of_month"].fillna(0).astype(int)
    save_df["name"] = save_df["name"].fillna("New Item").astype(str)

    save_df.to_sql('expenses', conn, if_exists='replace', index=False)
    conn.close()

# --- APP START ---
init_db()

# === ИЗМЕНЕНИЯ В ЗАГОЛОВКЕ ===
st.title("💸 PeekIn")
st.caption("Future Finance Control") 
# =============================

# --- DASHBOARD METRICS ---
col_m1, col_m2, col_m3 = st.columns(3)

# Main Layout
col1, col2 = st.columns([4, 6])

with col1:
    with st.expander("⚙️ Wallet & Income", expanded=True):
        start_bal = st.number_input("Current Balance (€)", 0, 100000, 2000, step=100)
        sal_date = st.number_input("Salary Date (Day of month)", 1, 31, 1)
        sal_amt = st.number_input("Salary Amount (€)", 0, 50000, 3500, step=100)

    st.subheader("Monthly Expenses")
    df_sql = load_data()
    
    edited_df = st.data_editor(
        df_sql,
        num_rows="dynamic",
        key="editor",
        hide_index=True, 
        column_config={
            "id": None,
            "name": st.column_config.TextColumn("Expense Name", required=True),
            "amount": st.column_config.NumberColumn("Amount (€)", format="%d €", default=0),
            "day_of_month": st.column_config.NumberColumn(
                "Day (1-31)", 
                help="Set 0 for daily spending. Set specific day for bills.",
                min_value=0, max_value=31, step=1, default=0
            ),
            "is_active": st.column_config.CheckboxColumn("On?", default=True)
        }
    )
    
    if not edited_df.equals(df_sql):
        save_data(edited_df)

with col2:
    # --- SCENARIO BLOCK ---
    st.info("🎯 **Playground:** Adjust sliders to fit your dream into reality.")
    
    sc_c1, sc_c2 = st.columns(2)
    goal_cost = sc_c1.slider("Goal Cost (Trip/Gadget)", 0, 20000, 2000, 100)
    goal_days = sc_c2.slider("Buy in (days)", 1, 180, 60)
    
    goal_date_obj = date.today() + timedelta(days=goal_days)
    st.caption(f"Planned purchase date: **{goal_date_obj.strftime('%d %b %Y')}**")

    # --- CALCULATION CORE ---
    active_rows = edited_df[edited_df["is_active"] == True]
    fixed_expenses = active_rows[active_rows["day_of_month"] > 0]
    variable_sum = active_rows[active_rows["day_of_month"] == 0]["amount"].sum()
    daily_burn = variable_sum / 30
    
    data = []
    curr = start_bal
    
    min_balance = curr
    cash_gap_date = None
    
    for i in range(180):
        calc_date = date.today() + timedelta(days=i)
        day_num = calc_date.day
        
        curr -= daily_burn
        
        if day_num == sal_date:
            curr += sal_amt
            
        todays_bills = fixed_expenses[fixed_expenses["day_of_month"] == day_num]["amount"].sum()
        curr -= todays_bills
        
        if i == goal_days:
            curr -= goal_cost
            
        if curr < min_balance:
            min_balance = curr
        
        if curr < 0 and cash_gap_date is None:
            cash_gap_date = calc_date
            
        data.append({"Date": calc_date, "Balance": curr})

    chart_df = pd.DataFrame(data)

    # --- VISUALIZATION ---
    final_bal = chart_df.iloc[-1]['Balance']
    col_m1.metric("Balance in 6 mo.", f"{final_bal:,.0f} €")
    col_m2.metric("Lowest Point", f"{min_balance:,.0f} €", delta_color="normal" if min_balance > 0 else "inverse")
    
    if cash_gap_date:
        col_m3.error(f"Bankruptcy on {cash_gap_date.strftime('%d %b')}!")
    else:
        col_m3.success("Safe Budget ✅")

    color = "#ff4b4b" if min_balance < 0 else "#00c04b"
    st.area_chart(chart_df, x="Date", y="Balance", color=color)
    
    if min_balance < 0:
        st.warning(f"💡 **Advice:** You cannot afford a **{goal_cost:,} €** purchase in {goal_days} days.")
    else:
        st.success(f"🚀 **Go for it!** You can buy this and still keep a safety buffer of **{min_balance:,.0f} €**.")