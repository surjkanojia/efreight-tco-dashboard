import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- PAGE SETUP ---
st.set_page_config(page_title="Dynamic E-Freight Master Model", layout="wide")
st.title("🚛 E-Freight TCO Dashboard")
st.markdown("Fully dynamic architecture with automated financial interpretations.")

# --- SIDEBAR 1: FREIGHT CATEGORY (THE LINKED DICTIONARY) ---
st.sidebar.header("1. Vehicle Configuration")
freight_presets = {
    "Light Commercial (e.g., Urban Delivery)": {"battery": 25, "eff": 0.25, "ev_price": 1200000, "d_price": 800000, "d_kml": 14.0},
    "Medium Duty (e.g., Regional Logistics)": {"battery": 150, "eff": 0.8, "ev_price": 2800000, "d_price": 1600000, "d_kml": 6.0},
    "Heavy Duty (e.g., Highway Freight)": {"battery": 250, "eff": 1.2, "ev_price": 4500000, "d_price": 2500000, "d_kml": 3.5}
}
selected_freight = st.sidebar.selectbox("Select Freight Class", list(freight_presets.keys()))
preset = freight_presets[selected_freight]

# --- SIDEBAR 2: TECHNICAL & ECONOMIC VARIABLES ---
st.sidebar.header("2. Modify Parameters")

with st.sidebar.expander("⏱️ Operational Route"):
    daily_km = st.number_input("Daily Distance (km)", value=120, step=10)
    operating_days = st.number_input("Operating Days per Year", value=300, step=10)
    lifespan = st.number_input("Project Lifespan (Years)", value=10, step=1)

with st.sidebar.expander("⛽ Diesel Economics"):
    diesel_truck_price = st.number_input("Diesel Truck Price (₹)", value=preset["d_price"], step=100000)
    diesel_price = st.slider("Diesel Fuel Price (₹/Liter)", 70.0, 130.0, 90.0, step=0.5)
    diesel_mileage = st.number_input("Diesel Mileage (km/l)", value=preset["d_kml"], step=0.5)

with st.sidebar.expander("⚡ Electric Vehicle Variables"):
    electric_truck_price = st.number_input("EV Truck Price (₹)", value=preset["ev_price"], step=100000)
    subsidy_amount = st.number_input("Gov Subsidy (₹)", value=300000, step=50000)
    battery_capacity = st.number_input("Battery Capacity (kWh)", value=preset["battery"], step=5)
    ev_efficiency = st.number_input("EV Efficiency (kWh/km)", value=preset["eff"], step=0.05)
    
    # Second-life battery valuation calculation (80% health * ₹4000/kWh)
    default_salvage = int(battery_capacity * 0.8 * 4000)
    battery_salvage_value = st.number_input("Battery Salvage Value (₹)", value=default_salvage, step=10000)

with st.sidebar.expander("🔌 Grid & Charging Tariffs (₹/kWh)"):
    tariff_standard = st.slider("Standard Grid Tariff", 4.0, 15.0, 8.5, step=0.5)
    tariff_night = st.slider("Night Depot Charging", 3.0, 12.0, 6.0, step=0.5)
    tariff_solar = st.slider("Solar PPA / Warehouse", 2.0, 10.0, 4.5, step=0.5)
    tariff_peak = st.slider("Public Fast / Peak Traffic", 8.0, 25.0, 15.0, step=0.5)

chart_color = st.sidebar.color_picker("Pick EV Chart Color", "#2ca02c")

# --- DYNAMIC BACKGROUND MATH ---
annual_km = daily_km * operating_days

# Diesel Math
diesel_cpm = diesel_price / diesel_mileage
diesel_annual_opex = diesel_cpm * annual_km
diesel_lifetime_opex = diesel_annual_opex * lifespan
tco_diesel = diesel_truck_price + diesel_lifetime_opex

# EV Math (Using Standard Grid for the baseline timeline)
ev_capex = electric_truck_price - subsidy_amount
ev_cpm_standard = ev_efficiency * tariff_standard
ev_annual_opex_standard = ev_cpm_standard * annual_km
ev_lifetime_opex = ev_annual_opex_standard * lifespan
tco_ev = ev_capex + ev_lifetime_opex - battery_salvage_value

# --- 1. INSTANT METRICS ---
st.subheader("1. Operational Snapshot")
col1, col2, col3, col4 = st.columns(4)
col1.metric("EV Running Cost (Standard)", f"₹ {ev_cpm_standard:,.2f} /km")
col2.metric("Diesel Running Cost", f"₹ {diesel_cpm:,.2f} /km")
col3.metric("Annual Distance", f"{annual_km:,} km")
col4.metric(f"Total {lifespan}-Year Savings", f"₹ {(tco_diesel - tco_ev):,.0f}")
st.divider()

