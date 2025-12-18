from datetime import datetime

from cloudinary.api import usage
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required, login_user, logout_user
<<<<<<< Updated upstream
from aapp import app, dao, login
from aapp.utils import get_months_list, save_result, validate_reading, handle_meter_reading
from aapp.dao import get_last_reading_values, save_new_reading, get_contract_expiration
import cloudinary.uploader
from aapp.models import UserRole, ApartmentStatus, ContractStatus, Apartment
from aapp.utils import process_upload
=======
from aapp import vnpay
from aapp import app, dao, login, db,vnpay_client
from aapp.models import UserRole, ApartmentStatus, ContractStatus, Rule, RuleKey, Apartment, PaymentStatus, Invoice
from aapp.utils import (
    get_tenant_context, hash_password, get_months_list, handle_meter_reading
)
>>>>>>> Stashed changes


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

# @app.route('/login', methods=['post'])
# def login_process():
#     username = request.form.get("username")
#     password = request.form.get("password")

#     manager = dao.auth_manager(username=username, password=password)

#     if manager:
#         login_user(manager)
#         return redirect('/admin')

#     return redirect('/?login_failed=1')


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

        elif role == 3:
            return redirect('/technician')

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
    return render_template('tenant/index.html')

@app.route('/tenant/apartment')
@login_required
def tenant_apartment():
    contracts = dao.load_contracts(tenant_id=current_user.id, status=ContractStatus.ACTIVE)

    my_apartment = None
    my_contract = None

    if contracts:
        my_contract = contracts[0]
        my_apartment = dao.get_apartment_by_id(my_contract.apartment_id)

    return render_template('tenant/apartment.html', apartment=my_apartment, contract=my_contract)


@app.route('/tenant/payments')
@login_required
def tenant_payments():
    contracts = dao.load_contracts(tenant_id=current_user.id, status=ContractStatus.ACTIVE)
    invoices = []

    if contracts:
        contract_id = contracts[0].id
        invoices = dao.load_invoices(contract_id=contract_id)
        invoices.sort(key=lambda x: x.month, reverse=True)
    return render_template('tenant/payments.html', invoices=invoices)

@app.route('/tenant/notifications')
def tenant_notifications():
    return render_template('tenant/notifications.html')

@app.route('/tenant/profile')
def tenant_profile():
    return render_template('tenant/profile.html')

@app.route('/tenant/settings')
def tenant_settings():
    return render_template('tenant/settings.html')


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


@app.route('/technician/meter_reading/<string:reading_type>', methods=['GET','POST'])
@login_required
def meter_reading_view(reading_type):
    if not current_user.is_authenticated or current_user.user_role!=UserRole.TECHNICIAN or reading_type not in ['electric','water']:
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

    apartments=dao.load_apartments(status=ApartmentStatus.RENTED)
    months=get_months_list()
    return render_template('technician/meter_reading.html', apartments=apartments, months=months,reading_type=reading_type)

@app.route('/contracts_expiration')
@login_required
def report_contracts_expiration():
    try:
        days=int(request.args.get('days',30))
    except ValueError:
<<<<<<< Updated upstream
        days=30
    contract_expiration=dao.get_contract_expiration(day_limit=days)
    return render_template('reports/contracts_expiration.html', contract_expiration=contract_expiration,day_limit=days,datetime=datetime)
=======
        days = 30
    contract_expiration = dao.get_contract_expiration(day_limit=days)
    return render_template('reports/contracts_expiration.html', contract_expiration=contract_expiration, day_limit=days,
                           datetime=datetime)


@app.route('/manager/revenue-report')
@login_required
def report_revenue():
    if current_user.user_role != UserRole.MANAGER:
        return redirect('/')  # Hoặc trang lỗi 403

    kw = request.args.get('kw')
    month = request.args.get('month')

    stats = dao.stats_revenue(kw=kw, month=month)

    total_revenue = 0
    if stats:
        for s in stats:
            if s[3] == PaymentStatus.PAID:
                total_revenue += s[2]

    # Lưu ý: render template mới nằm trong thư mục reports
    return render_template('reports/revenue.html',
                           stats=stats,
                           month=month,
                           kw=kw,
                           total_revenue=total_revenue)

@app.route('/payment')
def payment():
    invoice_id = request.args.get('invoice_id')
    amount = request.args.get('amount')
    if not invoice_id or not amount:
        return "Thiếu thông tin hóa đơn", 400

    params = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': vnpay_client.tmn_code,
        'vnp_Amount': int(float(amount)) * 100,
        'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
        'vnp_CurrCode': 'VND',
        'vnp_IpAddr': request.remote_addr,
        'vnp_Locale': 'vn',
        'vnp_OrderInfo': f"Thanh toan hao don {invoice_id}",
        'vnp_OrderType': 'billpayment',
        'vnp_ReturnUrl': url_for('payment_return',_external=True),
        'vnp_TxnRef': str(invoice_id),
    }
    pay_url=vnpay_client.get_payment_url(params)
    return redirect(pay_url)

@app.route('/payment_return',methods=['GET'])
def payment_return():
    data=request.args.to_dict()
    if vnpay_client.validate_response(data):
        vnp_txn_ref = data.get('vnp_TxnRef')
        response_code = data.get('vnp_ResponseCode')
        invoice_id = vnp_txn_ref.split('_')[0]
        if response_code=='00':
            invoice=Invoice.query.get(int(invoice_id))
            if invoice:
                invoice.status=PaymentStatus.PAID
                db.session.commit()
                db.session.refresh(invoice)
            flash(f"Thanh toán thành công hóa đơn #{invoice_id}!", "success")
            return redirect(url_for('tenant_payments'))
        else:
            flash(f"Thanh toán không thành công. Mã lỗi: {response_code}", "danger")
            return redirect(url_for('tenant_payments'))
    else:
        return "Xác thực không hợp lệ!",400
>>>>>>> Stashed changes

if __name__ == "__main__":
    from aapp import admin
    app.run(debug=True)