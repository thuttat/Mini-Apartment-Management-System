from flask import render_template, request, redirect
from flask_login import login_user
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


@app.route('/login', methods=['post'])
def login_process():
    username = request.form.get("username")
    password = request.form.get("password")

    manager = dao.auth_manager(username=username, password=password)

    if manager:
        login_user(manager)
        return redirect('/admin')

    return redirect('/?login_failed=1')




@login.user_loader
def load_user(user_id):
    return dao.get_manager_by_id(user_id)


if __name__ == "__main__":
    from aapp import admin
    app.run(debug=True)
