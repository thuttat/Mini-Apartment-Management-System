from datetime import datetime, timedelta
import cloudinary.uploader
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required, login_user, logout_user

from aapp import app, dao, login, db
from aapp.models import UserRole, ApartmentStatus, ContractStatus, Rule, RuleKey, Apartment
from aapp.utils import (
    get_tenant_context, hash_password, get_months_list, handle_meter_reading
)


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


@app.route('/settings')
@login_required
def settings():
    return render_template('layout/settings.html')


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
        err_msg = 'Wrong password!'
        return render_template('register.html', err_msg=err_msg)

    name = request.form.get('name')
    username = request.form.get('username')
    avatar = request.files.get('avatar')
    role = request.form.get('role')

    try:
        if role == 'MANAGER':
            dao.add_manager(name=name, username=username, password=password, avatar=avatar)
        elif role == 'TECHNICIAN':
            dao.add_technician(name=name, username=username, password=password, avatar=avatar)
        else:
            dao.add_tenant(name=name, username=username, password=password, avatar=avatar)

    except Exception as ex:
        print(ex)
        return render_template('register.html', err_msg="Error")

    return redirect('/login')


@app.route('/logout')
@login_required
def logout_process():
    logout_user()
    return redirect('/')


@app.route('/apartment/<apartment_id>')
def apartment_detail(apartment_id):
    apt = dao.get_apartment_by_id(apartment_id)
    if not apt:
        return render_template('404.html'), 404

    return render_template('details.html', apartment=apt)


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


# ==========================================
# TENANT ROUTES
# ==========================================
@app.route('/tenant/index')
@login_required
def tenant_index():
    ctx = get_tenant_context()
    electric_price = float(Rule.query.filter(Rule.key == RuleKey.PRICE_ELECTRIC).first().value)
    water_price = float(Rule.query.filter(Rule.key == RuleKey.PRICE_WATER).first().value)
    time = datetime.now().strftime('%Y-%m')
    return render_template('tenant/index.html',
                           contract=ctx['contract'],
                           invoices=ctx['invoices'],
                           electric_price=electric_price,
                           water_price=water_price,
                           time=time)


@app.route('/tenant/apartment')
@login_required
def tenant_apartment():
    ctx = get_tenant_context()
    return render_template('tenant/apartment.html', apartment=ctx['apartment'], contract=ctx['contract'])


@app.route('/tenant/payments')
@login_required
def tenant_payments():
    contracts = dao.load_contracts(tenant_id=current_user.id, status=ContractStatus.ACTIVE)
    invoices = []

    req_month = request.args.get('month')
    req_status = request.args.get('status')

    if contracts:
        contract_id = contracts[0].id
        all_invoices = dao.load_invoices(contract_id=contract_id)

        for inv in all_invoices:
            is_match = True
            if req_month and inv.month != req_month:
                is_match = False
            if req_status and inv.status.name != req_status:
                is_match = False

            if is_match:
                invoices.append(inv)

        invoices.sort(key=lambda x: x.month, reverse=True)
    total_unpaid = sum(inv.total_amount for inv in invoices if inv.status.name == 'UNPAID')

    return render_template('tenant/payments.html',
                           invoices=invoices,
                           total_unpaid=total_unpaid)


@app.route('/tenant/invoice/<invoice_id>')
@login_required
def tenant_invoice_detail(invoice_id):
    invoice = dao.get_invoice_by_id(invoice_id)

    if not invoice:
        return render_template('404.html'), 404

    if invoice.contract.tenant_id != current_user.id:
        return "This is not your invoice!", 403

    return render_template('tenant/invoice_detail.html', invoice=invoice)


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


# ==========================================
# TENANT - PROFILE ACTIONS
# ==========================================
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

    flash("Password changed successfully!", "success")
    return redirect(url_for('tenant_profile', tab="password", msg="CHANGE PASSWORD SUCCESSFULLY!"))


# ==========================================
# TECHNICIAN ROUTES
# ==========================================
@app.route('/technician')
def admin_index():
    return render_template('technician/index.html')


@app.route('/chart')
def chart_view():
    stats_data = dao.count_apartments()
    return render_template('reports/chart.html', stats_data=stats_data)


@app.route('/technician/index')
@login_required
def technician_index():
    rented_apartments = dao.load_apartments(status=ApartmentStatus.RENTED)
    return render_template('technician/index.html', apartments=rented_apartments)


@app.route('/technician/meter_reading/<string:reading_type>', methods=['GET', 'POST'])
@login_required
def meter_reading_view(reading_type):
    if not current_user.is_authenticated or current_user.user_role != UserRole.TECHNICIAN or reading_type not in [
        'electric', 'water']:
        flash('Bạn không có quyền hoặc trang không hợp lệ.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = {
            'apartment_id': request.form.get('apartment_id'),
            'month': request.form.get('month'),
            'new_reading_str': request.form.get('new_meter_reading'),
            'image_file': request.files.get('reading_proof_photo'),
            'reading_type': reading_type
        }

        success, message = handle_meter_reading(data)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')

        return redirect(url_for('meter_reading_view', reading_type=reading_type))

    apartments = dao.load_apartments(status=ApartmentStatus.RENTED)
    months = get_months_list()
    return render_template('technician/meter_reading.html', apartments=apartments, months=months,
                           reading_type=reading_type)


@app.route('/contracts_expiration')
@login_required
def report_contracts_expiration():
    try:
        days = int(request.args.get('days', 30))
    except ValueError:
        days = 30
    contract_expiration = dao.get_contract_expiration(day_limit=days)
    return render_template('reports/contracts_expiration.html', contract_expiration=contract_expiration, day_limit=days,
                           datetime=datetime)


if __name__ == "__main__":
    from aapp import admin

    app.run(debug=True)
