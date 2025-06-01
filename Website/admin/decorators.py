from functools import wraps
from flask import redirect, url_for, flash, session
from firebase_admin import auth

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('auth.login'))
        
        try:
            user = auth.get_user(session['user_id'])
            if not user.custom_claims or not user.custom_claims.get('admin'):
                flash('Admin access required', 'error')
                return redirect(url_for('views.home'))
        except:
            flash('Authentication failed', 'error')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function