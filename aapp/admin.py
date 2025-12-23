from datetime import datetime
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup
from werkzeug.utils import redirect
from flask_admin import Admin, BaseView, expose
from flask_login import current_user, logout_user
from wtforms import validators
from flask import request,flash
from wtforms.validators import ValidationError

from aapp.dao import handle_assign_contract, create_first_invoice
from aapp.utils import get_next_id, hash_password
from aapp import app, db, dao
from aapp.models import (Apartment, Tenant, Manager, Technician, Contract, Invoice,
                         Rule, UserRole, ApartmentDetail, RuleKey, ContractStatus,
                         ApartmentStatus, PaymentStatus, ContractAssignment)


class AdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.MANAGER

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/?forbidden=1')


# =========================================================
# USER
# =========================================================
class ManagerView(AdminView):
    column_list = ['id', 'full_name', 'phone_number', 'email', 'user_role', 'active']
    column_editable_list = ['active']
    column_searchable_list = ['id', 'full_name', 'username']
    column_filters = ['user_role', 'active']
    form_columns = ['full_name', 'username', 'password', 'phone_number', 'email', 'user_role', 'active']

    def on_model_change(self, form, model, is_created):
        if is_created and not model.id:
            model.id = get_next_id(Manager, "M", 3)
        if hasattr(form, 'password') and form.password.data:
            model.password = hash_password(form.password.data)


class TenantView(AdminView):
    column_list = ['id', 'full_name', 'phone_number', 'email', 'user_role']
    column_searchable_list = ['id', 'full_name', 'username']
    column_filters = ['user_role']
    page_size = 30
    form_columns = ['full_name', 'username', 'password', 'phone_number', 'email', 'dob', 'avatar', 'user_role',
                    'active']

    def on_model_change(self, form, model, is_created):
        if is_created and not model.id:
            model.id = get_next_id(Tenant, "T", 3)

        if hasattr(form, 'password') and form.password.data:
            model.password = hash_password(form.password.data)


class TechnicianView(AdminView):
    column_list = ['id', 'full_name', 'phone_number', 'email', 'user_role', 'active']
    column_searchable_list = ['id', 'full_name']
    column_editable_list = ['active']
    column_filters = ['user_role', 'active']
    form_columns = ['full_name', 'username', 'password', 'phone_number', 'email', 'user_role', 'active']

    def on_model_change(self, form, model, is_created):
        if is_created and not model.id:
            model.id = get_next_id(Technician, "TECH", 3)
        if hasattr(form, 'password') and form.password.data:
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
    can_edit = True
    can_delete = False

    form_columns = ['apartment', 'tenant', 'start_date', 'rental_period', 'member_count', 'deposit', 'status']
    form_excluded_columns = ('end_date', 'rent_price')

    def _available_apartments():
        occupied = db.session.query(Contract.apartment_id).filter(
            Contract.status.in_([ContractStatus.ACTIVE, ContractStatus.PENDING])
        )
        return Apartment.query.filter(~Apartment.id.in_(occupied))

    form_args = {
        'apartment': {
            'query_factory': _available_apartments,
        }
    }

    def on_model_change(self, form, model, is_created):
        if model.start_date and model.rental_period:
            model.end_date = dao.calculate_end_date(model.start_date, model.rental_period)

        if is_created and not model.id:
            model.id = get_next_id(Contract, "C", 3)
            model.rent_price = model.apartment.price
            if model.deposit is None:
                model.deposit = model.apartment.price

        max_people = dao.get_rule_value(RuleKey.MAX_PER_ROOM)
        if model.member_count > int(max_people):
            raise validators.ValidationError(
                f"The quantity is ({model.member_count})/({int(max_people)})."
            )

    def after_model_change(self, form, model, is_created):
        if not is_created:
            return

        if model.status == ContractStatus.ACTIVE:
            model.apartment.status = ApartmentStatus.RENTED  # chuyen doi trang thai can ho
            db.session.add(model.apartment)

        create_first_invoice(model)  # tao invoice thang dau

        db.session.commit()

