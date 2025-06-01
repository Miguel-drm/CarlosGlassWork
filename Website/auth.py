import datetime
from datetime import date
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError
from .admin.decorators import admin_required

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            user = auth.get_user_by_email(email)
            session['user_id'] = user.uid
            session['display_name'] = user.display_name
            
            # Explicitly check for admin status
            is_admin = user.custom_claims and user.custom_claims.get('admin') == True
            session['is_admin'] = is_admin
            
            flash('Logged in successfully!', 'success')
            return redirect(url_for('views.home'))
        except auth.UserNotFoundError:
            flash('No account found with this email.', 'error')
        except Exception as e:
            flash('Login failed. Please check your credentials.', 'error')
            
    return render_template("login.html")

@auth_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('fullName')
        birthdate = request.form.get('birthdate')
        
        # Calculate age
        try:
            birth_date = datetime.datetime.strptime(birthdate, '%Y-%m-%d').date()
            today = date.today()
            age = (today.year - birth_date.year - 
                  ((today.month, today.day) < (birth_date.month, birth_date.day)))
            
            if age < 18:
                flash('You must be 18 years or older to register.', 'error')
                return render_template("register.html")
                
            # Create user with no admin claims (regular user)
            user = auth.create_user(
                email=email,
                password=password,
                display_name=full_name
            )
            
            # Set custom claims to explicitly mark as non-admin
            auth.set_custom_user_claims(user.uid, {'admin': False})
            
            flash('Account created successfully!', 'success')
            return redirect(url_for('auth.login'))
            
        except ValueError:
            flash('Invalid date format.', 'error')
        except auth.EmailAlreadyExistsError:
            flash('Email already exists!', 'error')
        except FirebaseError as e:
            flash(f'An error occurred: {str(e)}', 'error')
            
    return render_template("register.html")

@auth_blueprint.route('/edit-account', methods=['GET', 'POST'])
def edit_account():
    if not session.get('user_id'):
        flash('Please login to access this page', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Get current user data
        user = auth.get_user(session['user_id'])
        
        if request.method == 'POST':
            full_name = request.form.get('fullName')
            
            # Update user profile
            auth.update_user(
                user.uid,
                display_name=full_name
            )
            
            flash('Account updated successfully!', 'success')
            return redirect(url_for('auth.edit_account'))
            
        try:
            return render_template('edit_account.html', user=user)
        except Exception as template_error:
            flash(f'Template error: {str(template_error)}', 'error')
            return redirect(url_for('views.home'))
        
    except auth.UserNotFoundError:
        flash('User not found. Please login again.', 'error')
        session.pop('user_id', None)
        return redirect(url_for('auth.login'))
    except Exception as e:
        flash(f'Error accessing account details: {str(e)}', 'error')
        return redirect(url_for('views.home'))

@auth_blueprint.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('auth.login'))