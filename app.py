from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
import uuid
import functools
import re

# Flask uygulamasını oluştur
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teknik_servis.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Oturum süresi

# Upload klasörünü oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'images'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'videos'), exist_ok=True)

# İzin verilen dosya uzantıları
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}

# Veritabanı bağlantısı
db = SQLAlchemy(app)


# Jinja2 için "now" değişkenini global olarak tanımla
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


# Kullanıcı modeli
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='personel')  # admin, personel
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        # 'pbkdf2:sha256' metodunu kullanarak sorunu çözelim
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Medya dosyaları için model


class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # image veya video
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)


# Servis kaydı için model
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tracking_number = db.Column(db.String(20), unique=True, nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    customer_complaint = db.Column(db.Text, nullable=False)
    service_note = db.Column(db.Text)
    repair_description = db.Column(db.Text)
    requested_amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='Beklemede')  # Beklemede, Tamir Edildi, İptal Edildi
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    # İlişkiler
    media = db.relationship('Media', backref='service', lazy=True, cascade="all, delete-orphan")
    creator = db.relationship('User', backref='services')


# Login gerektiğinde kullanılacak decorator
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login', next=request.url))
        return view(**kwargs)

    return wrapped_view


# Admin yetkisi kontrolü
def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login', next=request.url))

        user = User.query.get(session['user_id'])
        if user.role != 'admin':
            flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'danger')
            return redirect(url_for('index'))

        return view(**kwargs)

    return wrapped_view


# Dosya uzantısı kontrolü
def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def allowed_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


# Takip numarası oluşturma - UPDATED
def generate_tracking_number():
    # En son kaydı al
    last_service = Service.query.order_by(Service.id.desc()).first()

    if last_service and last_service.tracking_number.startswith('TS-'):
        # Son kaydın numarasından sayıyı çıkar
        match = re.search(r'TS-(\d+)', last_service.tracking_number)
        if match:
            last_number = int(match.group(1))
            new_number = last_number + 1
        else:
            # Eğer düzgün formatta değilse 1'den başla
            new_number = 1
    else:
        # Hiç kayıt yoksa 1'den başla
        new_number = 1

        # 5 basamaklı formatta TS-00001 şeklinde döndür
    return f"TS-{new_number:05d}"


# Login sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next', '')

    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session.permanent = True

            user.last_login = datetime.utcnow()
            db.session.commit()

            flash(f'Hoş geldiniz, {user.name or user.username}!', 'success')

            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))

        flash('Kullanıcı adı veya şifre hatalı.', 'danger')

    return render_template('login.html', next=next_page)


# Çıkış yapma
@app.route('/logout')
def logout():
    session.clear()
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('login'))


# Profil sayfası
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        if 'current_password' in request.form and request.form['current_password']:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if not user.check_password(current_password):
                flash('Mevcut şifreniz hatalı.', 'danger')
            elif new_password != confirm_password:
                flash('Yeni şifreler eşleşmiyor.', 'danger')
            elif len(new_password) < 6:
                flash('Şifre en az 6 karakter olmalıdır.', 'danger')
            else:
                user.set_password(new_password)
                flash('Şifreniz başarıyla güncellendi.', 'success')

        user.name = request.form['name']
        db.session.commit()
        flash('Profil bilgileriniz güncellendi.', 'success')

    return render_template('profile.html', user=user)


# Kullanıcı yönetimi sayfası (sadece admin)
@app.route('/users')
@admin_required
def list_users():
    users = User.query.all()
    return render_template('users.html', users=users)


