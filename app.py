from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import hmac
import secrets
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)

# Veritabanı bağlantısı oluşturma ve tabloların oluşturulması
def init_db():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Users tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        # Tarlalar tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tarlalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                size INTEGER NOT NULL,
                parcel_no TEXT NOT NULL,
                income INTEGER DEFAULT 0,
                expenses INTEGER DEFAULT 0,
                profit_loss INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Gelirler tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gelirler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                season TEXT NOT NULL,
                kategori TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                tarla_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

    try:
        cursor.execute('ALTER TABLE gelirler ADD COLUMN tarla_id INTEGER')
    except sqlite3.OperationalError:

        # Giderler tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS giderler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                season TEXT NOT NULL,
                kategori TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                tarla_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

    try:
        cursor.execute('ALTER TABLE giderler ADD COLUMN tarla_id INTEGER')
    except sqlite3.OperationalError:
        
        # İşlemler tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS islemler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tarla_id INTEGER NOT NULL,
                season TEXT NOT NULL,
                islem TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

    try:
        cursor.execute('ALTER TABLE islemler ADD COLUMN tarla_id INTEGER')
    except sqlite3.OperationalError:

        conn.commit()

def init_db():
    """Create the complete local schema for a clean installation."""
    schema = (
        '''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS tarlalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            size INTEGER NOT NULL,
            parcel_no TEXT NOT NULL,
            income REAL DEFAULT 0,
            expenses REAL DEFAULT 0,
            profit_loss REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS seasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(user_id, name),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS gelirler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            season TEXT NOT NULL,
            kategori TEXT NOT NULL,
            amount REAL NOT NULL,
            price REAL NOT NULL,
            tarla_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(tarla_id) REFERENCES tarlalar(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS giderler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            season TEXT NOT NULL,
            kategori TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            price REAL NOT NULL,
            tarla_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(tarla_id) REFERENCES tarlalar(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS islemler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tarla_id INTEGER NOT NULL,
            season TEXT NOT NULL,
            islem TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(tarla_id) REFERENCES tarlalar(id) ON DELETE CASCADE
        )''',
    )
    with sqlite3.connect('users.db') as conn:
        conn.execute('PRAGMA foreign_keys = ON')
        for statement in schema:
            conn.execute(statement)
        conn.commit()


@app.route('/')
def home():
    return redirect(url_for('index' if 'user_id' in session else 'login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username.strip() or len(password) < 8:
            flash('Kullanıcı adı gerekli ve şifre en az 8 karakter olmalıdır.', 'error')
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO users (username, password) VALUES (?, ?)',
                    (username.strip(), password_hash),
                )
                conn.commit()
                flash('Kayıt başarılı! Giriş sayfasına yönlendiriliyorsunuz.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Bu kullanıcı adı zaten alınmış. Lütfen farklı bir kullanıcı adı seçin.', 'error')
                return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username.strip(),))
            user = cursor.fetchone()
            stored_password = user[2] if user else ''
            is_hashed = stored_password.startswith(('scrypt:', 'pbkdf2:'))
            password_valid = (
                check_password_hash(stored_password, password)
                if is_hashed
                else hmac.compare_digest(stored_password, password)
            )
            if user and password_valid:
                if not is_hashed:
                    cursor.execute(
                        'UPDATE users SET password = ? WHERE id = ?',
                        (generate_password_hash(password), user[0]),
                    )
                    conn.commit()
                session['user_id'] = user[0]  # Kullanıcı ID'sini oturumda saklıyoruz
                session['username'] = user[1]
                flash('Giriş başarılı!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Kullanıcı adı veya şifre hatalı. Lütfen tekrar deneyin.', 'error')
                return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/index')
def index():
    if 'user_id' in session:
        return render_template('index.html', username=session['username'])
    else:
        flash('Lütfen önce giriş yapın.', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('login'))

