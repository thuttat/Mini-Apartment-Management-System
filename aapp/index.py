from datetime import datetime, timedelta

import cloudinary.uploader
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from aapp import app, dao, login, utils, db
from aapp.models import UserRole, ApartmentStatus, ContractStatus, Rule, RuleKey
from aapp.utils import get_tenant_context, hash_password


@app.context_processor
def inject_rules():
    return dict(global_rules=dao.get_all_rules_as_dict())


@app.route('/')
def index():
    req_status = request.args.get('status')
    status_filter = req_status if req_status else [
        ApartmentStatus.AVAILABLE,
        ApartmentStatus.LOOKING_FOR_ROOMMATE
    ]

    apartments = dao.load_apartments(
        room_type=request.args.get('room_type'),
        status=status_filter,
        min_price=request.args.get('min_price'),
        max_price=request.args.get('max_price'),
        keyword=request.args.get('keyword')
    )
    return render_template('index.html', apartments=apartments)

@app.route('/login')
def login_view():
    return render_template('login.html')

@app.route('/register')
def register_view():
    return render_template('register.html')

@app.route('/login', methods=['post'])
def login_process():
    username = request.form.get("username")
    password = request.form.get("password")

    user, role = dao.auth_user(username, password)
    if user:
        login_user(user)
        if role == UserRole.MANAGER:
            return redirect('/admin')
        elif role == UserRole.TENANT:
            return redirect('/tenant/index')
        elif role == UserRole.TECHNICIAN:
            return redirect('/technician/index')

    return render_template('login.html', err_msg="Wrong password or username")


@app.route('/register', methods=['post'])
def register_process():
    password = request.form.get('password')
    confirm = request.form.get('confirm')
    if password != confirm:
        err_msg = 'WRONG PASSWORD!'
        return render_template('register.html', err_msg=err_msg)

    avatar = request.files.get('avatar')
    try:
        dao.add_tenant(avatar=avatar,
                     name=request.form.get('name'),
                     username=request.form.get('username'),
                     password=request.form.get('password'))
    except Exception as ex:
        return render_template('register.html', err_msg="ERROR!")

    return redirect('/login')

@app.route('/logout')
@login_required
def logout_process():
    logout_user()
    return redirect('/')

@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)

@app.route('/tenant/index')
@login_required
def tenant_index():
    ctx = get_tenant_context()
    electric_price = float(Rule.query.filter(Rule.key == RuleKey.PRICE_ELECTRIC).first().value)
    water_price = float(Rule.query.filter(Rule.key == RuleKey.PRICE_WATER).first().value)
    time = datetime.now().strftime('%Y-%m')
    return render_template('tenant/index.html', contract=ctx['contract'], invoices=ctx['invoices'], electric_price=electric_price, water_price=water_price, time=time)

@app.route('/tenant/apartment')
@login_required
def tenant_apartment():
    ctx = get_tenant_context()
    return render_template('tenant/apartment.html', apartment=ctx['apartment'], contract=ctx['contract'])


@app.route('/tenant/payments')
@login_required
def tenant_payments():
    ctx = get_tenant_context()
    return render_template('tenant/payments.html', invoices=ctx['invoices'], total_unpaid=ctx['total_unpaid'], due_date=ctx['due_date'])

@app.route('/tenant/rules')
def tenant_rules():
    rules = Rule.query.all()
    now = datetime.now()

    for r in rules:
        r.is_new = (now - r.last_updated) <= timedelta(hours=24)
    return render_template('tenant/rules.html', rules=rules)

@app.route('/tenant/profile')
def tenant_profile():
    ctx = get_tenant_context()
    return render_template('tenant/profile.html', apartment=ctx['apartment'], contract=ctx['contract'])

@app.route('/technician/index')
@login_required
def technician_index():
    rented_apartments = dao.load_apartments(status=ApartmentStatus.RENTED)
    return render_template('technician/index.html', apartments=rented_apartments)

# upload anh moi
@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if request.method == 'POST':
        file_to_upload = request.files['avatar']

        if file_to_upload:
            upload_result = cloudinary.uploader.upload(
                file_to_upload,
                folder="skyscraper_avatars",
                public_id=f"avatar_{current_user.id}",
                overwrite=True,
                resource_type="image"
            )
            image_url = upload_result['secure_url']
            current_user.avatar = image_url
            db.session.commit()
    return redirect(url_for('tenant_profile'))

# thay doi thong tin cho tenant
@app.route('/change_info', methods=['POST'])
@login_required
def change_user_info():
    current_user.phone_number = request.form.get("phone_number")
    current_user.email = request.form.get("email")
    dob_str = request.form.get("dob")
    if dob_str:
        current_user.dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    db.session.commit()
    return redirect(url_for('tenant_profile'))

# doi password
@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    if current_user.password != hash_password(request.form.get("current_password")):
        return redirect(url_for('tenant_profile', tab="password", msg="WRONG PASSWORD!"))

    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    if new_pw != confirm_pw:
        return redirect(url_for('tenant_profile', tab="password", msg="WRONG CONFIRM PASSWORD!"))

    current_user.password = hash_password(new_pw)
    db.session.commit()

    flash("", "success")
    return redirect(url_for('tenant_profile', tab="password", msg="CHANGE PASSWORD SUCCESSFULLY!"))

if __name__ == "__main__":
    from aapp import admin
    app.run(debug=True)