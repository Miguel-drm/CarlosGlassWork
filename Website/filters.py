from flask import Blueprint, current_app

bp = Blueprint('filters', __name__)

def init_filters(app):
    @app.template_filter('status_color')
    def status_color(status):
        colors = {
            'pending': 'warning',
            'processing': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger',
            'approved': 'success',
            'rejected': 'danger'
        }
        return colors.get(status.lower(), 'secondary')

    @app.template_filter('peso')
    def peso(value):
        try:
            if isinstance(value, str):
                value = value.replace('₱', '').replace(',', '')
            float_val = float(value)
            return "{:,.2f}".format(float_val)
        except (ValueError, TypeError):
            return "0.00"