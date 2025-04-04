from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from azure.storage.blob import BlobServiceClient

app = Flask(__name__)
app.config.from_object('config.Config')

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
@login_required
def home():
    return render_template("home.html")

# หน้า Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash("Login failed. Check your username and/or password.", "danger")
    
    return render_template('login.html')

# หน้า Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

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

        flash("Document uploaded successfully", "success")
        return redirect(url_for('home'))
    
    return render_template('upload.html')

# ฟังก์ชันการค้นหาเอกสาร
@app.route('/search', methods=['GET'])
@login_required
def search():
    category = request.args.get('category', '')
    sub_category = request.args.get('sub_category', '')
    
    # การกรองแบบยืดหยุ่น
    query = Document.query
    if category:
        query = query.filter_by(category=category)
    if sub_category:
        query = query.filter_by(sub_category=sub_category)
    
    documents = query.all()
    return render_template('search_results.html', documents=documents)

# อัปเดตสถานะเอกสาร (สำหรับ Admin)
@app.route('/approve_document/<int:document_id>', methods=['POST'])
@login_required
def approve_document(document_id):
    if not current_user.role == 'admin':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('home'))
    
    document = Document.query.get_or_404(document_id)
    document.status = 'Approved'
    db.session.commit()
    flash("Document approved successfully", "success")
    return redirect(url_for('home'))

@app.route('/reject_document/<int:document_id>', methods=['POST'])
@login_required
def reject_document(document_id):
    if not current_user.role == 'admin':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('home'))
    
    document = Document.query.get_or_404(document_id)
    document.status = 'Rejected'
    db.session.commit()
    flash("Document rejected successfully", "danger")
    return redirect(url_for('home'))

if __name__ == '__main__':
    db.create_all()  # สร้างตารางในฐานข้อมูล
    app.run(debug=True)