# Yeni kullanıcı ekleme (sadece admin)
@app.route('/users/new', methods=['GET', 'POST'])
@admin_required
def new_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        role = request.form['role']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Bu kullanıcı adı zaten kullanılıyor.', 'danger')
            return render_template('new_user.html')

        if len(password) < 6:
            flash('Şifre en az 6 karakter olmalıdır.', 'danger')
            return render_template('new_user.html')

        user = User(username=username, name=name, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Kullanıcı başarıyla oluşturuldu.', 'success')
        return redirect(url_for('list_users'))

    return render_template('new_user.html')


# Kullanıcı düzenleme (sadece admin)
@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']

        user.name = name
        user.role = role

        if 'password' in request.form and request.form['password']:
            password = request.form['password']
            if len(password) < 6:
                flash('Şifre en az 6 karakter olmalıdır.', 'danger')
                return render_template('edit_user.html', user=user)

            user.set_password(password)

        db.session.commit()
        flash('Kullanıcı bilgileri güncellendi.', 'success')
        return redirect(url_for('list_users'))

    return render_template('edit_user.html', user=user)


# Kullanıcı silme (sadece admin)
@app.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session['user_id']:
        flash('Kendinizi silemezsiniz.', 'danger')
        return redirect(url_for('list_users'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    flash('Kullanıcı silindi.', 'success')
    return redirect(url_for('list_users'))


# Ana sayfa - tüm servis kayıtlarını listele
@app.route('/')
@login_required
def index():
    services = Service.query.order_by(Service.created_at.desc()).all()
    return render_template('index.html', services=services)


# Yeni servis kaydı oluşturma
@app.route('/service/new', methods=['GET', 'POST'])
@login_required
def new_service():
    if request.method == 'POST':
        company_name = request.form['company_name']
        customer_complaint = request.form['customer_complaint']

        # Yeni servis kaydı oluştur
        service = Service(
            tracking_number=generate_tracking_number(),
            company_name=company_name,
            customer_complaint=customer_complaint,
            created_by=session['user_id']
        )

        db.session.add(service)
        db.session.commit()

        # Dosya yükleme işlemleri
        if 'images' in request.files:
            images = request.files.getlist('images')
            for image in images:
                if image and image.filename != '' and allowed_image(image.filename):
                    filename = secure_filename(image.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], 'images', unique_filename))

                    # Veritabanına kaydet
                    media = Media(
                        filename=unique_filename,
                        file_type='image',
                        service_id=service.id
                    )
                    db.session.add(media)

        if 'videos' in request.files:
            videos = request.files.getlist('videos')
            for video in videos:
                if video and video.filename != '' and allowed_video(video.filename):
                    filename = secure_filename(video.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    video.save(os.path.join(app.config['UPLOAD_FOLDER'], 'videos', unique_filename))

                    # Veritabanına kaydet
                    media = Media(
                        filename=unique_filename,
                        file_type='video',
                        service_id=service.id
                    )
                    db.session.add(media)

        db.session.commit()
        flash('Servis kaydı başarıyla oluşturuldu.', 'success')
        return redirect(url_for('view_service', service_id=service.id))

    return render_template('new_service.html')


# Servis kaydı detayı
@app.route('/service/<int:service_id>')
@login_required
def view_service(service_id):
    service = Service.query.get_or_404(service_id)
    return render_template('view_service.html', service=service)


# Servis kaydını güncelleme - UPDATED with fixes
@app.route('/service/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)

    if request.method == 'POST':
        service.company_name = request.form['company_name']
        service.customer_complaint = request.form['customer_complaint']
        service.service_note = request.form.get('service_note', '')
        service.repair_description = request.form.get('repair_description', '')
        service.status = request.form['status']

        # Properly handle the requested_amount field
        requested_amount = request.form.get('requested_amount', '').strip()
        if requested_amount:
            try:
                service.requested_amount = float(requested_amount)
            except ValueError:
                flash('Talep edilen miktar geçerli bir sayı olmalıdır.', 'danger')
                return render_template('edit_service.html', service=service)
        else:
            # If the field is empty or contains only whitespace, set to None
            service.requested_amount = None

            # Dosya yükleme işlemleri - Images
        if 'images' in request.files:
            images = request.files.getlist('images')
            for image in images:
                # Check if there's actually a file with content
                if image and image.filename and image.filename.strip() != '' and allowed_image(image.filename):
                    filename = secure_filename(image.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], 'images', unique_filename))

                    # Veritabanına kaydet
                    media = Media(
                        filename=unique_filename,
                        file_type='image',
                        service_id=service.id
                    )
                    db.session.add(media)

                    # Dosya yükleme işlemleri - Videos
        if 'videos' in request.files:
            videos = request.files.getlist('videos')
            for video in videos:
                # Check if there's actually a file with content
                if video and video.filename and video.filename.strip() != '' and allowed_video(video.filename):
                    filename = secure_filename(video.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    video.save(os.path.join(app.config['UPLOAD_FOLDER'], 'videos', unique_filename))

                    # Veritabanına kaydet
                    media = Media(
                        filename=unique_filename,
                        file_type='video',
                        service_id=service.id
                    )
                    db.session.add(media)

        db.session.commit()
        flash('Servis kaydı başarıyla güncellendi.', 'success')
        return redirect(url_for('view_service', service_id=service.id))

    return render_template('edit_service.html', service=service)


# Medya dosyasını silme
@app.route('/media/<int:media_id>/delete', methods=['POST'])
@login_required
def delete_media(media_id):
    media = Media.query.get_or_404(media_id)
    service_id = media.service_id

    # Dosyayı diskten sil
    file_path = os.path.join(app.config['UPLOAD_FOLDER'],
                             'images' if media.file_type == 'image' else 'videos',
                             media.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

        # Veritabanından sil
    db.session.delete(media)
    db.session.commit()

    flash('Medya dosyası başarıyla silindi.', 'success')
    return redirect(url_for('edit_service', service_id=service_id))


# Servis kaydını silme
@app.route('/service/<int:service_id>/delete', methods=['POST'])
@login_required
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)

    # Önce ilişkili medya dosyalarını diskten sil
    for media in service.media:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                 'images' if media.file_type == 'image' else 'videos',
                                 media.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

            # Servis kaydını veritabanından sil (ilişkili medya kayıtları da cascade ile silinecek)
    db.session.delete(service)
    db.session.commit()

    flash('Servis kaydı başarıyla silindi.', 'success')
    return redirect(url_for('index'))


# Takip numarası ile arama
@app.route('/search', methods=['GET'])
@login_required
def search():
    tracking_number = request.args.get('tracking_number', '')
    service = Service.query.filter_by(tracking_number=tracking_number).first()

    if service:
        return redirect(url_for('view_service', service_id=service.id))
    else:
        flash('Belirtilen takip numarasına sahip servis kaydı bulunamadı.', 'danger')
        return redirect(url_for('index'))

        # Medya dosyalarını servis etme


@app.route('/uploads/<folder>/<filename>')
@login_required
def uploaded_file(folder, filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], folder), filename)


# HTML Şablonları için Jinja2 filtreleri
@app.template_filter('format_date')
def format_date(date):
    if date:
        return date.strftime('%d.%m.%Y %H:%M')
    return ''


# Uygulamayı başlat
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Veritabanı tablolarını oluştur

        # Admin kullanıcısı oluştur (eğer yoksa)
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', name='Admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Admin kullanıcısı oluşturuldu. Kullanıcı adı: admin, Şifre: admin123')

    # Port'u çevresel değişkenden oku, yoksa 5000 kullan
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)