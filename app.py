import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.colors as pc

# Memuat dan memproses data
data_kualitas_udara = pd.read_csv('data/combined_air_quality_data.csv')
data_kualitas_udara['timestamp'] = pd.to_datetime(data_kualitas_udara['timestamp'])

# Mengidentifikasi kolom untuk polutan dan kondisi cuaca
polutan = data_kualitas_udara.columns[:6].tolist()
kondisi_cuaca = data_kualitas_udara.columns[6:10].tolist() + [data_kualitas_udara.columns[11]]

# Pengurutan tingkat kualitas udara
tingkat_kualitas = ['Good', 'Hazardous', 'Moderate', 'Unhealthy', 'Unhealthy for Sensitive Groups', 'Very Unhealthy']

# Konfigurasi halaman Streamlit
st.set_page_config(page_title='Dashboard Kualitas Udara', page_icon='https://i.ibb.co/gmPh93j/Pngtree-chemical-plant-air-pollution-5929941.png')

st.title('Dashboard Analisis Kualitas Udara Beijing (2013 - 2017)')
with st.sidebar:
    st.markdown(
        """
        <div style="text-align: center;">
            <img src="https://i.ibb.co/gmPh93j/Pngtree-chemical-plant-air-pollution-5929941.png" alt="logo" width="200">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.header('Filter')
    opsi_stasiun = ['Semua Stasiun'] + data_kualitas_udara['station'].unique().tolist()
    stasiun_terpilih = st.multiselect('Pilih Stasiun', opsi_stasiun, default='Semua Stasiun')

    opsi_kategori = ['Semua Kategori'] + data_kualitas_udara['Category'].unique().tolist()
    kategori_terpilih = st.selectbox('Pilih Kategori Kualitas Udara', opsi_kategori)

    # Filter pemilihan tanggal dan jam
    tanggal_mulai = st.date_input('Tanggal Mulai', data_kualitas_udara['timestamp'].min().date())
    tanggal_akhir = st.date_input('Tanggal Akhir', data_kualitas_udara['timestamp'].max().date())
    jam_mulai = st.slider('Jam Mulai', 0, 23, 0)
    jam_akhir = st.slider('Jam Akhir', 0, 23, 23)

# Penyaringan dataset berdasarkan pilihan pengguna
if 'Semua Stasiun' in stasiun_terpilih:
    stasiun_terpilih = opsi_stasiun[1:]  # Menghapus 'Semua Stasiun'

dataset_terfilter = data_kualitas_udara[
    (data_kualitas_udara['station'].isin(stasiun_terpilih)) &
    (data_kualitas_udara['Category'].isin([kategori_terpilih] if kategori_terpilih != 'Semua Kategori' else opsi_kategori)) &
    (data_kualitas_udara['timestamp'].dt.date.between(tanggal_mulai, tanggal_akhir)) &
    (data_kualitas_udara['timestamp'].dt.hour.between(jam_mulai, jam_akhir))
]

tab = st.tabs(["Ikhtisar", "Tren Polutan", "Hubungan Polutan", "Kualitas Udara Stasiun"])

with tab[0]:
    st.write(f"**Data untuk {', '.join(stasiun_terpilih)} - {kategori_terpilih}**")
    jumlah_ringkasan = dataset_terfilter['Category'].value_counts().reindex(tingkat_kualitas, fill_value=0)
    for tingkat, jumlah in jumlah_ringkasan.items():
        st.metric(tingkat, f"{jumlah} Hari")

    diagram_pai = px.pie(
        names=jumlah_ringkasan.index,
        values=jumlah_ringkasan.values,
        title='Distribusi Kategori Kualitas Udara'
    )
    st.plotly_chart(diagram_pai)

with tab[1]:
    # Plot deret waktu untuk polutan yang dipilih
    pilihan_polutan = st.selectbox('Pilih Polutan', polutan)

    # Pastikan 'timestamp' dalam format datetime
    dataset_terfilter['timestamp'] = pd.to_datetime(dataset_terfilter['timestamp'])

    # Pilih kolom numerik untuk pengambilan sampel ulang, termasuk 'timestamp'
    kolom_numerik = dataset_terfilter.select_dtypes(include=[np.number]).columns.tolist()
    kolom_resampling = kolom_numerik + ['timestamp']
    data_resampling = dataset_terfilter[kolom_resampling]

    if not data_resampling.empty:
        data_deret_waktu = data_resampling.resample('M', on='timestamp').mean()
        grafik_garis = px.line(
            data_deret_waktu,
            x=data_deret_waktu.index,
            y=pilihan_polutan,
            title=f'Rata-Rata Bulanan {pilihan_polutan}'
        )
        st.plotly_chart(grafik_garis)
    else:
        st.write("Tidak ada data tersedia untuk filter yang dipilih.")

with tab[2]:
    # Plot scatter korelasi antar polutan
    polutan_x = st.selectbox('Pilih Polutan untuk Sumbu X', polutan, index=0)
    polutan_y = st.selectbox('Pilih Polutan untuk Sumbu Y', polutan, index=1)
    plot_scatter = px.scatter(
        dataset_terfilter,
        x=polutan_x,
        y=polutan_y,
        color='station',
        title=f'Korelasi antara {polutan_x} dan {polutan_y}'
    )
    st.plotly_chart(plot_scatter)

with tab[3]:
    # Distribusi kualitas udara per stasiun dan dampak arah angin
    pivot_stasiun = dataset_terfilter.pivot_table(
        index='station',
        columns='Category',
        values='PM2.5',
        aggfunc='count',
        fill_value=0
    )
    grafik_batang = px.bar(
        pivot_stasiun,
        x=pivot_stasiun.index,
        y=tingkat_kualitas,
        title='Kualitas Udara per Stasiun',
        labels={'value': 'Jumlah', 'variable': 'Kategori'},
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    grafik_batang.update_layout(barmode='stack')
    st.plotly_chart(grafik_batang)

    data_angin = data_kualitas_udara.groupby(['wd', 'Category']).size().reset_index(name='jumlah')
    data_angin['Urutan_Kategori'] = data_angin['Category'].map({tingkat: idx for idx, tingkat in enumerate(tingkat_kualitas)})
    data_angin_terurut = data_angin.sort_values(by=['Urutan_Kategori', 'wd'])

    biru = pc.sequential.Blues_r[:len(tingkat_kualitas)]
    grafik_polar = go.Figure()
    for idx, tingkat in enumerate(tingkat_kualitas):
        data_kategori = data_angin_terurut[data_angin_terurut['Category'] == tingkat]
        grafik_polar.add_trace(go.Barpolar(
            r=data_kategori['jumlah'],
            theta=data_kategori['wd'],
            name=tingkat,
            marker=dict(color=biru[idx])
        ))
    grafik_polar.update_layout(title="Distribusi Arah Angin dan Kualitas Udara")
    st.plotly_chart(grafik_polar)