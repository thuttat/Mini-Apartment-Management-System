from flask import render_template, request, redirect, url_for
from flask_login import current_user, login_required, login_user, logout_user
from aapp import app, dao, login

from aapp.models import UserRole, ApartmentStatus, ContractStatus


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

@app.route('/technician/index')
@login_required
def technician_index():
    rented_apartments = dao.load_apartments(status=ApartmentStatus.RENTED)
    return render_template('technician/index.html', apartments=rented_apartments)

if __name__ == "__main__":
    from aapp import admin
    app.run(debug=True)