import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Tidal Technologies (TiTech)",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    /* Global Setting */
    .stApp { background-color: #050505; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; }
    
    /* HUD CARD STYLE */
    .hud-card {
        background: rgba(20, 25, 35, 0.7);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        backdrop-filter: blur(5px);
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .hud-card:hover { border-color: #94a3b8; transform: translateY(-3px); }
    
    .hud-label {
        font-size: 10px; color: #94a3b8; 
        text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px;
    }
    .hud-value {
        font-size: 28px; font-weight: 700; color: #f8fafc;
        text-shadow: 0 0 10px rgba(255,255,255,0.1);
    }
    .hud-unit { font-size: 11px; color: #64748b; font-weight: 400; }
    
    /* SYSTEM INSIGHT BOX (PENJELASAN DINAMIS) */
    .insight-box {
        background: rgba(15, 23, 42, 0.9);
        border-left: 4px solid #00f2ff;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 20px;
        font-size: 14px;
        line-height: 1.6;
        color: #e2e8f0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .insight-title {
        color: #00f2ff; font-weight: bold; margin-bottom: 5px; 
        text-transform: uppercase; font-size: 12px; letter-spacing: 1px;
    }
    
    /* Time Label on Slider */
    .time-label {
        color: #f87171; font-size: 14px; text-align: center; 
        margin-top: -25px; margin-bottom: 10px; font-weight: bold;
    }
    
    /* Section Headers */
    .section-header {
        font-size: 20px; font-weight: 600; color: #e2e8f0; 
        margin-top: 30px; margin-bottom: 15px; 
        border-left: 4px solid #00f2ff; padding-left: 15px;
    }
    
    /* Slider Customization */
    .stSlider [data-baseweb="slider"] { margin-top: -20px; }
    </style>
""", unsafe_allow_html=True)

# --- Perhitungan nilai ---
@st.cache_data
def get_smart_dataset():
    hours = 8784
    dates = pd.date_range(start="2024-01-01", periods=hours, freq='H')
    
    # 1. HIDROLIK (ARUS AIR)
    t = np.linspace(0, 4*np.pi, hours)
    flow = 0.5 + 0.35 * np.sin(t) + np.random.normal(0, 0.05, hours)
    flow = np.clip(flow, 0.05, 0.95) 
    
    # Perhitungan daya teoritis
    p_theory = 0.5 * 1000 * 2.0 * (flow**3)
    
    # Penentuan efisiensi turbin dinamis PR
    turbin_eff_curve = 0.45 * (1 - np.exp(-5 * (flow - 0.1))) 
    turbin_eff_curve = np.clip(turbin_eff_curve, 0, 0.45)
    
    # Daya dihasilkan (watt)
    p_gen = p_theory * turbin_eff_curve
    p_gen = np.clip(p_gen, 0, 1500)
    
    # Penentuan Performance Ratio Turbin (%)
    pr_turbin = turbin_eff_curve * 100 
    
    # Penentuan nilai rpm
    rotor_rpm = flow * 65 # menetapkan 65 RPM
    gen_rpm = rotor_rpm * 15 # Gearbox 1:15
    
    # Perbandingan voltase ED
    voltage = (p_gen / 55) + 10 # Baseline 10V
    voltage = np.clip(voltage, 0, 48)
    
    p_load = []
    rejection_list = [] 
    status = []
    
    # If else kondisi sistem mikrokontroller
    for v, p_avail in zip(voltage, p_gen):
        if v < 12:
            # mode berhenti
            mode = "Berhenti/ Daya rendah"
            cons = 5 # Watt (idle)
            rej = 0  # tidak berfungsi sistem elektrodialisis
        elif v < 22:
            # Mode (Normal)
            mode = "Berjalan Sedang / Normal"
            cons = p_avail * 0.6 # batas dari 60%
            rej = 70 + (v-12)*2.5
        else:
            mode = "Berjalan Optimal"
            cons = p_avail * 0.85 # batas dari 85%
            rej = 98.0 + np.random.uniform(0, 1.5) # Stabil tinggi
            
        p_load.append(cons)
        rejection_list.append(min(99.9, rej))
        status.append(mode)
            
    # Neraca Energi
    p_load = np.array(p_load)
    p_surplus = p_gen - p_load
    
    df = pd.DataFrame({
        'Timestamp': dates,
        'Formatted_Date': dates.strftime('%d %b %Y %H:%00'), 
        'Month': dates.strftime('%B'),
        'Flow_Rate': flow,
        'P_Gen': p_gen,
        'P_Load': p_load,
        'P_Surplus': p_surplus,
        'PR_Turbin': pr_turbin,
        'Voltage': voltage,
        'Pemisahan Air': rejection_list, 
        'Status': status,
        'Rotor_RPM': rotor_rpm,
        'Gen_RPM': gen_rpm
    })
    return df

df = get_smart_dataset()
c_head1, c_head2 = st.columns([2, 1])
with c_head1:
    # --- BAGIAN YANG DIUBAH ---
    st.markdown("## 🌊 TIDAL TECHNOLOGIES (TITECH)")
    st.caption("Sistem Terintegrasi Turbin Arus Pasut dengan Sistem Elektrodialisis")
    # ---------------------------

with c_head2:
    view_mode = st.selectbox(
        "RENTANG TAMPILAN:",
        ["🔴 REAL-TIME (Harian)", "🔴 BULANAN (Agregat)", "🔴 TAHUNAN (Laporan)"],
        index=0
    )

# --- LOGIC MODE TAMPILAN ---
if view_mode == "🔴 REAL-TIME (Harian)":
    
    # 1. SLIDER TANGGAL ASLI
    st.markdown("### Waktu Data")
    
    # Penggunaan slider untuk tanggal
    time_options = df['Formatted_Date'].tolist()
    start_val = time_options[4000] 
    selected_time_str = st.select_slider("", options=time_options, value=start_val)
    # Ambil Data slider
    row = df[df['Formatted_Date'] == selected_time_str].iloc[0]
    idx = df.index[df['Formatted_Date'] == selected_time_str][0]
    
    # If else penentuan kontrol panel sistem
    if row['Flow_Rate'] < 0.2:
        flow_desc = "Sangat Rendah (Kritis)"
        turbin_stats = "Turbin hampir berhenti, efisiensi rendah."
    elif row['Flow_Rate'] < 0.6:
        flow_desc = "Sedang (Stabil)"
        turbin_stats = "Turbin beroperasi pada zona efisiensi sedang/normal."
    else:
        flow_desc = "Tinggi (Optimal)"
        turbin_stats = "Turbin berputar maksimal, memicu efisiensi optimal."
        
    st.markdown(f"""
    <div class="insight-box">
        <div class="insight-title">🤖 Hasil Analisis Sistem </div>
        Saat ini pada <b>{selected_time_str}</b>, arus sungai terpantau <b>{row['Flow_Rate']:.2f} m/s ({flow_desc})</b>. {turbin_stats}<br>
        Generator menghasilkan tegangan <b>{row['Voltage']:.1f} V</b>, yang mengaktifkan mode <b>{row['Status']}</b>. 
        Hasilnya, kualitas pemisahan garam mencapai <b>{row['Pemisahan Air']:.2f}%</b> dengan sisa energi (surplus) sebesar <b>{row['P_Surplus']:.0f} Watt</b> untuk baterai.
    </div>
    """, unsafe_allow_html=True)

    # Visualisasi perencanaan energi dan performa
    st.markdown('<div class="section-header">1. Neraca Energi & Efisiensi Mesin</div>', unsafe_allow_html=True)
    
    k1, k2, k3, k4 = st.columns(4)
    
    def hud_card(col, label, val, unit, color):
        with col:
            st.markdown(f"""
            <div class="hud-card" style="border-left: 4px solid {color};">
                <div class="hud-label">{label}</div>
                <div class="hud-value">{val}</div>
                <div class="hud-unit">{unit}</div>
            </div>
            """, unsafe_allow_html=True)
            
    hud_card(k1, "OUTPUT TURBIN", f"{row['P_Gen']:.0f}", "WATT", "#00f2ff")
    hud_card(k2, "BEBAN ED", f"{row['P_Load']:.0f}", "WATT", "#facc15")
    hud_card(k3, "SURPLUS ENERGI", f"{row['P_Surplus']:.0f}", "WATT", "#4ade80")
    
    # Performance Ratio Turbin 
    pr_color = "#4ade80" if row['PR_Turbin'] > 30 else "#f87171"
    hud_card(k4, "PR TURBIN", f"{row['PR_Turbin']:.1f}", "% EFISIENSI", pr_color)

    # Nilai Performa Hybrid Elektrodialisis
    st.markdown('<div class="section-header">2. Performa Hybrid Multicell ED</div>', unsafe_allow_html=True)
    
    g1, g2, g3 = st.columns([1, 1, 2])
    
    with g1:
        # Tingkat pemisahan laut
        fig_rej = go.Figure(go.Indicator(
            mode = "gauge+number", value = row['Pemisahan Air'],
            title = {'text': "Persentase tingkat pemisahan (%)", 'font': {'size': 14}},
            gauge = {
                'axis': {'range': [0, 100]}, 
                'bar': {'color': "#4ade80" if row['Pemisahan Air'] > 95 else "#f87171"},
                'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': 95},
                'bgcolor': "#1e293b"
            }
        ))
        fig_rej.update_layout(height=180, margin={'t':40,'b':10}, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_rej, use_container_width=True)
        
    with g2:
        # Generator voltase gauss
        fig_vol = go.Figure(go.Indicator(
            mode = "gauge+number", value = row['Voltage'],
            title = {'text': "Tegangan Sel (Volt)", 'font': {'size': 14}},
            gauge = {
                'axis': {'range': [0, 50]}, 
                'bar': {'color': "#facc15"},
                'steps': [{'range': [0, 12], 'color': '#334155'}, {'range': [20, 50], 'color': '#1e293b'}],
                'bgcolor': "#1e293b"
            }
        ))
        fig_vol.update_layout(height=180, margin={'t':40,'b':10}, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_vol, use_container_width=True)
        
    with g3:
        # Grafik perbandingan Korelasi Arus vs Pemisahan air laut
        st.markdown("**Monitoring Dinamika (24 Jam)**")
        # Zoom data +/- 12 jam
        df_zoom = df.iloc[max(0, idx-12):min(len(df), idx+12)]
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=df_zoom['Timestamp'], y=df_zoom['Flow_Rate'], name='Arus Air (m/s)', yaxis='y1', line=dict(color='#00f2ff')))
        fig_trend.add_trace(go.Scatter(x=df_zoom['Timestamp'], y=df_zoom['Pemisahan Air'], name='Pemisahan Air (%)', yaxis='y2', line=dict(color='#4ade80')))
        # Garis Slider
        vline = row['Timestamp'].timestamp() * 1000
        fig_trend.add_vline(x=vline, line_dash="dash", line_color="white", annotation_text="POSISI SLIDER")
        fig_trend.update_layout(
            template="plotly_dark", height=200,
            yaxis=dict(title=dict(text="Arus (m/s)", font=dict(color="#00f2ff"))),
            yaxis2=dict(title=dict(text="Pemisahan (%)", font=dict(color="#4ade80")), overlaying='y', side='right'),
            margin=dict(l=0, r=0, t=10, b=0), showlegend=True, legend=dict(orientation="h", y=1.2),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_trend, use_container_width=True)

else:
    # Visualisasi hasil data bulanan dan tahunan
    c_filt1, c_filt2 = st.columns(2)
    with c_filt1:
        agg_method = st.selectbox("Metode Statistik:", ["Rata-rata (Average)", "Total (Sum)", "Maksimum (Max)"])
    
    with c_filt2:
        if view_mode == "🔴 BULANAN (Agregat)":
            filter_val = st.selectbox("Pilih Bulan:", df['Month'].unique())
            df_target = df[df['Month'] == filter_val]
            group_col = df_target['Timestamp'].dt.day
            x_label = "Tanggal"
        else: # Tahunan
            df_target = df
            group_col = df_target['Timestamp'].dt.month_name()
            x_label = "Bulan"

    # Proses Agregasi
    if "Total" in agg_method:
        row_data = df_target.sum(numeric_only=True)
        # Khusus metrik non-kumulatif, ambil rata-rata
        row_data['Voltage'] = df_target['Voltage'].mean()
        row_data['Pemisahan Air'] = df_target['Pemisahan Air'].mean()
        row_data['PR_Turbin'] = df_target['PR_Turbin'].mean()
        chart_df = df_target.groupby(group_col).sum(numeric_only=True).reset_index()
        unit_str = "kWh (Total)"
        # Convert Watt-hour ke kWh untuk Total
        val_gen = row_data['P_Gen'] / 1000
        val_ed = row_data['P_Load'] / 1000
        val_surplus = row_data['P_Surplus'] / 1000
    elif "Maksimum" in agg_method:
        row_data = df_target.max(numeric_only=True)
        chart_df = df_target.groupby(group_col).max(numeric_only=True).reset_index()
        unit_str = "Peak Watt"
        val_gen = row_data['P_Gen']
        val_ed = row_data['P_Load']
        val_surplus = row_data['P_Surplus']
    else: # Average
        row_data = df_target.mean(numeric_only=True)
        chart_df = df_target.groupby(group_col).mean(numeric_only=True).reset_index()
        unit_str = "Avg Watt"
        val_gen = row_data['P_Gen']
        val_ed = row_data['P_Load']
        val_surplus = row_data['P_Surplus']
    
    # Rename kolom grouping agar konsisten untuk plotting
    chart_df.columns = [x_label] + list(chart_df.columns[1:])
    
    # --- TAMPILAN LAPORAN ---
    st.markdown(f"### LAPORAN {view_mode.split()[1]} - {agg_method.upper()}")
    
    k1, k2, k3, k4 = st.columns(4)
    def hud_card(col, label, val, unit, color):
        with col:
            st.markdown(f"""
            <div class="hud-card" style="border-left: 4px solid {color};">
                <div class="hud-label">{label}</div>
                <div class="hud-value">{val:,.0f}</div>
                <div class="hud-unit">{unit}</div>
            </div>
            """, unsafe_allow_html=True)
            
    hud_card(k1, "ENERGI DIHASILKAN", val_gen, unit_str, "#00f2ff")
    hud_card(k2, "ENERGI DESALINASI", val_ed, unit_str, "#facc15")
    hud_card(k3, "SURPLUS ENERGI", val_surplus, unit_str, "#4ade80")
    hud_card(k4, "AVG EFISIENSI TURBIN", row_data['PR_Turbin'], "% Ratio", "#a855f7")
    
    st.markdown("---")
    c_chart1, c_chart2 = st.columns([2, 1])
    
    with c_chart1:
        st.markdown(f"**Tren Distribusi Energi ({x_label})**")
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=chart_df[x_label], y=chart_df['P_Gen'], name='Generated', marker_color='#00f2ff'))
        fig_bar.add_trace(go.Bar(x=chart_df[x_label], y=chart_df['P_Load'], name='Used (ED)', marker_color='#facc15'))
        fig_bar.update_layout(template="plotly_dark", barmode='group', height=350, paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c_chart2:
        st.markdown("**Proporsi Total**")
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Desalinasi', 'Surplus'], 
            values=[val_ed, val_surplus], 
            hole=.6, marker=dict(colors=['#facc15', '#4ade80'])
        )])
        fig_pie.update_layout(template="plotly_dark", height=350, showlegend=True, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

# Footer Table
with st.expander(" Hasil Data File Keseluruhan"):
    if view_mode == "🔴 REAL-TIME (Harian)":
        st.dataframe(df)
    else:
        st.dataframe(chart_df)
