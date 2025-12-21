import math
from datetime import datetime, timedelta
from sys import exception

import cloudinary.uploader
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_required, login_user, logout_user

from aapp import app, dao, login, db, vnpay_client, init_extensions
from aapp.dao import renew_contract, load_invoices, count_invoices
from aapp.models import UserRole, ApartmentStatus, ContractStatus, Rule, RuleKey, Apartment, PaymentStatus, Invoice, Contract
from aapp.utils import (
    get_tenant_context, hash_password, get_months_list, handle_meter_reading
)


@app.context_processor
def inject_rules():
    return dict(global_rules=dao.get_all_rules_as_dict())


@app.route('/')
def index():
    req_status = request.args.get('status')
    room_type = request.args.get('room_type')
    from_price = request.args.get('from_price')
    to_price = request.args.get('to_price')
    keyword = request.args.get('keyword')
    page = int(request.args.get('page', 1))


    status_filter = req_status if req_status else [
        ApartmentStatus.AVAILABLE,
        ApartmentStatus.LOOKING_FOR_ROOMMATE
    ]

    apartments = dao.load_apartments(
        room_type=room_type,
        status=status_filter,
        from_price=from_price,
        to_price=to_price,
        keyword=keyword,
        page=page
    )
    total_count = dao.count_for_pagination(
        room_type=room_type,
        status=status_filter,
        from_price=from_price,
        to_price=to_price,
        keyword=keyword
    )
    return render_template('index.html', apartments=apartments,
                           pages=math.ceil(total_count / app.config['PAGE_SIZE']))


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
            return redirect('/')
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

# man hinh gia han hop dong cua admin nam o ngoai
@app.route("/admin/renew_contracts", methods=["GET", "POST"])
def renew_contract_view():
    if request.method == "POST":
        contract_id = request.form["contract_id"]
        rental_period = int(request.form["rental_period"])

        renew_contract(contract_id, rental_period)
        flash("Contract renewed successfully!")
        return redirect(url_for("renew_contract_view"))

    active_contracts = Contract.query.filter(Contract.status == ContractStatus.ACTIVE).all()

    return render_template(
        "admin/renew_contracts.html", contracts=active_contracts)


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

    return render_template(
        'tenant/apartment.html', apartment=ctx['apartment'], contract=ctx['contract'])

@app.route('/tenant/contract/<contract_id>')
@login_required
def tenant_contract_detail(contract_id):
    contract = Contract.query.get(contract_id)

    if not contract:
        return render_template('404.html'), 404

    if contract.tenant_id != current_user.id:
        return "This is not your contract!", 403

    return render_template('tenant/contract_detail.html', contract=contract)


@app.route('/tenant/payments')
@login_required
def tenant_payments():
    ctx = get_tenant_context()
    contract = ctx['contract']
    page = int(request.args.get('page', 1))
    req_month = request.args.get('month')
    req_status = request.args.get('status')

    invoices = load_invoices(
        contract_id=contract.id,
        month=req_month,
        status=PaymentStatus[req_status] if req_status else None,
        page=page
    )

    total_unpaid = sum(inv.total_amount for inv in invoices if inv.status.name == 'UNPAID')

    return render_template('tenant/payments.html',
                           invoices=invoices,
                           total_unpaid=total_unpaid,
                           pages=int(math.ceil(count_invoices(contract.id, status=PaymentStatus[req_status] if req_status else None)
                                               / app.config['PAGE_SIZE'])))


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

    return render_template('tenant/profile.html', apartment=ctx['apartment'],
                           contract=ctx['contract'], contracts=ctx['contracts'])


# ==========================================
# TENANT - PROFILE ACTIONS
# ==========================================
@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if request.method == 'POST':
        file_to_upload = request.files['avatar']

        try:
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
                flash("Update avatar successfully!", category='success')
            else:
                flash("No file selected!", category='danger')
        except Exception:
            db.session.rollback()
            flash("There's something wrong! Try again later.", "danger")
    return redirect(url_for('tenant_profile'))


@app.route('/change_info', methods=['POST'])
@login_required
def change_user_info():
    try:
        current_user.phone_number = request.form.get("phone_number")
        current_user.email = request.form.get("email")
        dob_str = request.form.get("dob")
        if dob_str:
            current_user.dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        db.session.commit()
        flash("Update personal information successfully!", 'success')

    except Exception:
        db.session.rollback()
        flash("There's something wrong! Try again later.", "danger")
    return redirect(url_for('tenant_profile'))


@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    if current_user.password != hash_password(request.form.get("current_password")):
        flash('Current password is incorrect!', 'danger')
        return redirect(url_for('tenant_profile'))

    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    if new_pw != confirm_pw:
        flash('Confirm password is incorrect!', 'danger')
        return redirect(url_for('tenant_profile'))

    current_user.password = hash_password(new_pw)
    db.session.commit()

    flash("Password changed successfully!", "success")
    return redirect(url_for('tenant_profile'))