class ContractAssignmentView(AdminView):
    column_list = ['id', 'contract', 'old_tenant', 'new_tenant', 'effective_date', 'note']
    column_filters = ['contract', 'effective_date']
    column_searchable_list = ['id']

    form_columns = ['contract', 'new_tenant', 'effective_date', 'note']
    can_delete = False
    can_edit = False

    def create_model(self, form):
        try:
            handle_assign_contract(
                contract_id=form.contract.data.id,
                new_tenant_id=form.new_tenant.data.id,
                effective_date=form.effective_date.data,
                note=form.note.data
            )
            return True
        except Exception as e:
            db.session.rollback()
            raise e

# =========================================================
# INVOICE
# =========================================================

class InvoiceView(AdminView):
    can_create = False
    can_edit = True
    can_delete = True
    can_export = True

    column_list = ['id', 'contract', 'month', 'rent_price', 'electric_usage', 'water_usage', 'total_amount', 'status']

    column_filters = ['status', 'month', 'contract.apartment.id']
    column_searchable_list = ['id', 'contract.id']
    column_default_sort = ('month', True)

    column_labels = {
        'contract': 'Constract',
        'month': 'Month',
        'rent_price': 'Rent price',
        'electric_usage': 'Electric (kWh)',
        'water_usage': 'Water (m3)',
        'total_amount': 'Total',
        'status': 'Status'
    }

    def _money_formatter(view, context, model, name):
        val = getattr(model, name)
        if val:
            return f"{val:,.0f} VNĐ"
        return "0 VNĐ"

    column_formatters = {
        'rent_price': _money_formatter,
        'total_amount': _money_formatter,
    }

    form_columns = [
        'contract',
        'month',
        'electric_end_reading', 'electric_usage',
        'water_end_reading', 'water_usage',
        'service_fee',
        'total_amount',
        'status'
    ]

    # Khóa
    form_widget_args = {
        'contract': {'disabled': True},
        'month': {'disabled': True},
        'electric_usage': {'disabled': True},
        'water_usage': {'disabled': True},
        'total_amount': {'disabled': True}
    }

    def on_model_change(self, form, model, is_created):
        usage_data = dao.calculate_usage(
            contract_id=model.contract.id,
            current_month=model.month,
            electric_end=model.electric_end_reading,
            water_end=model.water_end_reading
        )
        model.electric_usage = usage_data['electric_usage']
        model.water_usage = usage_data['water_usage']

        money_data = dao.calculate_monthly_invoice(
            contract=model.contract,
            electric_usage=model.electric_usage,
            water_usage=model.water_usage,
            service_fee=model.service_fee
        )
        model.electric_fee = money_data['electric_fee']
        model.water_fee = money_data['water_fee']
        model.total_amount = money_data['total_price']

    def delete_model(self, model):
        try:
            if model.status == PaymentStatus.PAID:
                flash(f'Can not delete {model.id} has paid', 'error')
                return False
            model.active = False
            self.session.commit()
            return True
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(f'{str(ex)}', 'error')
            self.session.rollback()
            return False

    def get_query(self):
        return super(InvoiceView, self).get_query().filter(self.model.active == True)

    def get_count_query(self):
        return super(InvoiceView, self).get_count_query().filter(self.model.active == True)


# =========================================================
# RULE
# =========================================================
class RuleView(AdminView):
    column_list = ['key', 'name_display', 'value', 'description', 'last_updated']
    column_searchable_list = ['name_display']
    column_editable_list = ['value']
    can_create = False
    can_delete = False

    def on_model_change(self, form, model, is_created):
        model.last_updated = datetime.now()


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
admin.add_view(ContractAssignmentView(ContractAssignment, db.session, name='Contract Assignment'))
admin.add_view(InvoiceView(Invoice, db.session, name='Invoice'))
admin.add_view(RuleView(Rule, db.session, name='Rule'))

admin.add_view(LogoutView(name="Logout"))