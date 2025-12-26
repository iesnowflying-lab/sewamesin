import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Monitoring Sewa ISG", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: white;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    html, body, [class*="css"] { font-size: 1.1rem; }
    [data-testid="stDataFrame"] { font-size: 1.3rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Monitoring Peminjaman Mesin")

# 2. KONEKSI KE GOOGLE SHEETS
url_sheets = "https://docs.google.com/spreadsheets/d/1BvYyCa0DgJrjuMYQzFEL_49_StYhr71rzvNJ8crwHaU/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=url_sheets, ttl="0")

try:
    df = load_data()

    if df.empty:
        st.error("Data dari Google Sheets kosong.")
        st.stop()

    # --- PEMBERSIHAN DATA ---
    df['To'] = df['To'].astype(str).str.strip()
    df['Jenis_Mesin'] = df['Jenis_Mesin'].astype(str).str.strip()
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0).astype(int)
    
    # Penanganan kolom No_Surat agar sesuai dengan Google Sheets
    if 'No_Surat' not in df.columns:
        # Cek kemungkinan variasi nama (no_surat / No Surat)
        if 'no_surat' in df.columns:
            df = df.rename(columns={'no_surat': 'No_Surat'})
        elif 'No Surat' in df.columns:
            df = df.rename(columns={'No Surat': 'No_Surat'})
        else:
            df['No_Surat'] = "-" # Jika kolom benar-benar tidak ada

    # Konversi Tanggal & Hitung Sisa Hari
    df['Start_Sewa'] = pd.to_datetime(df['Start_Sewa'], errors='coerce').dt.date
    df['Akhir_Sewa'] = pd.to_datetime(df['Akhir_Sewa'], errors='coerce').dt.date
    hari_ini = datetime.now().date()
    df['Sisa'] = df['Akhir_Sewa'].apply(lambda x: (x - hari_ini).days if pd.notna(x) else 0)

    # Filter Status Belum Kembali
    df_monitor = df[df['Status_Kembali'] == False].sort_values(by='Akhir_Sewa')

    if df_monitor.empty:
        st.warning("Tidak ada mesin yang belum dikembalikan.")
        st.stop()

    # --- BAGIAN 1: TABEL REKAP ---
    st.subheader("📋 Rekap Peminjaman Mesin")

    def highlight_sisa_hari(row):
        styles = [''] * len(row)
        sisa_index = row.index.get_loc('Sisa')
        sisa = row['Sisa']
        
        if sisa < 0:
            styles[sisa_index] = 'background-color: #ff4b4b; color: white' # Merah
        elif sisa < 3:
            styles[sisa_index] = 'background-color: #ffa500; color: black' # Orange
        elif sisa < 6:
            styles[sisa_index] = 'background-color: #ffff00; color: black' # Kuning
            
        return styles

    # UPDATE URUTAN KOLOM: No_Surat diletakkan setelah 'To'
    display_columns = [
        'Jenis_Mesin', 'Merek', 'Type', 'Qty', 'From', 'To', 
        'No_Surat', 'Start_Sewa', 'Akhir_Sewa', 'Sisa'
    ]

    # Terapkan styling
    styled_df = df_monitor[display_columns].style.apply(highlight_sisa_hari, axis=1)

    st.dataframe(
        styled_df,
        column_config={
            "Jenis_Mesin": st.column_config.TextColumn("Jenis Mesin"),
            "Qty": st.column_config.NumberColumn("Qty", format="%d"),
            "To": st.column_config.TextColumn("To"),
            "No_Surat": st.column_config.TextColumn("No Surat", width="medium"),
            "Start_Sewa": st.column_config.DateColumn("Start Sewa", format="DD/MM/YYYY"),
            "Akhir_Sewa": st.column_config.DateColumn("Akhir Sewa", format="DD/MM/YYYY"),
            "Sisa": st.column_config.NumberColumn("Sisa Hari", format="%d hr"),
        },
        hide_index=True,
        use_container_width=True
    )

    st.divider()

    # --- BAGIAN 2: GRAFIK PIE ---
    st.subheader("📈 Distribusi Unit Berdasarkan Lokasi")
    list_customer = df_monitor['To'].unique()

    if len(list_customer) > 0:
        max_cols_per_row = 4
        for start in range(0, len(list_customer), max_cols_per_row):
            cols = st.columns(min(max_cols_per_row, len(list_customer) - start))
            for i, customer in enumerate(list_customer[start:start + max_cols_per_row]):
                with cols[i]:
                    df_cust = df_monitor[df_monitor['To'] == customer]
                    df_pie = df_cust.groupby('Jenis_Mesin')['Qty'].sum().reset_index()

                    if not df_pie.empty and df_pie['Qty'].sum() > 0:
                        fig = px.pie(df_pie, values='Qty', names='Jenis_Mesin', title=f"{customer}", hole=0.3)
                        fig.update_layout(height=400, showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
                        fig.update_traces(textinfo='percent+label+value', insidetextorientation='horizontal')
                        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Terjadi error: {str(e)}")

st.stop()