from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models import db, Category, Subcategory, Document

# ฟังก์ชันตรวจสอบสิทธิ์ผู้ใช้ admin
def is_admin():
    return current_user.role == 'admin'

# หน้าแสดงและจัดการ Categories
@app.route('/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    if not is_admin():
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        category_name = request.form['category_name']
        
        # ตรวจสอบว่า category_name ซ้ำหรือไม่
        if Category.query.filter_by(name=category_name).first():
            flash(f"Category '{category_name}' already exists.", "danger")
        else:
            new_category = Category(name=category_name)
            db.session.add(new_category)
            db.session.commit()
            flash(f"Category '{category_name}' created successfully", "success")
    
    categories = Category.query.all()
    return render_template('manage_categories.html', categories=categories)

# หน้าแสดงและจัดการ Subcategories
@app.route('/subcategories', methods=['GET', 'POST'])
@login_required
def manage_subcategories():
    if not is_admin():
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        subcategory_name = request.form['subcategory_name']
        category_id = request.form['category_id']
        
        # ตรวจสอบว่า subcategory_name ซ้ำหรือไม่ใน category เดียวกัน
        if Subcategory.query.filter_by(name=subcategory_name, category_id=category_id).first():
            flash(f"Subcategory '{subcategory_name}' already exists in this category.", "danger")
        else:
            new_subcategory = Subcategory(name=subcategory_name, category_id=category_id)
            db.session.add(new_subcategory)
            db.session.commit()
            flash(f"Subcategory '{subcategory_name}' created successfully", "success")
    
    categories = Category.query.all()
    subcategories = Subcategory.query.all()
    return render_template('manage_subcategories.html', categories=categories, subcategories=subcategories)

# หน้า Home สำหรับผู้ใช้ทั่วไปและ Admin
@app.route('/')
@login_required
def home():
    if is_admin():
        # ค้นหาผู้ใช้งานที่เป็น Admin และเอกสารที่มีสถานะ Pending
        documents = Document.query.filter_by(status='Pending').all()
    else:
        documents = Document.query.filter_by(user_id=current_user.id).all()  # สำหรับผู้ใช้ทั่วไป
    return render_template("home.html", documents=documents)