@app.route('/tarla', methods=['GET'])
def tarla():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcıya ait aktif tarlaları getir
        cursor.execute('''
            SELECT id, name, size, parcel_no FROM tarlalar WHERE user_id = ?
        ''', (session['user_id'],))
        tarlalar = cursor.fetchall()

        # Kullanıcıya ait aktif tarlaların gelir, gider ve kar-zarar toplamlarını hesapla
        cursor.execute('''
            SELECT SUM(gelirler.price) 
            FROM gelirler
            INNER JOIN tarlalar ON gelirler.tarla_id = tarlalar.id
            WHERE tarlalar.user_id = ?
        ''', (session['user_id'],))
        toplam_gelir = cursor.fetchone()[0] or 0

        cursor.execute('''
            SELECT SUM(giderler.price) 
            FROM giderler
            INNER JOIN tarlalar ON giderler.tarla_id = tarlalar.id
            WHERE tarlalar.user_id = ?
        ''', (session['user_id'],))
        toplam_gider = cursor.fetchone()[0] or 0

        toplam_kar_zarar = toplam_gelir - toplam_gider

        # Sezon bilgilerini ve detaylarını tarlalara ekle
        tarla_sezon_detaylari = []
        for tarla in tarlalar:
            cursor.execute('''
                SELECT DISTINCT season 
                FROM gelirler 
                WHERE tarla_id = ? AND user_id = ?
                UNION
                SELECT DISTINCT season 
                FROM giderler 
                WHERE tarla_id = ? AND user_id = ?
            ''', (tarla[0], session['user_id'], tarla[0], session['user_id']))
            sezonlar = cursor.fetchall()

            sezon_detaylari = []
            for season in sezonlar:
                season_name = season[0]

                # Gelir ve gider detaylarını getir
                cursor.execute('''
                    SELECT kategori, amount, price 
                    FROM gelirler 
                    WHERE tarla_id = ? AND user_id = ? AND season = ?
                ''', (tarla[0], session['user_id'], season_name))
                gelirler = cursor.fetchall()

                cursor.execute('''
                    SELECT kategori, type, amount, price 
                    FROM giderler 
                    WHERE tarla_id = ? AND user_id = ? AND season = ?
                ''', (tarla[0], session['user_id'], season_name))
                giderler = cursor.fetchall()

                # Toplam gelir ve gider hesapla
                cursor.execute('''
                    SELECT SUM(price) 
                    FROM gelirler 
                    WHERE tarla_id = ? AND user_id = ? AND season = ?
                ''', (tarla[0], session['user_id'], season_name))
                toplam_sezon_gelir = cursor.fetchone()[0] or 0

                cursor.execute('''
                    SELECT SUM(price) 
                    FROM giderler 
                    WHERE tarla_id = ? AND user_id = ? AND season = ?
                ''', (tarla[0], session['user_id'], season_name))
                toplam_sezon_gider = cursor.fetchone()[0] or 0

                sezon_kar_zarar = toplam_sezon_gelir - toplam_sezon_gider

                sezon_detaylari.append({
                    'season_name': season_name,
                    'gelirler': gelirler,
                    'giderler': giderler,
                    'sezon_gelir': toplam_sezon_gelir,
                    'sezon_gider': toplam_sezon_gider,
                    'sezon_kar_zarar': sezon_kar_zarar
                })

            tarla_sezon_detaylari.append({
                'tarla': tarla,
                'sezonlar': sezon_detaylari
            })

    summary_data = {
        'total_fields': len(tarlalar),
        'total_income': toplam_gelir,
        'total_expenses': toplam_gider,
        'total_profit_loss': toplam_kar_zarar
    }

    return render_template(
        'tarla.html',
        tarlalar=tarlalar,
        summary=summary_data,
        tarla_sezon_detaylari=tarla_sezon_detaylari
    )





@app.route('/tarla_sil/<int:tarla_id>', methods=['POST'])
def tarla_sil(tarla_id):
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Tarla kontrolü
        cursor.execute('''
            SELECT id FROM tarlalar WHERE id = ? AND user_id = ?
        ''', (tarla_id, session['user_id']))
        tarla = cursor.fetchone()

        if not tarla:
            flash('Tarla bulunamadı!', 'error')
            return redirect(url_for('tarla'))

        # İlgili verileri sil
        cursor.execute('DELETE FROM gelirler WHERE tarla_id = ?', (tarla_id,))
        cursor.execute('DELETE FROM giderler WHERE tarla_id = ?', (tarla_id,))
        cursor.execute('DELETE FROM islemler WHERE tarla_id = ?', (tarla_id,))
        cursor.execute('DELETE FROM tarlalar WHERE id = ?', (tarla_id,))
        conn.commit()

    flash('Tarla ve ilişkili tüm veriler silindi.', 'success')
    return redirect(url_for('tarla'))