# --- 2. MULTI-CHART INFERENCES & DATA ENGINE ---
st.subheader("2. Financial Visualizations & Interpretations")

# Building the Timeline Data
years = np.arange(1, lifespan + 1)
df_timeline = pd.DataFrame({
    "Year": years,
    "Diesel_Lakhs": (diesel_truck_price + (diesel_annual_opex * years)) / 100000,
    "EV_Lakhs": (ev_capex + (ev_annual_opex_standard * years)) / 100000
})

# Logic to find the Break-Even Year
breakeven_year = "Does Not Break Even"
for y in years:
    if df_timeline.loc[df_timeline['Year'] == y, 'EV_Lakhs'].values[0] < df_timeline.loc[df_timeline['Year'] == y, 'Diesel_Lakhs'].values[0]:
        breakeven_year = y
        break

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("**Cumulative Break-Even Timeline**")
    fig1, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(df_timeline['Year'], df_timeline['Diesel_Lakhs'], color='red', linewidth=2, marker='o', label='Diesel TCO')
    ax1.plot(df_timeline['Year'], df_timeline['EV_Lakhs'], color=chart_color, linewidth=2, marker='o', label='EV TCO')
    ax1.set_xlabel("Years")
    ax1.set_ylabel("Total Cost (Lakhs INR)")
    ax1.set_ylim(bottom=0) # Proper scaling: Forces Y-axis to start at 0
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig1)

with chart_col2:
    st.markdown("**Total TCO Breakdown**")
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    labels = ['Diesel', 'Electric']
    capex_data = [diesel_truck_price / 100000, ev_capex / 100000]
    opex_data = [diesel_lifetime_opex / 100000, ev_lifetime_opex / 100000]
    
    ax2.bar(labels, capex_data, label='CAPEX (Upfront Cost)', color='#404040')
    ax2.bar(labels, opex_data, bottom=capex_data, label='OPEX (Fuel/Energy)', color=['#ff9999', chart_color])
    ax2.set_ylabel("Cost (Lakhs INR)")
    ax2.set_ylim(bottom=0) # Proper scaling
    ax2.legend()
    st.pyplot(fig2)

# --- AUTOMATED TEXT INTERPRETATION ---
st.info(f"**Automated Data Interpretation:** For a **{selected_freight}** operating {annual_km:,} km per year, the Electric Vehicle requires a higher upfront investment but costs significantly less to operate (₹{ev_cpm_standard:.2f}/km vs ₹{diesel_cpm:.2f}/km). Based on current parameters, the EV completely recovers its initial cost premium by **Year {breakeven_year}**. Over the full {lifespan}-year lifecycle, the EV strategy yields a net financial saving of **₹{(tco_diesel - tco_ev)/100000:.2f} Lakhs**, not including the end-of-life battery salvage value which returns an estimated ₹{battery_salvage_value:,.0f} to the operator.")
st.divider()

# --- 3. CHARGING STRATEGY COMPARISON ---
st.subheader("3. Charging Infrastructure Strategy Comparison")

df_scenarios = pd.DataFrame({
    "Strategy": ["Standard Grid", "Night Depot Charging", "Solar PPA", "Public Fast / Peak"],
    "Tariff_INR": [tariff_standard, tariff_night, tariff_solar, tariff_peak]
})
df_scenarios['Cost_per_km'] = df_scenarios['Tariff_INR'] * ev_efficiency
df_scenarios['Lifetime_TCO_Lakhs'] = (ev_capex + (df_scenarios['Cost_per_km'] * annual_km * lifespan) - battery_salvage_value) / 100000

fig3, ax3 = plt.subplots(figsize=(10, 4))
ax3.bar(df_scenarios['Strategy'], df_scenarios['Lifetime_TCO_Lakhs'], color=chart_color)
ax3.axhline(y=(tco_diesel/100000), color='red', linestyle='--', linewidth=2, label=f'Diesel Baseline (₹{tco_diesel/100000:,.1f}L)')
ax3.set_ylabel("10-Year TCO (Lakhs INR)")
ax3.set_ylim(bottom=0) # Proper scaling
ax3.legend()
ax3.grid(axis='y', linestyle='--', alpha=0.5)
st.pyplot(fig3)

# --- 4. DATA EXPORT ---
csv_data = df_scenarios.to_csv(index=False).encode('utf-8')
st.download_button(label="📥 Download Strategy Data as CSV", data=csv_data, file_name='tco_strategy_data.csv', mime='text/csv')
