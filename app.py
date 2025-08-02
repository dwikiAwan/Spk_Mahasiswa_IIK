from flask import Flask, render_template, request
import sqlite3
from collections import Counter

app = Flask(__name__, template_folder='ui')

# Data kriteria dan bobot sesuai studi kasus
CRITERIA = {
    'c1': {'name': 'Logika Pemrograman', 'weight': 0.30, 'type': 'benefit'},
    'c2': {'name': 'Desain UI/UX', 'weight': 0.20, 'type': 'benefit'},
    'c3': {'name': 'Matematika Dasar', 'weight': 0.25, 'type': 'benefit'},
    'c4': {'name': 'Minat (1-5)', 'weight': 0.25, 'type': 'benefit'}
}

# Alternatif jurusan
ALTERNATIVES = {
    'A1': 'Web Developer',
    'A2': 'Mobile Developer', 
    'A3': 'Data Analyst',
    'A4': 'Game Developer'
}

# PROFIL JURUSAN
JURUSAN_PROFILES = {
    'A1': {'c1': 80, 'c2': 90, 'c3': 70, 'c4': 4},
    'A2': {'c1': 75, 'c2': 85, 'c3': 65, 'c4': 4.5},
    'A3': {'c1': 90, 'c2': 70, 'c3': 90, 'c4': 3.5},
    'A4': {'c1': 85, 'c2': 95, 'c3': 75, 'c4': 5}
}

# Data existing untuk perhitungan normalisasi
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
            rekomendasi TEXT,
            nilai_saw REAL
        )
    ''')
    conn.commit()
    conn.close()

def calculate_saw(all_data_for_max_calc, new_student_data):
    # Step 1: Gabungkan semua data untuk mencari nilai maksimum
    all_values_for_max = [{k: m_data[k] for k in CRITERIA.keys() if k in m_data} for m_data in all_data_for_max_calc]
    all_values_for_max.extend(JURUSAN_PROFILES.values())

    # Step 2: Cari nilai maksimum untuk setiap kriteria (untuk normalisasi)
    max_values_overall = {key: max(d[key] for d in all_values_for_max if key in d) if all_values_for_max and any(key in d for d in all_values_for_max) else 1 for key in CRITERIA.keys()}

    # Step 3: Normalisasi nilai mahasiswa baru 
    normalized_student_data = {key: new_student_data[key] / max_values_overall[key] if max_values_overall[key] != 0 else 0 for key in CRITERIA.keys()}

    final_scores_for_jurusan = {}
    detail_perhitungan = {}

    for alt_code, alt_name in ALTERNATIVES.items():
        profile = JURUSAN_PROFILES[alt_code]
        
        normalized_profile = {key: profile[key] / max_values_overall[key] if max_values_overall[key] != 0 else 0 for key in CRITERIA.keys()}
        
        compatibility_score = 0
        detail_kriteria = {}
        
        for key in CRITERIA.keys():
            similarity = 1 - abs(normalized_student_data[key] - normalized_profile[key])
            weighted_score = similarity * CRITERIA[key]['weight']
            compatibility_score += weighted_score
            
            detail_kriteria[key] = {
                'mahasiswa_raw': new_student_data[key],
                'profil_raw': profile[key],
                'mahasiswa_normalized': round(normalized_student_data[key], 4),
                'profil_normalized': round(normalized_profile[key], 4),
                'similarity': round(similarity, 4),
                'weighted_score': round(weighted_score, 4),
                'weight': CRITERIA[key]['weight']
            }
        
        final_scores_for_jurusan[alt_code] = compatibility_score
        detail_perhitungan[alt_code] = detail_kriteria
    
    best_alternative_code = max(final_scores_for_jurusan, key=final_scores_for_jurusan.get)
    
    return (
        ALTERNATIVES[best_alternative_code],
        final_scores_for_jurusan[best_alternative_code],
        final_scores_for_jurusan,
        detail_perhitungan,
        max_values_overall
    )

@app.route('/')
def landing():
    create_table()
    return render_template('landing.html')

@app.route('/check')
def index():
    create_table()
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    nama = request.form['nama']
    c1 = int(request.form['c1'])
    c2 = int(request.form['c2'])
    c3 = int(request.form['c3'])
    c4 = int(request.form['c4'])

    conn = get_db_connection()
    all_data_from_db_rows = conn.execute('SELECT nama, c1, c2, c3, c4 FROM mahasiswa').fetchall()
    conn.close()

    processed_db_data = [{'name': row['nama'], 'c1': row['c1'], 'c2': row['c2'], 'c3': row['c3'], 'c4': row['c4']} for row in all_data_from_db_rows]

    new_student_data = {'name': nama, 'c1': c1, 'c2': c2, 'c3': c3, 'c4': c4}
    all_data_for_calculation = EXISTING_DATA + processed_db_data + [new_student_data]

    rekomendasi, nilai_saw, all_scores, detail_perhitungan, max_values = calculate_saw(
        all_data_for_calculation, new_student_data
    )

    conn = get_db_connection()
    conn.execute('''INSERT INTO mahasiswa (nama, c1, c2, c3, c4, rekomendasi, nilai_saw) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (nama, c1, c2, c3, c4, rekomendasi, nilai_saw))
    conn.commit()
    conn.close()

    return render_template('hasil.html', 
                            nama=nama, 
                            rekomendasi=rekomendasi, 
                            nilai_akhir=nilai_saw,
                            all_scores=all_scores,
                            detail_perhitungan=detail_perhitungan,
                            max_values=max_values,
                            alternatives=ALTERNATIVES,
                            criteria=CRITERIA,
                            student_data=new_student_data,
                            jurusan_profiles=JURUSAN_PROFILES)

