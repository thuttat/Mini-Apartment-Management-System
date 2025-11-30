from os import abort

from flask import render_template, request, redirect, url_for
from flask_login import login_user, current_user, login_required, logout_user
from sqlalchemy.testing.pickleable import User

from aapp import app, dao, login
from aapp.models import UserRole, Technician


@app.route('/')
def index():
    apartments = dao.load_apartments(
        room_type=request.args.get('room_type'),
        status=request.args.get('status'),
        min_price=request.args.get('min_price'),
        max_price=request.args.get('max_price')
    )

    return render_template('index.html', apartments=apartments)


@app.route('/login', methods=['post'])
def login_process():
    username = request.form.get("username")
    password = request.form.get("password")

    manager = dao.auth_manager(username=username, password=password)
    technician = dao.auth_technician(username=username, password=password)
    if manager:
        login_user(manager)
        return redirect('/admin')
    elif technician:
        login_user(technician)
        return redirect('/technician')

    return redirect('/?login_failed=1')

# @app.route('/technician')
# def technician():
#     abort(401)


@login.user_loader
def load_user(user_id):
    return dao.get_user(user_id)


@app.route('/technician')
@login_required
def technician_dashboard():
    return render_template('technician/index.html')

@app.context_processor
def user_role():
    return dict(UserRole=UserRole)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

if __name__ == "__main__":
    from aapp import admin
    app.run(debug=True)