@app.route('/tarla_ekle', methods=['GET', 'POST'])
def tarla_ekle():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        field_name = request.form.get('field_name')
        field_size = request.form.get('field_size')
        parcel_no = request.form.get('parcel_no')

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tarlalar (user_id, name, size, parcel_no)
                VALUES (?, ?, ?, ?)
            ''', (session['user_id'], field_name, field_size, parcel_no))
            conn.commit()

        flash('Tarla başarıyla eklendi!', 'success')
        return redirect(url_for('tarla'))

    return render_template('tarla_ekle.html')


@app.route('/tarla/<int:tarla_id>')
def eklenen_tarla(tarla_id):
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Tarla bilgilerini al
        cursor.execute('''
            SELECT * FROM tarlalar WHERE id = ? AND user_id = ?
        ''', (tarla_id, session['user_id']))
        tarla = cursor.fetchone()

        if not tarla:
            flash('Tarla bulunamadı!', 'error')
            return redirect(url_for('tarla'))

        # Sezon bilgilerini al ve sıralı liste olarak getir
        cursor.execute('''
            SELECT DISTINCT season FROM gelirler WHERE tarla_id = ? AND user_id = ?
            UNION
            SELECT DISTINCT season FROM giderler WHERE tarla_id = ? AND user_id = ?
            ORDER BY season
        ''', (tarla_id, session['user_id'], tarla_id, session['user_id']))
        seasons = cursor.fetchall()

        # Her sezonun gelir, gider, kar-zarar ve Hasat Satışı hesaplarını yap
        season_details = []
        previous_hasat = None  # Önceki sezonun hasat miktarını saklayacak
        toplam_ilk_hasat = None  # İlk sezonun toplam hasat miktarı
        toplam_son_hasat = None  # Son sezonun toplam hasat miktarı
        for season in seasons:
            season_name = season[0]

            # Gelir
            cursor.execute('''
                SELECT SUM(price) FROM gelirler WHERE tarla_id = ? AND user_id = ? AND season = ?
            ''', (tarla_id, session['user_id'], season_name))
            season_income = cursor.fetchone()[0] or 0

            # Gider
            cursor.execute('''
                SELECT SUM(price) FROM giderler WHERE tarla_id = ? AND user_id = ? AND season = ?
            ''', (tarla_id, session['user_id'], season_name))
            season_expenses = cursor.fetchone()[0] or 0

            # Kar-Zarar
            season_profit_loss = season_income - season_expenses

            # Hasat Satışı miktarı
            cursor.execute('''
                SELECT SUM(amount) FROM gelirler 
                WHERE tarla_id = ? AND user_id = ? AND season = ? AND kategori = "Hasat Satışı"
            ''', (tarla_id, session['user_id'], season_name))
            hasat_satisi = cursor.fetchone()[0] or 0

            if toplam_ilk_hasat is None:  # İlk sezonun toplam hasat miktarını kaydet
                toplam_ilk_hasat = hasat_satisi

            toplam_son_hasat = hasat_satisi  # Her döngüde son sezonun toplam hasat miktarını güncelle

            # Verimlilik oranı
            verimlilik_orani = None
            if previous_hasat is not None and previous_hasat > 0:
                verimlilik_orani = round(((hasat_satisi - previous_hasat) / previous_hasat) * 100, 2)

            season_details.append({
                'season_name': season_name,
                'income': season_income,
                'expenses': season_expenses,
                'profit_loss': season_profit_loss,
                'hasat_satisi': hasat_satisi,
                'verimlilik_orani': verimlilik_orani
            })

            previous_hasat = hasat_satisi  # Mevcut sezonu bir sonraki sezon için referans yap

        # Toplam Verimlilik Oranı Hesaplama
        toplam_verimlilik_orani = None
        if toplam_ilk_hasat is not None and toplam_son_hasat is not None and toplam_ilk_hasat > 0:
            toplam_verimlilik_orani = round(((toplam_son_hasat - toplam_ilk_hasat) / toplam_ilk_hasat) * 100, 2)

    return render_template(
        'eklenen_tarla.html',
        tarla={
            'id': tarla[0],
            'name': tarla[2],
            'size': tarla[3],
            'parcel_no': tarla[4],
            'toplam_verimlilik_orani': toplam_verimlilik_orani
        },
        season_details=season_details
    )



@app.route('/season/<season_name>')
def season_view(season_name):
    tarla_id = request.args.get('tarla_id')

    if 'user_id' not in session or not tarla_id:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Gelirleri filtrele
        cursor.execute('''
            SELECT kategori, amount, price, id
            FROM gelirler
            WHERE user_id = ? AND season = ? AND tarla_id = ?
        ''', (session['user_id'], season_name, tarla_id))
        gelirler = cursor.fetchall()

        # Giderleri filtrele
        cursor.execute('''
            SELECT kategori, type, amount, price, id
            FROM giderler
            WHERE user_id = ? AND season = ? AND tarla_id = ?
        ''', (session['user_id'], season_name, tarla_id))
        giderler = cursor.fetchall()

        # Toplam gelir ve gider
        cursor.execute('''
            SELECT COALESCE(SUM(price), 0) 
            FROM gelirler 
            WHERE user_id = ? AND season = ? AND tarla_id = ?
        ''', (session['user_id'], season_name, tarla_id))
        toplam_gelir = cursor.fetchone()[0]


        cursor.execute('''
            SELECT COALESCE(SUM(price), 0) 
            FROM giderler 
            WHERE user_id = ? AND season = ? AND tarla_id = ?
        ''', (session['user_id'], season_name, tarla_id))
        toplam_gider = cursor.fetchone()[0]


        sezon_kar_zarar = toplam_gelir - toplam_gider

    return render_template(
        'sezon.html',
        season_name=season_name,
        gelirler=gelirler,
        giderler=giderler,
        toplam_gelir=toplam_gelir,
        toplam_gider=toplam_gider,
        sezon_kar_zarar=sezon_kar_zarar,
        tarla_id=tarla_id
    )



# Giderler
@app.route('/gider/tohum', methods=['GET', 'POST'])
def tohum_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')
    tarla_id = request.args.get('tarla_id')


    if request.method == 'POST':
        tohum_secimi = request.form.get('tohum_secimi')
        tohum_marka = request.form.get('tohum_marka')
        toplam_miktar = request.form.get('toplam_miktar')
        toplam_tutar = request.form.get('toplam_tutar')


        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, 'Tohum', f"{tohum_secimi} - {tohum_marka}", toplam_miktar, toplam_tutar, tarla_id))
            conn.commit()

        flash('Tohum gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('tohum-gider.html', season_name=season_name, tarla_id=tarla_id)



@app.route('/gider/gubre', methods=['GET', 'POST'])
def gubre_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        urun_grubu = request.form['urun_grubu']
        marka = request.form['marka']
        toplam_miktar = request.form['toplam_miktar']
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Gübre", f"{urun_grubu} - {marka}", toplam_miktar, toplam_tutar, tarla_id))
            conn.commit()

        flash('Gübre gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('gubre-gider.html', season_name=season_name, tarla_id=tarla_id)



@app.route('/gider/ilac', methods=['GET', 'POST'])
def ilac_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        urun_tipi = request.form['urun_tipi']
        marka = request.form['marka']
        toplam_miktar = request.form['toplam_miktar']
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "İlaç", f"{urun_tipi} - {marka}", toplam_miktar, toplam_tutar, tarla_id))
            conn.commit()

        flash('İlaç gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('ilac-gider.html', season_name=season_name, tarla_id=tarla_id)



@app.route('/gider/akaryakit', methods=['GET', 'POST'])
def akaryakit_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        akaryakit_tipi = request.form['akaryakit_tipi']
        toplam_miktar = request.form['toplam_miktar']
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Akaryakıt", akaryakit_tipi, toplam_miktar, toplam_tutar, tarla_id))
            conn.commit()

        flash('Akaryakıt gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('akaryakit-gider.html', season_name=season_name, tarla_id=tarla_id)



@app.route('/gider/elektrik', methods=['GET', 'POST'])
def elektrik_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')  # Sezon bilgisini al
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        # Kullanıcıdan gelen veriyi al
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            # Gider tablosuna veriyi ekle
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Elektrik", "Elektrik", 0, toplam_tutar, tarla_id))  # Miktar (amount) = 0
            conn.commit()

        flash('Elektrik gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('elektrik-gider.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gider/iscilik', methods=['GET', 'POST'])
def iscilik_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')  # Sezon bilgisini al
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        # Kullanıcıdan gelen veriyi al
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            # Gider tablosuna veriyi ekle
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "İşçilik", "İşçilik", 0, toplam_tutar, tarla_id))  # Miktar (amount) = 0
            conn.commit()

        flash('İşçilik gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('iscilik-gider.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gider/nakliye', methods=['GET', 'POST'])
def nakliye_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')  # Sezon bilgisini al
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        # Kullanıcıdan gelen verileri al
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            # Gider tablosuna verileri ekle
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Nakliye", "Nakliye", 0, toplam_tutar, tarla_id))
            conn.commit()

        flash('Nakliye gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('nakliye-gider.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gider/kredi', methods=['GET', 'POST'])
def kredi_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')  # Sezon bilgisini al
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        # Kullanıcıdan gelen veriyi al
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            # Gider tablosuna veriyi ekle
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Kredi", "Kredi", 0, toplam_tutar, tarla_id))  # Miktar (amount) = 0
            conn.commit()

        flash('Kredi gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('kredi-gider.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gider/sigorta', methods=['GET', 'POST'])
def sigorta_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')  # Sezon bilgisini al
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        # Kullanıcıdan gelen veriyi al
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            # Gider tablosuna veriyi ekle
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Sigorta", "Sigorta", 0, toplam_tutar, tarla_id))  # Miktar (amount) = 0
            conn.commit()

        flash('Sigorta gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('sigorta-gider.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gider/tarla-kirasi', methods=['GET', 'POST'])
def tarla_kirasi_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')  # Sezon bilgisini al
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        # Kullanıcıdan gelen veriyi al
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            # Gider tablosuna veriyi ekle
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Tarla Kirası", "Tarla Kirası", 0, toplam_tutar, tarla_id))  # Miktar (amount) = 0
            conn.commit()

        flash('Tarla kirası gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('tarla-kirasi-gider.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gider/bicim', methods=['GET', 'POST'])
def bicim_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')  # Sezon bilgisini al
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        # Kullanıcıdan gelen veriyi al
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            # Gider tablosuna veriyi ekle
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Biçim", "Biçim", 0, toplam_tutar, tarla_id))  # Miktar (amount) = 0
            conn.commit()

        flash('Biçim gideri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('bicim-gider.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gider/diger', methods=['GET', 'POST'])
def diger_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')  # Sezon bilgisini al
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        # Kullanıcıdan gelen veriyi al
        toplam_tutar = request.form['toplam_tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            # Gider tablosuna veriyi ekle
            cursor.execute('''
                INSERT INTO giderler (user_id, season, kategori, type, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Diğer", "Diğer", 0, toplam_tutar, tarla_id))  # Miktar (amount) = 0
            conn.commit()

        flash('Diğer gider başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('diger-gider.html', season_name=season_name, tarla_id=tarla_id)


# Gelirler
@app.route('/gelir/hasat', methods=['GET', 'POST'])
def hasat_gelir():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        miktar = request.form['miktar']
        tutar = request.form['tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO gelirler (user_id, season, kategori, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Hasat Satışı", miktar, tutar, tarla_id))
            conn.commit()

        flash('Hasat geliri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('hasat-gelir.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gelir/hibe', methods=['GET', 'POST'])
def hibe_gelir():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        tutar = request.form['tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO gelirler (user_id, season, kategori, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Hibe", 0, tutar, tarla_id))
            conn.commit()

        flash('Hibe geliri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('hibe-gelir.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gelir/diger', methods=['GET', 'POST'])
def diger_gelir():
    if 'user_id' not in session:
        flash('Lütfen giriş yapınız!', 'error')
        return redirect(url_for('login'))

    season_name = request.args.get('season')
    tarla_id = request.args.get('tarla_id')

    if request.method == 'POST':
        tutar = request.form['tutar']

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO gelirler (user_id, season, kategori, amount, price, tarla_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], season_name, "Diğer", 0, tutar, tarla_id))  # Miktar = 0
            conn.commit()

        flash('Diğer geliri başarıyla kaydedildi!', 'success')
        return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

    return render_template('diger-gelir.html', season_name=season_name, tarla_id=tarla_id)


@app.route('/gelir_sil/<int:gelir_id>', methods=['POST'])
def gelir_sil(gelir_id):
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    # Parametreleri URL'den al
    season_name = request.args.get('season')
    tarla_id = request.args.get('tarla_id')

    if not season_name or not tarla_id:
        flash('Sezon veya tarla bilgisi eksik!', 'error')
        return redirect(url_for('tarla'))

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM gelirler WHERE id = ? AND user_id = ?
        ''', (gelir_id, session['user_id']))
        conn.commit()

    flash('Gelir başarıyla silindi!', 'success')
    return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))



@app.route('/gider_sil/<int:gider_id>', methods=['POST'])
def gider_sil(gider_id):
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    # Parametreleri URL'den al
    season_name = request.args.get('season')
    tarla_id = request.args.get('tarla_id')

    if not season_name or not tarla_id:
        flash('Sezon veya tarla bilgisi eksik!', 'error')
        return redirect(url_for('tarla'))

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM giderler WHERE id = ? AND user_id = ?
        ''', (gider_id, session['user_id']))
        conn.commit()

    flash('Gider başarıyla silindi!', 'success')
    return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))



@app.route('/islemler/<season_name>/<int:tarla_id>', methods=['GET', 'POST'])
def islemler(season_name, tarla_id):
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        if request.method == 'POST':
            selected_islemler = []
            akaryakit_verileri = []

            # Checkbox ve Akaryakıt verilerini eşleştirerek al
            for i in range(1, 9):  # 8 işlem için örnek; gerekirse artırabilirsiniz
                islem = request.form.get(f'islemler_{i}')
                akaryakit_tipi = request.form.get(f'akaryakit_tipi_{i}')
                toplam_miktar = request.form.get(f'toplam_miktar_{i}')
                toplam_tutar = request.form.get(f'toplam_tutar_{i}')

                if islem:  # Sadece işaretli checkbox'ları işler
                    selected_islemler.append(islem)
                    if akaryakit_tipi or toplam_miktar or toplam_tutar:
                        if not (akaryakit_tipi and toplam_miktar and toplam_tutar):
                            flash('Eksik Akaryakıt bilgisi girdiniz!', 'error')
                            return redirect(url_for('islemler', season_name=season_name, tarla_id=tarla_id))
                        akaryakit_verileri.append({
                            'kategori': 'Akaryakıt',
                            'type': akaryakit_tipi,
                            'amount': toplam_miktar,
                            'price': toplam_tutar
                        })

            # Eski işlemleri sil
            cursor.execute('''
                DELETE FROM islemler WHERE user_id = ? AND tarla_id = ? AND season = ?
            ''', (session['user_id'], tarla_id, season_name))

            # Yeni işlemleri kaydet
            for islem in selected_islemler:
                cursor.execute('''
                    INSERT INTO islemler (user_id, tarla_id, season, islem)
                    VALUES (?, ?, ?, ?)
                ''', (session['user_id'], tarla_id, season_name, islem))

            # Akaryakıt verilerini kaydet
            for veri in akaryakit_verileri:
                cursor.execute('''
                    INSERT INTO giderler (user_id, tarla_id, season, kategori, type, amount, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (session['user_id'], tarla_id, season_name, veri['kategori'], veri['type'], veri['amount'], veri['price']))

            conn.commit()
            flash('Yapılan işlemler ve Akaryakıt detayları kaydedildi!', 'success')

            return redirect(url_for('season_view', season_name=season_name, tarla_id=tarla_id))

        # Önceki işlemleri getir
        cursor.execute('''
            SELECT islem FROM islemler WHERE user_id = ? AND tarla_id = ? AND season = ?
        ''', (session['user_id'], tarla_id, season_name))
        islemler = [row[0] for row in cursor.fetchall()]

    return render_template('islemler.html', season_name=season_name, tarla_id=tarla_id, islemler=islemler)




# Hızlı Menu Butonları

@app.route('/hizli_menu_tohum', methods=['GET', 'POST'])
def hizli_menu_tohum():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_tohum'))

        # Doğru URL formatında yönlendirme sağlamak için
        return redirect(url_for('tohum_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_tohum.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_gubre', methods=['GET', 'POST'])
def hizli_menu_gubre():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_gubre'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('gubre_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_gubre.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_ilac', methods=['GET', 'POST'])
def hizli_menu_ilac():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_ilac'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('ilac_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_ilac.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_akaryakit', methods=['GET', 'POST'])
def hizli_menu_akaryakit():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_akaryakit'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('akaryakit_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_akaryakit.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_elektrik', methods=['GET', 'POST'])
def hizli_menu_elektrik():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_elektrik'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('elektrik_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_elektrik.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_iscilik', methods=['GET', 'POST'])
def hizli_menu_iscilik():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_iscilik'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('iscilik_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_iscilik.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_nakliye', methods=['GET', 'POST'])
def hizli_menu_nakliye():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_nakliye'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('nakliye_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_nakliye.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_kredi', methods=['GET', 'POST'])
def hizli_menu_kredi():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_kredi'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('kredi_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_kredi.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_sigorta', methods=['GET', 'POST'])
def hizli_menu_sigorta():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_sigorta'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('sigorta_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_sigorta.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_tarla_kirasi', methods=['GET', 'POST'])
def hizli_menu_tarla_kirasi():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_tarla_kirasi'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('tarla_kirasi_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_tarla_kirasi.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_bicim', methods=['GET', 'POST'])
def hizli_menu_bicim():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_bicim'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('bicim_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_bicim.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_diger_gider', methods=['GET', 'POST'])
def hizli_menu_diger_gider():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_diger'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('diger_gider', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_diger_gider.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_hasat', methods=['GET', 'POST'])
def hizli_menu_hasat():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_hasat'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('hasat_gelir', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_hasat.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_hibe', methods=['GET', 'POST'])
def hizli_menu_hibe():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_hibe'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('hibe_gelir', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_hibe.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_diger_gelir', methods=['GET', 'POST'])
def hizli_menu_diger_gelir():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_diger_gelir'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('diger_gelir', tarla_id=tarla_id, season=season_name))

    return render_template('hizli_menu_diger_gelir.html', tarlalar=tarlalar, sezonlar=sezonlar)


@app.route('/hizli_menu_islemler', methods=['GET', 'POST'])
def hizli_menu_islemler():
    if 'user_id' not in session:
        flash('Lütfen giriş yapın!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Kullanıcının eklediği tarlaları al
        cursor.execute('''
            SELECT id, name FROM tarlalar WHERE user_id = ?
        ''', (user_id,))
        tarlalar = cursor.fetchall()

        # Sabit sezonlar
        sezonlar = [('2024-2025',), ('2025-2026',), ('2026-2027',)]

    if request.method == 'POST':
        tarla_id = request.form.get('tarla_id')
        season_name = request.form.get('season_name')

        if not tarla_id or not season_name:
            flash('Lütfen bir tarla ve sezon seçin!', 'error')
            return redirect(url_for('hizli_menu_islemler'))

        # Doğru URL formatında yönlendirme
        return redirect(url_for('islemler', season_name=season_name, tarla_id=tarla_id))

    return render_template('hizli_menu_islemler.html', tarlalar=tarlalar, sezonlar=sezonlar)



if __name__ == '__main__':
    init_db()  # Veritabanını başlat
    app.run(debug=True, port=5500)