# xu ly doi can ho cho tenant
@app.route('/switch_apartment/<contract_id>', methods=['POST'])
@login_required
def switch_apartment(contract_id):
    contracts = dao.load_contracts(tenant_id=current_user.id, status=ContractStatus.ACTIVE)

    for c in contracts:
        if contract_id != c.id:
            continue

    session['current_contract_id'] = contract_id
    return redirect(url_for('tenant_profile', contract_id=contract_id))

# ==========================================
# TECHNICIAN ROUTES
# ==========================================
@app.route('/technician')
def admin_index():
    return render_template('technician/index.html')


@app.route('/chart')
@login_required
def chart_view():
    stats_data = dao.count_apartments()
    return render_template('reports/chart.html', stats_data=stats_data)


@app.route('/technician/index')
@login_required
def technician_index():
    rented_apartments = dao.load_apartments(status=[ApartmentStatus.RENTED, ApartmentStatus.LOOKING_FOR_ROOMMATE])
    return render_template('technician/index.html', apartments=rented_apartments)


@app.route('/technician/meter_reading/<string:reading_type>', methods=['GET', 'POST'])
@login_required
def meter_reading_view(reading_type):
    if not current_user.is_authenticated or current_user.user_role != UserRole.TECHNICIAN or reading_type not in [
        'electric', 'water']:
        flash('You have no role or this site does not accessable', 'danger')
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

    apartments = dao.load_apartments(status=[ApartmentStatus.RENTED, ApartmentStatus.LOOKING_FOR_ROOMMATE],page = None)
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



@app.route('/manager/revenue-report')
@login_required
def report_revenue():
    if current_user.user_role != UserRole.MANAGER:
        return redirect('/')
    year = request.args.get('year')
    month = request.args.get('month')
    kw = request.args.get('kw')

    stats = []
    mode = 'year' if year else 'month'

    if mode == 'year':
        stats = dao.stats_revenue_by_year(year)
    else:
        if not month and not kw:
            month = datetime.now().strftime('%Y-%m')
        stats = dao.stats_revenue(kw=kw, month=month)

    total_revenue = 0
    if stats:
        for s in stats:
            if mode == 'year':
                total_revenue += s[1]
            elif s[3] == PaymentStatus.PAID:
                total_revenue += s[2]

    return render_template('reports/revenue.html',
                           stats=stats,month=month,year=year,kw=kw,total_revenue=total_revenue,mode=mode)

@app.route('/payment')
def payment():
    invoice_id = request.args.get('invoice_id')
    amount = request.args.get('amount')
    txn_ref = f"{invoice_id}_{int(datetime.now().timestamp())}"
    if not invoice_id or not amount:
        return "Have no information about this once", 400

    params = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': vnpay_client.tmn_code,
        'vnp_Amount': int(float(amount)) * 100,
        'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
        'vnp_CurrCode': 'VND',
        'vnp_IpAddr': request.remote_addr,
        'vnp_Locale': 'vn',
        'vnp_OrderInfo': f"Pay for {invoice_id}",
        'vnp_OrderType': 'billpayment',
        'vnp_ReturnUrl': url_for('payment_return',_external=True),
        'vnp_TxnRef': txn_ref,
    }
    pay_url=vnpay_client.get_payment_url(params)
    return redirect(pay_url)

@app.route('/payment_return',methods=['GET'])
def payment_return():
    data=request.args.to_dict()
    if vnpay_client.validate_response(data):
        vnp_txn_ref = data.get('vnp_TxnRef')
        response_code = data.get('vnp_ResponseCode')
        vnp_amount = int(data.get('vnp_Amount',0))/100

        try:
            invoice_id_str= vnp_txn_ref.split('_')[0]
        except Exception as e:
            flash("Invalid transaction code!", "danger")
            return redirect(url_for('tenant_payments'))
        invoice_id = str(invoice_id_str)
        invoice = Invoice.query.get(str(invoice_id))
        if response_code=='00':
            if invoice:
                if abs(invoice.total_amount-vnp_amount) < 1:
                    invoice.status=PaymentStatus.PAID
                    db.session.commit()
                    db.session.refresh(invoice)
                    flash(f"Payment successful for invoice #{invoice_id}!", "success")
                else:
                    flash(f"Payment amount({vnp_amount}) does not match the invoice!", "danger")
            else:
                flash(f"Invoice not found!", "danger")
        else:
            flash(f"Payment failed. Response code: {response_code}", "danger")
        return redirect(url_for('tenant_payments'))
    else:
        return "Invalid checksum!",400

init_extensions()

if __name__ == "__main__":
    from aapp import admin

    app.run(debug=True)