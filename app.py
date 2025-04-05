from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from azure.storage.blob import BlobServiceClient
from config import Config
import uuid

app = Flask(__name__)
app.config.from_object(Config)

# ตั้งค่า Database
db = SQLAlchemy(app)

# ตั้งค่า Login Manager
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ตั้งค่า Azure Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(app.config['AZURE_STORAGE_CONNECTION_STRING'])

# โมเดล User
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')  # เพิ่ม role

# โมเดล Documents
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # Pending, Approved, Rejected
    category = db.Column(db.String(100), nullable=False)
    sub_category = db.Column(db.String(100), nullable=False)

# โมเดล Categories
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    subcategories = db.relationship('Subcategory', backref='category', lazy=True)

# โมเดล Subcategories
class Subcategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)    

# โหลดข้อมูลผู้ใช้เมื่อเข้าสู่ระบบ
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# หน้า Homepage
@app.route('/')
def index():
    return redirect(url_for('login'))

# หน้า Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            # ทุกคนที่ล็อกอินสำเร็จจะถูกเปลี่ยนเส้นทางไปที่หน้า dashboard
            return redirect(url_for('dashboard'))  # เปลี่ยนเส้นทางไปหน้า dashboard

        else:
            flash("Login failed. Check your username and/or password.", "danger")
    
    return render_template('login.html')

# หน้า Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        # ตรวจสอบว่ามีผู้ใช้ที่ใช้ชื่อเดียวกันหรือไม่
        user = User.query.filter_by(username=username).first()
        if user:
            flash("Username already exists. Please choose a different username.", "danger")
            return redirect(url_for('register'))
        
        # แปลงรหัสผ่านให้เป็น hash โดยใช้ pbkdf2:sha256
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # สร้างผู้ใช้ใหม่
        new_user = User(username=username, password=hashed_password, role=role)
        
        # บันทึกในฐานข้อมูล
        db.session.add(new_user)
        db.session.commit()
        
        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for('login'))
    
    return render_template('register.html')

# หน้า Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# หน้า Dashboard (แสดงรายการเอกสาร)
@app.route('/dashboard')
@login_required
def dashboard():
    # สำหรับทุกคน (ไม่จำกัดแค่เอกสารของ user ปัจจุบัน)
    documents = Document.query.all()  # แสดงเอกสารทั้งหมด
    return render_template("dashboard.html", documents=documents)

# หน้า Upload Document
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']
        category = request.form['category']
        sub_category = request.form['sub_category']
        status = 'Pending'
        
        # Upload to Azure Blob Storage
        container_name = "documents"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.filename)
        blob_client.upload_blob(file)

        # บันทึกข้อมูลใน Database
        document = Document(user_id=current_user.id, file_name=file.filename, file_path=file.filename, 
                            status=status, category=category, sub_category=sub_category)
        db.session.add(document)
        db.session.commit()

        unique_filename = str(uuid.uuid4()) + "_" + file.filename
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=unique_filename)

        flash("Document uploaded successfully", "success")
        return redirect(url_for('dashboard'))
    
    return render_template('upload.html')

# หน้า Download Document
@app.route('/download_document/<int:document_id>')
@login_required
def download_document(document_id):
    # ดึงข้อมูลเอกสารจากฐานข้อมูล
    document = Document.query.get_or_404(document_id)

    # ตรวจสอบสถานะเอกสารว่ามีสถานะเป็น "Approved" หรือไม่
    if document.status != 'Approved':
        flash("You cannot download a document that is not approved.", "danger")
        return redirect(url_for('dashboard'))

    # เชื่อมต่อกับ Azure Blob Storage
    container_name = "documents"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=document.file_name)

    # ดาวน์โหลดไฟล์จาก Blob Storage
    download_stream = blob_client.download_blob()

    # ส่งไฟล์ไปยังผู้ใช้
    return download_stream.readall(), 200, {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': f'attachment; filename={document.file_name}'
    }



# อัปเดตสถานะเอกสาร (สำหรับ Admin)
@app.route('/approve_document/<int:document_id>', methods=['POST'])
@login_required
def approve_document(document_id):
    if not current_user.role == 'admin':
        flash("You do not have permission to approve this document.", "danger")
        return redirect(url_for('dashboard'))
    
    document = Document.query.get_or_404(document_id)
    document.status = 'Approved'
    db.session.commit()
    flash("Document approved successfully", "success")  # เพิ่มข้อความแจ้งเตือนว่าอนุมัติเอกสารแล้ว
    return redirect(url_for('dashboard'))  # เปลี่ยนเส้นทางไปที่ dashboard

@app.route('/reject_document/<int:document_id>', methods=['POST'])
@login_required
def reject_document(document_id):
    if not current_user.role == 'admin':
        flash("You do not have permission to reject this document.", "danger")
        return redirect(url_for('dashboard'))
    
    document = Document.query.get_or_404(document_id)
    document.status = 'Rejected'
    db.session.commit()
    flash("Document rejected successfully", "danger")  # เพิ่มข้อความแจ้งเตือนว่าเอกสารถูกปฏิเสธแล้ว
    return redirect(url_for('dashboard'))  # เปลี่ยนเส้นทางไปที่ dashboard


# กำหนดโมเดลต่าง ๆ ที่นี่...

if __name__ == '__main__':
    with app.app_context():  # เริ่มต้น application context
        db.create_all()  # สร้างตารางในฐานข้อมูล
        app.run(host='0.0.0.0', port=8000)
