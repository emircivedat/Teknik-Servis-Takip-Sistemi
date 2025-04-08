
# Teknik Servis Takip Sistemi

Bu proje, teknik servis firmalarının müşteri ve cihaz takibini kolaylaştırmak için geliştirilmiş web tabanlı bir yönetim sistemidir.

## Özellikler

- 🔒 Kullanıcı yönetimi ve rol tabanlı yetkilendirme (admin/personel)
- 📝 Servis kayıtları oluşturma, görüntüleme ve düzenleme
- 🔍 Takip numarası ile hızlı arama
- 📊 Servis durumu takibi (Beklemede, Tamir Edildi, İptal Edildi)
- 📸 Resim ve video yükleme desteği
- 📱 Mobil uyumlu arayüz

## Kurulum

### Gereksinimler

```bash
pip install flask flask-sqlalchemy werkzeug
```

### Kurulum Adımları

1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/emircivedat/teknik-servis-takip-sistemi.git
   cd teknik-servis-takip-sistemi
   ```

2. Sanal ortam oluşturun (isteğe bağlı ama önerilir):
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. Gerekli paketleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

4. Uygulamayı çalıştırın:
   ```bash
   python app.py
   ```

5. Tarayıcınızda `http://127.0.0.1:5000` adresine gidin

## Kullanım

### İlk Giriş
- Varsayılan yönetici bilgileri:
  - Kullanıcı adı: `admin`
  - Şifre: `admin123`
  - **ÖNEMLİ:** Üretim ortamında bu şifreyi değiştirmeyi unutmayın!

### Servis Kaydı Oluşturma
1. Ana sayfadaki "Yeni Servis Kaydı" butonuna tıklayın
2. Müşteri bilgilerini ve şikayet detaylarını doldurun
3. İsterseniz resim/video ekleyin
4. Kaydet butonuna basın

### Servis Takibi
- Ana sayfadaki arama kutusundan takip numarası ile sorgulama yapabilirsiniz
- Servis durumlarını güncelleyebilir ve notlar ekleyebilirsiniz
- Tamamlanan servisler için ücret bilgisi girebilirsiniz

## Teknik Detaylar

### Veritabanı Yapısı
- SQLite veritabanı (varsayılan olarak `teknik_servis.db`)
- Temel tablolar: User, Service, Media

### Güvenlik
- Şifreler güvenli bir şekilde hash'lenerek saklanır
- Rol tabanlı erişim kontrolü
- Dosya yükleme güvenliği

### Klasör Yapısı
- `/static` - CSS, JS ve diğer statik dosyalar
- `/templates` - HTML şablonları
- `/uploads` - Yüklenen medya dosyaları (resimler ve videolar)

## requirements.txt İçeriği

```
Flask==2.0.1
Flask-SQLAlchemy==2.5.1
Werkzeug==2.0.1
```

## Geliştirme

Bu proje Flask web microframework kullanılarak geliştirilmiştir. Veritabanı işlemleri için SQLAlchemy ORM kullanılmıştır. Uygulamada kullanıcı yönetimi, servis kayıtları ve dosya yükleme işlemleri için kapsamlı bir yapı bulunmaktadır.

Katkıda bulunmak istiyorsanız, lütfen bir issue açın veya pull request gönderin.
