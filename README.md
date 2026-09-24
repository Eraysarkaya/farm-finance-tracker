# Farm Finance Tracker

Çiftçilerin farklı tarlalara ait gelir ve giderleri sezonlara göre kaydedip hangi tarladan ne kadar kâr veya zarar ettiklerini görebilmeleri için geliştirilmiş web uygulaması. Flask ve SQLite kullanan bu öğrenme projesinde her kullanıcı yalnız kendi tarla kayıtlarını yönetir.

## Özellikler

- Hesap oluşturma ve oturum açma
- Tarla, parsel ve sezon kayıtları
- Hasat, destek, yakıt, gübre, tohum ve diğer gelir/gider kalemleri
- Tarla bazında ve genel kâr/zarar özeti
- Kullanıcıların yalnız kendi tarlalarını değiştirebilmesi

**Teknolojiler:** Python, Flask, SQLite.

## Ekran görüntüleri

| Tarla özeti | Tarla detayları | Yeni kayıt |
| --- | --- | --- |
| ![Tarla özeti](docs/screenshots/01-field-summary.png) | ![Tarla detayları](docs/screenshots/02-field-details.png) | ![Yeni kayıt](docs/screenshots/03-new-entry.png) |

## Yerel kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows'ta sanal ortamı `.venv\Scripts\activate` ile açın. Oturum anahtarını `FLASK_SECRET_KEY` ortam değişkenine atayıp `python app.py` çalıştırın. PowerShell örneği:

```powershell
$env:FLASK_SECRET_KEY='yerel-ortam-icin-rastgele-bir-anahtar'
python app.py
```

Uygulama: `http://127.0.0.1:5500`. Veritabanı ilk çalıştırmada oluşturulur. Testler: `python -m unittest discover -s tests -v`.

**Durum:** Arayüz, ilk ders projesindeki yapıyı koruyor. Kimlik doğrulama ve kurulum daha sonra iyileştirildi; bazı kategori işlemlerinde yinelenen kod bulunuyor.

## Lisans

MIT.
