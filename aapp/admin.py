from dateutil.relativedelta import relativedelta
from flask_admin.contrib.sqla import ModelView
from werkzeug.utils import redirect
from flask_admin import Admin, BaseView, expose
from flask_login import current_user, logout_user
from flask_admin.form import rules
from wtforms import validators, ValidationError
from aapp.utils import get_next_id, hash_password
from aapp import app, db, dao
from aapp.models import (Apartment, Tenant, Manager, Technician, Contract, Invoice,
                         Rule, UserRole, ApartmentDetail, RuleKey, ContractStatus, ApartmentStatus)


class AdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.MANAGER

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/?forbidden=1')


# =========================================================
# USER
# =========================================================
class ManagerView(AdminView):
    column_list = ['id', 'full_name', 'phone_number', 'email', 'user_role']
    column_searchable_list = ['id', 'full_name', 'username']
    column_filters = ['user_role']
    form_columns = ['full_name', 'username', 'password', 'phone_number', 'email', 'user_role', 'active']

    def on_model_change(self, form, model, is_created):
        if is_created and not model.id:
            model.id = get_next_id(Manager, "M", 3)

        if form.password.data:
            model.password = hash_password(form.password.data)


class TenantView(AdminView):
    column_list = ['id', 'full_name', 'phone_number', 'email', 'user_role']
    column_searchable_list = ['id', 'full_name', 'username']
    column_filters = ['user_role']
    page_size = 30
    form_columns = ['full_name', 'username', 'password', 'phone_number', 'email', 'avatar', 'user_role', 'active']

    def on_model_change(self, form, model, is_created):
        if is_created and not model.id:
            model.id = get_next_id(Tenant, "T", 3)

        if form.password.data:
            model.password = hash_password(form.password.data)


class TechnicianView(AdminView):
    column_list = ['id', 'full_name', 'phone_number', 'email', 'user_role']
    column_searchable_list = ['id', 'full_name']
    form_columns = ['full_name', 'username', 'password', 'phone_number', 'email', 'user_role', 'active']

    def on_model_change(self, form, model, is_created):
        if is_created and not model.id:
            model.id = get_next_id(Technician, "TECH", 3)

        if form.password.data:
            model.password = hash_password(form.password.data)


# =========================================================
# APARTMENT
# =========================================================
class ApartmentView(AdminView):
    column_list = ['id', 'room_type', 'status', 'floor', 'price', 'area']
    column_searchable_list = ['id']
    column_filters = ['status', 'room_type', 'floor']
    column_editable_list = ['status', 'price']
    form_columns = ['id', 'room_type', 'status', 'floor', 'area', 'price', 'image_urls']
    can_export = True


class ApartmentDetailView(AdminView):
    column_list = ['id', 'apartment', 'manager', 'note', 'active']
    column_searchable_list = ['apartment.id', 'manager.full_name']
    column_filters = ['apartment.id', 'manager.id']
    can_export = True
    edit_modal = True

    def on_model_change(self, form, model, is_created):
        if is_created and not model.id:
            model.id = get_next_id(ApartmentDetail, "AD", 4)


# =========================================================
# CONTRACT
# =========================================================
class ContractView(AdminView):
    column_list = ['id', 'apartment', 'tenant', 'start_date', 'end_date', 'member_count', 'rent_price', 'status']
    column_filters = ['status', 'apartment.id', 'tenant.id']
    column_searchable_list = ['id']
    can_export = True

    form_columns = ['apartment', 'tenant', 'start_date', 'rental_period', 'member_count', 'deposit', 'rent_price', 'status']
    form_excluded_columns = ('end_date',)

    def on_model_change(self, form, model, is_created):
        if model.start_date and model.rental_period:
            model.end_date = Contract.calculate_end_date(model.start_date, model.rental_period)

        if is_created and not model.id:
            model.id = get_next_id(Contract, "C", 3)

        max_people = dao.get_rule_value(RuleKey.MAX_PER_ROOM)
        if model.member_count > int(max_people):
            raise validators.ValidationError(
                f"The quantity is ({model.member_count})/({int(max_people)})."
            )

        if is_created and model.status == ContractStatus.ACTIVE:
            existing = Contract.query.filter_by(apartment_id=model.apartment.id, status=ContractStatus.ACTIVE).first()
            if existing:
                raise validators.ValidationError(f"Room {model.apartment.id} has active constract!")


# =========================================================
# INVOICE
# =========================================================
class InvoiceView(AdminView):
    column_list = ['id', 'contract', 'month', 'total_amount', 'status']
    column_filters = ['status', 'month']
    column_searchable_list = ['id', 'contract.id']
    can_export = True
    form_columns = ['contract', 'month', 'electric_usage', 'water_usage', 'service_fee', 'status']

    def on_model_change(self, form, model, is_created):
        if is_created and not model.id:
            model.id = get_next_id(Invoice, "INV", 6)

        e_price = dao.get_rule_value(RuleKey.PRICE_ELECTRIC)
        w_price = dao.get_rule_value(RuleKey.PRICE_WATER)
        s_price = model.service_fee if model.service_fee else dao.get_rule_value(RuleKey.PRICE_SERVICE)

        e_fee = (model.electric_usage or 0) * e_price
        w_fee = (model.water_usage or 0) * w_price

        model.electric_fee = e_fee
        model.water_fee = w_fee
        model.service_fee = s_price
        model.total_amount = e_fee + w_fee + s_price


# =========================================================
# RULE
# =========================================================
class RuleView(AdminView):
    column_list = ['key', 'name_display', 'value', 'description', 'last_updated']
    column_searchable_list = ['name_display']
    column_editable_list = ['value']
    can_create = False
    can_delete = False


# =========================================================
# LOGOUT
# =========================================================
class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect('/')

    def is_accessible(self):
        return current_user.is_authenticated


# =========================================================
# INIT ADMIN
# =========================================================
admin = Admin(app=app, name="Apartment Management")

admin.add_view(ManagerView(Manager, db.session, name='Manager'))
admin.add_view(TenantView(Tenant, db.session, name='Tenant'))
admin.add_view(TechnicianView(Technician, db.session, name='Technician'))

admin.add_view(ApartmentView(Apartment, db.session, name='Apartment'))
admin.add_view(ApartmentDetailView(ApartmentDetail, db.session, name='Apartment Detail'))

admin.add_view(ContractView(Contract, db.session, name='Contract'))
admin.add_view(InvoiceView(Invoice, db.session, name='Invoice'))
admin.add_view(RuleView(Rule, db.session, name='Rule'))

admin.add_view(LogoutView(name="Logout"))