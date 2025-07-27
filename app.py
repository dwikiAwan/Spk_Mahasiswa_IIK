from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from collections import Counter

app = Flask(__name__, template_folder='ui')

# Data kriteria dan bobot yang sudah ditentukan
CRITERIA = {
    'c1': {'name': 'Logika Pemrograman', 'weight': 0.30},
    'c2': {'name': 'Desain UI/UX', 'weight': 0.20},
    'c3': {'name': 'Matematika Dasar', 'weight': 0.25},
    'c4': {'name': 'Minat', 'weight': 0.25}
}

# Alternatif (jurusan) yang tersedia
ALTERNATIVES = {
    'A1': 'Web Developer',
    'A2': 'Mobile Developer',
    'A3': 'Data Analyst',
    'A4': 'Game Developer'
}

# Data profil ideal untuk setiap jurusan (dari studi kasus Anda)
JURUSAN_PROFILES = {
    'A1': {'c1': 80, 'c2': 90, 'c3': 70, 'c4': 4}, # Web Developer
    'A2': {'c1': 75, 'c2': 85, 'c3': 65, 'c4': 5}, # Mobile Developer
    'A3': {'c1': 90, 'c2': 70, 'c3': 90, 'c4': 3}, # Data Analyst
    'A4': {'c1': 85, 'c2': 95, 'c3': 75, 'c4': 5}  # Game Developer
}


