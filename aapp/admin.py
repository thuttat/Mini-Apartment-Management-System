from flask_admin.contrib.sqla import ModelView
from werkzeug.utils import redirect
from flask_admin import Admin, BaseView, expose
from flask_login import current_user, logout_user

from aapp import app, db
from aapp.models import Apartment, Tenant, Manager, Contract, Invoice, Rule, UserRole

class AdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.MANAGER

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/?forbidden=1')

class ApartmentView(AdminView):
    column_list = ['id', 'apartment_id', 'room_type', 'status', 'floor', 'area', 'price']
    column_searchable_list = ['apartment_id']
    column_filters = ['room_type', 'status', 'floor', 'price']
    can_export = True
    edit_modal = True
    page_size = 30

class TenantView(AdminView):
    column_list = ['id', 'tenant_id', 'full_name', 'phone_number', 'email', 'user_role']
    column_searchable_list = ['tenant_id', 'full_name']
    column_filters = ['user_role']
    page_size = 30

class ManagerView(AdminView):
    column_list = ['id', 'manager_id', 'full_name', 'phone_number', 'email', 'user_role']
    column_searchable_list = ['manager_id', 'full_name']
    column_filters = ['user_role']

class ContractView(AdminView):
    column_list = ['id', 'contract_id', 'apartment_id', 'tenant_id', 'start_date', 'end_date', 'rent_price', 'status']
    column_filters = ['status', 'apartment_id', 'tenant_id']
    column_searchable_list = ['contract_id']
    can_export = True

class InvoiceView(AdminView):
    column_list = ['id', 'invoice_id', 'contract_id', 'month', 'total_amount', 'status']
    column_filters = ['status', 'month']
    column_searchable_list = ['invoice_id', 'contract_id']
    can_export = True

class RuleView(AdminView):
    column_list = ['id', 'rule_name', 'value', 'description', 'last_updated']
    column_searchable_list = ['rule_name']

class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect('/')

    def is_accessible(self):
        return current_user.is_authenticated

admin = Admin(app=app, name="Apartment Management")

admin.add_view(ManagerView(Manager, db.session))
admin.add_view(TenantView(Tenant, db.session))
admin.add_view(ApartmentView(Apartment, db.session))
admin.add_view(ContractView(Contract, db.session))
admin.add_view(InvoiceView(Invoice, db.session))
admin.add_view(RuleView(Rule, db.session))
admin.add_view(LogoutView(name="Logout"))
