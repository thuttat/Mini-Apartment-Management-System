from flask import render_template, request, redirect
from flask_login import current_user, login_required, login_user, logout_user
from aapp import app, dao, login


@app.route('/')
def index():
    apartments = dao.load_apartments(
        room_type=request.args.get('room_type'),
        status=request.args.get('status'),
        min_price=request.args.get('min_price'),
        max_price=request.args.get('max_price')
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
        # Redirect theo role
        if role == 2:
            return redirect('/admin')
        elif role == 1:
            return redirect('/tenant/index')
        # elif role == 'technician':
        #     return redirect('/technician-dashboard')

    return redirect('/?login_failed=1')


@app.route('/register', methods=['post'])
def register_process():
    password = request.form.get('password')
    confirm = request.form.get('confirm')
    if password != confirm:
        err_msg = 'MẬT KHẨU KHÔNG KHỚP!'
        return render_template('register.html', err_msg=err_msg)

    avatar = request.files.get('avatar')
    try:
        dao.add_tenant(avatar=avatar,
                     name=request.form.get('name'),
                     username=request.form.get('username'),
                     password=request.form.get('password'))
    except Exception as ex:
        return render_template('register.html', err_msg="Hệ thống bị lỗi! Vui lòng quay lại sau!")

    return redirect('/login')

@app.route('/logout')
@login_required
def logout_process():
    logout_user()
    return redirect('/')

@login.user_loader
def load_user(user_id):
    return dao.get_manager_by_id(user_id)

@app.route('/tenant/index')
@login_required
def tenant_index():
    return render_template('tenant/index.html')

@app.route('/tenant/apartment')
def tenant_apartment():
    # apartment = dao.tenant_load_user(current_user.id)
    return render_template('tenant/apartment.html')

@app.route('/tenant/payments')
def tenant_payments():
    return render_template('tenant/payments.html')

@app.route('/tenant/notifications')
def tenant_notifications():
    return render_template('tenant/notifications.html')

@app.route('/tenant/profile')
def tenant_profile():
    return render_template('tenant/profile.html')

@app.route('/tenant/settings')
def tenant_settings():
    return render_template('tenant/settings.html')

if __name__ == "__main__":
    from aapp import admin
    app.run(debug=True)