EXISTING_DATA = [
    {'name': 'Budi', 'c1': 80, 'c2': 90, 'c3': 70, 'c4': 4},
    {'name': 'Citra', 'c1': 75, 'c2': 85, 'c3': 65, 'c4': 5},
    {'name': 'Dewi', 'c1': 90, 'c2': 70, 'c3': 90, 'c4': 3},
    {'name': 'Eko', 'c1': 85, 'c2': 95, 'c3': 75, 'c4': 5},
]


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mahasiswa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            c1 INTEGER,
            c2 INTEGER,
            c3 INTEGER,
            c4 INTEGER,
            rekomendasi TEXT
        )
    ''')
    conn.commit()
    conn.close()


def calculate_saw(all_data_for_max_calc, new_student_data):
    all_values_for_max = []
    for m_data in all_data_for_max_calc:
        all_values_for_max.append({k: m_data[k] for k in CRITERIA.keys()})
    for j_data in JURUSAN_PROFILES.values():
        all_values_for_max.append(j_data)

    max_values_overall = {}
    for key in CRITERIA.keys():
        # Pastikan ada data untuk dihitung MAX-nya, jika tidak, set ke nilai default (misal 1 untuk menghindari ZeroDivisionError)
        if all_values_for_max and any(key in d for d in all_values_for_max):
            max_values_overall[key] = max(d[key] for d in all_values_for_max if key in d)
        else:
            max_values_overall[key] = 1 # Default jika tidak ada data

    # Normalisasi nilai mahasiswa baru
    normalized_student_data = {}
    for key in CRITERIA.keys():
        if max_values_overall[key] == 0: # Hindari pembagian dengan nol
            normalized_student_data[key] = 0
        else:
            normalized_student_data[key] = new_student_data[key] / max_values_overall[key]

    # Hitung skor kecocokan mahasiswa baru dengan setiap profil jurusan
    # Menggunakan pendekatan SAW: sum(bobot * (nilai_mhs_normal * nilai_profil_normal))
    # Ini mengukur kesamaan antara mahasiswa dan profil jurusan, dibobotkan oleh kriteria.
    final_scores_for_jurusan = {}
    for alt_code, alt_name in ALTERNATIVES.items():
        profile = JURUSAN_PROFILES[alt_code]
        
        # Normalisasi profil jurusan (menggunakan max_values_overall yang sama)
        normalized_profile = {}
        for key in CRITERIA.keys():
            if max_values_overall[key] == 0: # Hindari pembagian dengan nol
                normalized_profile[key] = 0
            else:
                normalized_profile[key] = profile[key] / max_values_overall[key]
        
        compatibility_score = 0
        for key in CRITERIA.keys():
            compatibility_score += (normalized_student_data[key] * normalized_profile[key]) * CRITERIA[key]['weight']
        
        final_scores_for_jurusan[alt_code] = compatibility_score
    
    # Dapatkan jurusan dengan skor kecocokan tertinggi
    best_alternative_code = max(final_scores_for_jurusan, key=final_scores_for_jurusan.get)
    return ALTERNATIVES[best_alternative_code], final_scores_for_jurusan[best_alternative_code]


# ROUTE untuk halaman LANDING (HOME)
@app.route('/')
def landing():
    create_table() # Pastikan tabel dibuat saat aplikasi pertama kali diakses
    return render_template('landing.html')

# ROUTE untuk FORM INPUT (sekarang di /check)
@app.route('/check')
def index():
    create_table()
    return render_template('index.html')

# ROUTE untuk memproses data dari form input
@app.route('/calculate', methods=['POST'])
def calculate():
    nama = request.form['nama']
    c1 = int(request.form['c1'])
    c2 = int(request.form['c2'])
    c3 = int(request.form['c3'])
    c4 = int(request.form['c4'])

    conn = get_db_connection()
    # Ambil semua data mahasiswa dari database (kecuali yang baru diinput, karena belum disimpan)
    all_data_from_db_rows = conn.execute('SELECT nama, c1, c2, c3, c4 FROM mahasiswa').fetchall()
    conn.close()

    # Konversi sqlite3.Row objects ke dictionary agar konsisten dengan EXISTING_DATA
    processed_db_data = []
    for row in all_data_from_db_rows:
        processed_db_data.append({
            'name': row['nama'],
            'c1': row['c1'],
            'c2': row['c2'],
            'c3': row['c3'],
            'c4': row['c4']
        })

    # Data mahasiswa baru dalam format dictionary
    new_student_data = {'name': nama, 'c1': c1, 'c2': c2, 'c3': c3, 'c4': c4}

    # Gabungkan data lama (EXISTING_DATA) dengan data dari database dan data mahasiswa baru
    # Ini adalah dataset lengkap untuk perhitungan MAX global yang akurat.
    all_data_for_calculation = EXISTING_DATA + processed_db_data + [new_student_data]
    
    rekomendasi, nilai_akhir = calculate_saw(all_data_for_calculation, new_student_data)
    
    # Simpan data mahasiswa baru ke database
    conn = get_db_connection()
    conn.execute('INSERT INTO mahasiswa (nama, c1, c2, c3, c4, rekomendasi) VALUES (?, ?, ?, ?, ?, ?)',
                 (nama, c1, c2, c3, c4, rekomendasi))
    conn.commit()
    conn.close()
    
    return render_template('hasil.html', nama=nama, rekomendasi=rekomendasi, nilai_akhir=nilai_akhir)

# ROUTE untuk menampilkan daftar semua mahasiswa dengan filter
@app.route('/students')
def show_students():
    conn = get_db_connection()
    
    # Ambil parameter 'jurusan' dari URL (jika ada)
    selected_jurusan = request.args.get('jurusan')
    
    if selected_jurusan and selected_jurusan != 'all':
        # Jika ada filter jurusan yang dipilih, query database berdasarkan itu
        mahasiswa_list = conn.execute('SELECT * FROM mahasiswa WHERE rekomendasi = ?', (selected_jurusan,)).fetchall()
    else:
        # Jika tidak ada filter atau filter 'all', ambil semua mahasiswa
        mahasiswa_list = conn.execute('SELECT * FROM mahasiswa').fetchall()
    
    conn.close()
    
    # Kirim daftar jurusan yang tersedia ke template untuk dropdown filter
    all_jurusan_names = sorted(list(set(ALTERNATIVES.values()))) # Mengambil nama jurusan unik dan mengurutkannya
    
    return render_template('students.html', 
                           mahasiswa_list=mahasiswa_list,
                           all_jurusan_names=all_jurusan_names,
                           selected_jurusan=selected_jurusan)

# ROUTE untuk INFOGRAFIK (sekarang di /team)
@app.route('/team')
def show_infographics():
    conn = get_db_connection()
    # Ambil semua rekomendasi jurusan dari database
    all_recommendations = conn.execute('SELECT rekomendasi FROM mahasiswa').fetchall()
    conn.close()

    # Hitung jumlah rekomendasi untuk setiap jurusan
    recommendation_counts = Counter()
    for row in all_recommendations:
        recommendation_counts[row['rekomendasi']] += 1
    
    # Urutkan berdasarkan nama jurusan untuk konsistensi di chart
    sorted_recommendation_counts = {
        jurusan_name: recommendation_counts[jurusan_name]
        for jurusan_name in sorted(ALTERNATIVES.values())
    }

    total_students = sum(sorted_recommendation_counts.values())

    return render_template('team.html', # Menggunakan team.html
                           criteria=CRITERIA,
                           alternatives=ALTERNATIVES,
                           jurusan_profiles=JURUSAN_PROFILES,
                           recommendation_counts=sorted_recommendation_counts,
                           total_students=total_students)

if __name__ == '__main__':
    app.run(debug=True)
