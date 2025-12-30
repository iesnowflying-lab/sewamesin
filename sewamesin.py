import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. KONFIGURASI HALAMAN
st.set_page_config(
    page_title="Monitoring Peminjaman Mesin - sewa mesin01",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. CUSTOM CSS
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    .stApp { background-color: #fdfdfd; color: #333333; }
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
    }
    .stButton button { 
        width: 100%; 
        height: 85px; 
        border-radius: 15px; 
        font-weight: bold; 
    }
    .double-line {
        border-top: 3px solid #cbd5e1;
        border-bottom: 3px solid #cbd5e1;
        height: 8px;
        margin: 5px 0 25px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. KONEKSI DATA
url_sheets = "https://docs.google.com/spreadsheets/d/1BvYyCa0DgJrjuMYQzFEL_49_StYhr71rzvNJ8crwHaU/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    return conn.read(spreadsheet=url_sheets, ttl="0")

# --- FUNGSI WARNA KHUSUS KOLOM SISA ---
def color_sisa_only(val):
    try:
        # Mengambil angka dari teks "X Hari"
        num = int(str(val).split()[0])
        if num <= 0:
            return 'background-color: #ffcccc; color: black;' # Merah
        elif 1 <= num <= 7:
            return 'background-color: #fff9c4; color: black;' # Kuning
    except:
        pass
    return ''

# --- FUNGSI DIAGRAM PIE/DONUT ---
def create_min_donut(dataframe, site_name, colors):
    df_site = dataframe[dataframe['To'] == site_name].groupby('Jenis_Mesin')['Qty'].sum().reset_index()
    if df_site.empty: return None
    total_site = df_site['Qty'].sum()
    df_site['custom_label'] = df_site.apply(
        lambda x: f"{x['Jenis_Mesin']} / {x['Qty']} / {(x['Qty']/total_site*100):.1f}%", axis=1
    )
    fig = px.pie(df_site, values='Qty', names='Jenis_Mesin', hole=0.5, color_discrete_sequence=colors)
    fig.update_traces(
        textinfo='text', text=df_site['custom_label'], textposition='outside', 
        marker=dict(line=dict(color='#FFFFFF', width=2)), textfont_size=14
    )
    fig.add_annotation(text=site_name, x=0.5, y=0.5, showarrow=False, font=dict(size=30, family="Arial Black"))
    fig.update_layout(showlegend=False, height=650, margin=dict(t=50, b=50, l=10, r=10))
    return fig

# 4. HEADER
st.title("📡 Monitoring Peminjaman Mesin")
st.markdown('<div class="double-line"></div>', unsafe_allow_html=True)

try:
    df_raw = load_data()
    df = df_raw.copy()
    df['To'] = df['To'].astype(str).str.strip()
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0).astype(int)
    df['Akhir_Sewa'] = pd.to_datetime(df['Akhir_Sewa'], errors='coerce').dt.date
    
    hari_ini = datetime.now().date()
    df['Sisa'] = df['Akhir_Sewa'].apply(lambda x: (x - hari_ini).days if pd.notna(x) else 0)
    df_monitor = df[df['Status_Kembali'] == False].sort_values(by='Akhir_Sewa')

    # --- METRICS & REFRESH ---
    m1, m2, m3, m4 = st.columns([1, 1, 1, 0.6])
    total_unit = df_monitor['Qty'].sum()
    m1.metric("Total Unit Disewa", f"{total_unit} Unit")
    m2.metric("Deadline < 7 Hari", f"{df_monitor[df_monitor['Sisa'] <= 7].shape[0]} Mesin")
    m3.metric("Total Lokasi", f"{df_monitor['To'].nunique()} Lokasi")
    with m4:
        st.write("") 
        if st.button('🔄 Refresh Data'):
            st.cache_data.clear()
            st.rerun()

    # --- TABEL ---
    st.subheader("📋 Detail Peminjaman")
    df_table = df_monitor[['Jenis_Mesin', 'Merek', 'Type', 'Qty', 'To', 'Start_Sewa', 'Akhir_Sewa', 'Sisa']].copy()
    
    # Format agar rata kiri dengan menambahkan satuan secara manual
    df_table['Qty'] = df_table['Qty'].astype(str) + " Unit"
    df_table['Sisa'] = df_table['Sisa'].astype(str) + " Hari"
    df_table = df_table.rename(columns={'Sisa': 'Sisa Hari'})

    # Terapkan warna hanya di kolom Sisa Hari agar tidak merusak format tanggal
    styled_df = df_table.style.applymap(color_sisa_only, subset=['Sisa Hari'])
    st.dataframe(styled_df, hide_index=True, use_container_width=True)

    st.markdown("---")

    # --- DIAGRAM DONUT ---
    st.subheader("📍 Sebaran Unit Berdasarkan Lokasi")
    col_isg, col_irg = st.columns(2)
    with col_isg:
        f_isg = create_min_donut(df_monitor, 'ISG', px.colors.qualitative.Pastel)
        if f_isg: st.plotly_chart(f_isg, use_container_width=True)
    with col_irg:
        f_irg = create_min_donut(df_monitor, 'IRG', px.colors.qualitative.Safe)
        if f_irg: st.plotly_chart(f_irg, use_container_width=True)

    st.markdown("---")
    
    # --- DIAGRAM BATANG ---
    st.subheader("📊 Total Semua Jenis Mesin")
    df_total = df_monitor.groupby('Jenis_Mesin')['Qty'].sum().sort_values(ascending=True).reset_index()
    total_populasi = df_total['Qty'].sum()
    df_total['Persen'] = (df_total['Qty'] / total_populasi * 100).round(1)
    df_total['Label'] = df_total.apply(lambda x: f"{x['Qty']} Unit ({x['Persen']}%)", axis=1)

    fig_bar = px.bar(df_total, x='Qty', y='Jenis_Mesin', orientation='h', text='Label')
    fig_bar.update_traces(marker_color='#3b82f6', textposition='auto', textfont_size=12, cliponaxis=False)
    fig_bar.update_layout(
        showlegend=False, height=500, xaxis_title=None, yaxis_title=None, 
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(ticksuffix=" Unit", showgrid=True, gridcolor='#f1f5f9', range=[0, df_total['Qty'].max() * 1.3]),
        margin=dict(l=10, r=10, t=20, b=20)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

except Exception as e:
    st.error(f"❌ Kesalahan: {e}")