# ---
# Route untuk menampilkan daftar mahasiswa
# Logika ini sudah benar, tetapi saya pastikan tidak ada karakter tersembunyi
@app.route('/students')
def show_students():
    conn = get_db_connection()
    selected_jurusan = request.args.get('jurusan')

    if selected_jurusan and selected_jurusan != 'all':
        mahasiswa_list = conn.execute('SELECT * FROM mahasiswa WHERE rekomendasi = ?', (selected_jurusan,)).fetchall()
    else:
        mahasiswa_list = conn.execute('SELECT * FROM mahasiswa').fetchall()

    conn.close()
    
    all_jurusan_names = sorted(list(set(ALTERNATIVES.values())))

    return render_template('students.html',
                            mahasiswa_list=mahasiswa_list,
                            all_jurusan_names=all_jurusan_names,
                            selected_jurusan=selected_jurusan)

# ---
# Route untuk infografis (tidak ada perubahan)
@app.route('/team')
def show_infographics():
    conn = get_db_connection()
    all_recommendations = conn.execute('SELECT rekomendasi FROM mahasiswa').fetchall()
    conn.close()

    recommendation_counts = Counter(row['rekomendasi'] for row in all_recommendations)
    
    sorted_recommendation_counts = {
        jurusan_name: recommendation_counts[jurusan_name]
        for jurusan_name in sorted(ALTERNATIVES.values())
    }

    total_students = sum(sorted_recommendation_counts.values())
    nama_jurusan = list(sorted_recommendation_counts.keys())
    skor_akhir = list(sorted_recommendation_counts.values())

    rekomendasi_terbaik, nilai_tertinggi = ("-", 0) if not skor_akhir else (
        nama_jurusan[skor_akhir.index(max(skor_akhir))],
        max(skor_akhir)
    )

    return render_template('team.html',
        criteria=CRITERIA,
        alternatives=ALTERNATIVES,
        jurusan_profiles=JURUSAN_PROFILES,
        recommendation_counts=sorted_recommendation_counts,
        total_students=total_students,
        nama_jurusan=nama_jurusan,
        skor_akhir=skor_akhir,
        rekomendasi_terbaik=rekomendasi_terbaik,
        nilai_tertinggi=nilai_tertinggi
    )

# ---
# Route untuk menghapus mahasiswa (tidak ada perubahan)
@app.route('/delete_mahasiswa/<int:id>', methods=['DELETE'])
def delete_mahasiswa(id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM mahasiswa WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return {'message': 'Mahasiswa berhasil dihapus'}, 200
    except Exception as e:
        conn.rollback()
        conn.close()
        return {'message': f'Gagal menghapus mahasiswa: {str(e)}'}, 500

if __name__ == '__main__':
    app.run(debug=True)