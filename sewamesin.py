import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Monitoring Sewa ISG", layout="wide")

# CSS: Menghapus space atas dan mengatur font tabel
st.markdown("""
    <style>
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

# --- MEMULAI BLOK TRY DENGAN BENAR ---
try:
    df = load_data()
    
    if df.empty:
        st.error("Data dari Google Sheets kosong. Periksa koneksi atau URL sheet.")
        st.stop()
    
    # Pembersihan Data
    df['To'] = df['To'].astype(str).str.strip()
    df['Jenis_Mesin'] = df['Jenis_Mesin'].astype(str).str.strip()
    
    # Pastikan Qty numerik
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0).astype(int)
    
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
    
    # Fungsi untuk styling conditional: warna orange/kuning hanya pada kolom 'Sisa' jika <= 0
    def highlight_rows(row):
        styles = [''] * len(row)  # Default kosong untuk semua kolom
        if row['Sisa'] <= 0:
            # Cari indeks kolom 'Sisa' dan warnai dengan orange/kuning
            sisa_index = row.index.get_loc('Sisa')
            styles[sisa_index] = 'background-color: #ff6600'  # Warna orange-kuning
        return styles
    
    # Terapkan styling pada dataframe
    styled_df = df_monitor[['Jenis_Mesin', 'Merek', 'Type', 'Qty', 'From', 'To', 'Start_Sewa', 'Akhir_Sewa', 'Sisa']].style.apply(highlight_rows, axis=1)
    
    # Tampilkan dataframe dengan styling
    st.dataframe(
        styled_df,
        column_config={
            "Jenis_Mesin": st.column_config.TextColumn("Jenis_Mesin", width=20),
            "Merek": st.column_config.TextColumn("Merek", width=20),
            "Type": st.column_config.TextColumn("Type", width=20),
            "Qty": st.column_config.NumberColumn("Qty", width=5, format="%d"),
            "From": st.column_config.TextColumn("From", width=20),
            "To": st.column_config.TextColumn("To", width=20),
            "Start_Sewa": st.column_config.DateColumn("Start_Sewa", width=30, format="DD/MM/YYYY"),
            "Akhir_Sewa": st.column_config.DateColumn("Akhir_Sewa", width=30, format="DD/MM/YYYY"),
            "Sisa": st.column_config.NumberColumn("Sisa Hari", width=10, format="%d hr"),
        },
        hide_index=True,
        use_container_width=True
    )

    st.divider()

    # --- BAGIAN 2: GRAFIK PIE PER CUSTOMER ---
    st.subheader("📈 Distribusi Unit Berdasarkan Lokasi")
    
    # Mengambil data unik dari kolom 'To'
    list_customer = df_monitor['To'].unique()
    
    if len(list_customer) > 0:
        # Batasi kolom per baris (misalnya maks 4) untuk layout yang lebih baik
        max_cols_per_row = 4
        for start in range(0, len(list_customer), max_cols_per_row):
            cols = st.columns(min(max_cols_per_row, len(list_customer) - start))
            for i, customer in enumerate(list_customer[start:start + max_cols_per_row]):
                with cols[i]:
                    df_cust = df_monitor[df_monitor['To'] == customer]
                    df_pie = df_cust.groupby('Jenis_Mesin')['Qty'].sum().reset_index()
                    
                    if not df_pie.empty and df_pie['Qty'].sum() > 0:
                        fig = px.pie(
                            df_pie, 
                            values='Qty', 
                            names='Jenis_Mesin', 
                            title=f"Distribusi Unit untuk {customer}",
                            hole=0.3  # Donut chart
                        )
                        # Update layout: hilangkan legend, ukuran lebih besar, dan margin
                        fig.update_layout(
                            height=400,  # Tinggi chart lebih besar
                            width=400,   # Lebar chart lebih besar
                            showlegend=False,  # Hilangkan legend
                            margin=dict(l=20, r=20, t=40, b=20)  # Margin untuk ruang
                        )
                        # Update traces: tampilkan persentase, jumlah mesin (value), dan jenis mesin (label) di dalam pie
                        # Ubah insidetextorientation ke 'horizontal' agar tulisan tidak miring
                        fig.update_traces(
                            textinfo='percent+label+value',  # Menampilkan persentase, label (jenis mesin), dan nilai (jumlah mesin)
                            insidetextorientation='horizontal'  # Tulisan horizontal, bukan radial/miring
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.write(f"Tidak ada data unit untuk {customer}")
    else:
        st.write("Tidak ada lokasi customer yang tersedia.")

    # --- BAGIAN 3: GRAFIK KESELURUHAN (OPSIONAL, SEBAGAI TAMBAHAN) ---
    st.divider()
    st.subheader("📊 Distribusi Keseluruhan Berdasarkan Jenis Mesin")
    df_pie_overall = df_monitor.groupby('Jenis_Mesin')['Qty'].sum().reset_index()
    if not df_pie_overall.empty and df_pie_overall['Qty'].sum() > 0:
        fig_overall = px.pie(
            df_pie_overall, 
            values='Qty', 
            names='Jenis_Mesin', 
            title="Distribusi Keseluruhan Unit"
        )
        # Update layout: hilangkan legend, ukuran lebih besar, dan margin (sama seperti di atas)
        fig_overall.update_layout(
            height=400,
            width=400,
            showlegend=False,  # Hilangkan legend
            margin=dict(l=20, r=20, t=40, b=20)
        )
        # Update traces: tampilkan persentase, jumlah mesin (value), dan jenis mesin (label) di dalam pie
        # Ubah insidetextorientation ke 'horizontal' agar tulisan tidak miring
        fig_overall.update_traces(
            textinfo='percent+label+value',  # Menampilkan persentase, label (jenis mesin), dan nilai (jumlah mesin)
            insidetextorientation='horizontal'  # Tulisan horizontal, bukan radial/miring
        )
        st.plotly_chart(fig_overall, use_container_width=True)
    else:
        st.write("Tidak ada data untuk grafik keseluruhan.")

except Exception as e:
    st.error(f"Terjadi error: {str(e)}. Periksa koneksi Google Sheets atau format data.")
    st.stop()