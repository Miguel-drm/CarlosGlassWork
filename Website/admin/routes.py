from flask import render_template, flash, redirect, url_for, request, send_file, jsonify, session
from firebase_admin import auth, firestore
from . import admin_bp
from .decorators import admin_required
from werkzeug.utils import secure_filename
from ..mongodb_config import get_gridfs, get_db
from bson.objectid import ObjectId
import io
import os
from cloudinary.uploader import upload, destroy
from cloudinary.utils import cloudinary_url
from cloudinary import config
from dotenv import load_dotenv
from ..constants import CUSTOMIZE_STATUS, STATUS_COLORS
from firebase_admin import firestore
from flask import jsonify

load_dotenv()

# Add Cloudinary configuration at the top after imports
config(
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key = os.getenv('CLOUDINARY_API_KEY'),
    api_secret = os.getenv('CLOUDINARY_API_SECRET')
)

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    try:
        # Get user count
        users_list = auth.list_users()
        total_users = len(users_list.users)

        # Get product count from Firestore
        db = firestore.client()
        products_ref = db.collection('products')
        products_count = len(list(products_ref.stream()))

        # Get customize requests
        customize_requests = []
        customize_ref = db.collection('customize_requests').order_by('created_at', direction=firestore.Query.DESCENDING).limit(10)
        for doc in customize_ref.stream():
            request = doc.to_dict()
            request['id'] = doc.id
            request['status_color'] = {
                'pending': 'warning',
                'approved': 'success',
                'rejected': 'danger'
            }.get(request['status'], 'secondary')
            customize_requests.append(request)

        return render_template('admin/admin_dashboard.html',
                             total_products=products_count,
                             total_users=total_users,
                             total_orders=0,
                             recent_orders=[],
                             customize_requests=customize_requests)

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('admin.manage_products'))

@admin_bp.route('/users')
@admin_required
def manage_users():
    try:
        users = auth.list_users()
        return render_template('admin/manage_users.html', users=users.users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/products')
@admin_required
def manage_products():
    try:
        # Initialize Firestore client
        db = firestore.client()
        
        # Get all products from the 'products' collection
        products_ref = db.collection('products')
        products = []
        
        for doc in products_ref.stream():
            product = doc.to_dict()
            product['id'] = doc.id  # Add document ID for actions
            products.append(product)
            
        return render_template('admin/manage_products.html', products=products)
    except Exception as e:
        flash(f'Error loading products: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            price = request.form.get('price')
            description = request.form.get('description')
            category = request.form.get('category')

            if not all([name, price, category]):
                flash('Missing required fields', 'error')
                return redirect(request.url)

            try:
                price = float(price)
            except ValueError:
                flash('Invalid price format', 'error')
                return redirect(request.url)

            # Handle image upload
            if 'image' not in request.files:
                flash('No image file uploaded', 'error')
                return redirect(request.url)

            image = request.files['image']
            if image.filename == '':
                flash('No selected image file', 'error')
                return redirect(request.url)

            if not allowed_file(image.filename):
                flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF', 'error')
                return redirect(request.url)

            try:
                # Upload image to Cloudinary
                upload_result = upload(image)
                
                # Save to Firestore
                db = firestore.client()
                product_data = {
                    'name': name,
                    'price': price,
                    'description': description,
                    'category': category,
                    'image_url': upload_result['secure_url'],
                    'image_public_id': upload_result['public_id'],
                    'created_at': firestore.SERVER_TIMESTAMP
                }
                
                db.collection('products').add(product_data)
                flash('Product added successfully!', 'success')
                return redirect(url_for('admin.manage_products'))

            except Exception as e:
                print(f"Error during save: {str(e)}")
                raise

        except Exception as e:
            flash(f'Error adding product: {str(e)}', 'error')
            return redirect(url_for('admin.add_product'))

    return render_template('admin/add_product.html')

@admin_bp.route('/products/<product_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    try:
        db = firestore.client()
        product_ref = db.collection('products').document(product_id)
        product = product_ref.get()

        if not product.exists:
            flash('Product not found', 'error')
            return redirect(url_for('admin.manage_products'))

        if request.method == 'POST':
            # Get form data
            update_data = {
                'name': request.form.get('name'),
                'price': float(request.form.get('price')),
                'description': request.form.get('description'),
                'category': request.form.get('category'),
                'updated_at': firestore.SERVER_TIMESTAMP
            }

            # Handle new image if uploaded
            if 'image' in request.files and request.files['image'].filename:
                image = request.files['image']
                if allowed_file(image.filename):
                    # Delete old image from Cloudinary if exists
                    old_data = product.to_dict()
                    if 'image_public_id' in old_data:
                        try:
                            destroy(old_data['image_public_id'])
                        except Exception as e:
                            print(f"Error deleting old image: {str(e)}")

                    # Upload new image to Cloudinary
                    try:
                        upload_result = upload(image)
                        update_data.update({
                            'image_url': upload_result['secure_url'],
                            'image_public_id': upload_result['public_id']
                        })
                    except Exception as e:
                        flash(f'Error uploading new image: {str(e)}', 'error')
                        return redirect(request.url)
                else:
                    flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF', 'error')
                    return redirect(request.url)

            # Update Firestore
            product_ref.update(update_data)
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin.manage_products'))

        # GET request - show edit form
        product_data = product.to_dict()
        product_data['id'] = product_id
        return render_template('admin/edit_product.html', product=product_data)

    except Exception as e:
        flash(f'Error editing product: {str(e)}', 'error')
        return redirect(url_for('admin.manage_products'))

@admin_bp.route('/images/<image_id>')
def serve_image(image_id):
    try:
        fs = get_gridfs()
        if fs is None:  # Changed from if not fs
            raise Exception("MongoDB connection failed")
            
        # Find and serve the file from GridFS
        file_data = fs.get(ObjectId(image_id))
        return send_file(
            io.BytesIO(file_data.read()),
            mimetype=file_data.content_type,
            as_attachment=False
        )
    except Exception as e:
        return f'Error loading image: {str(e)}'

@admin_bp.route('/products/<product_id>/delete', methods=['POST'])
@admin_required
def delete_product(product_id):
    try:
        # Get Firestore instance
        db = firestore.client()
        
        # Get product data
        product_ref = db.collection('products').document(product_id)
        product = product_ref.get()
        
        if product.exists:
            product_data = product.to_dict()
            
            # Delete image from Cloudinary if exists
            if 'image_public_id' in product_data:
                try:
                    destroy(product_data['image_public_id'])
                except Exception as e:
                    print(f"Error deleting image from Cloudinary: {str(e)}")
            
            # Delete product from Firestore
            product_ref.delete()
            return jsonify({'success': True})
        
        return jsonify({
            'success': False, 
            'error': 'Product not found'
        })
        
    except Exception as e:
        print(f"Error deleting product: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@admin_bp.route('/customize-requests/<request_id>/approve', methods=['POST'])
@admin_required
def approve_customize_request(request_id):
    try:
        db = firestore.client()
        request_ref = db.collection('customize_requests').document(request_id)
        request_doc = request_ref.get()

        if not request_doc.exists:
            return jsonify({'success': False, 'error': 'Request not found'})

        # Update request status
        request_ref.update({
            'status': CUSTOMIZE_STATUS['APPROVED'],
            'approved_at': firestore.SERVER_TIMESTAMP,
            'approved_by': session.get('user_id')
        })

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error approving request: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/customize-requests/<request_id>/delete', methods=['POST'])
@admin_required
def delete_customize_request(request_id):
    try:
        db = firestore.client()
        request_ref = db.collection('customize_requests').document(request_id)
        request_doc = request_ref.get()

        if not request_doc.exists:
            return jsonify({'success': False, 'error': 'Request not found'})

        # Delete the request
        request_ref.delete()

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting request: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/customize-requests')
@admin_required
def manage_customize_requests():
    try:
        db = firestore.client()
        requests_ref = db.collection('customize_requests').order_by('created_at', direction=firestore.Query.DESCENDING)
        customize_requests = []
        
        for doc in requests_ref.stream():
            request = doc.to_dict()
            request['id'] = doc.id
            # Convert Firestore timestamp to dict for JSON serialization
            if request.get('created_at'):
                request['created_at'] = {
                    '_seconds': request['created_at'].timestamp(),
                    '_nanoseconds': 0
                }
            customize_requests.append(request)
            
        return render_template('admin/customize_requests.html', requests=customize_requests)
    except Exception as e:
        flash(f'Error loading requests: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/products/<product_id>')
@admin_required
def get_product(product_id):
    try:
        db = firestore.client()
        product_doc = db.collection('products').document(product_id).get()
        
        if not product_doc.exists:
            return jsonify({'error': 'Product not found'}), 404
            
        product_data = product_doc.to_dict()
        product_data['id'] = product_doc.id
        
        return jsonify(product_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS