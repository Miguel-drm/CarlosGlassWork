from flask import Blueprint, render_template, session, flash, redirect, url_for, jsonify, request
from firebase_admin import firestore, auth  # Add auth import
from datetime import datetime
from flask_login import login_required

views = Blueprint('views', __name__)


@views.route('/')
def home():
    return render_template("home.html", now=datetime.now()) 

@views.route('/terms')
def terms():
    return render_template('terms.html', now=datetime.now())

@views.route('/privacy')
def privacy():
    return render_template('privacy.html', now=datetime.now())

@views.route('/about')
def about():
    return render_template('about.html', now=datetime.now())

@views.route('/customer-service')
def customer_service():
    return render_template('customer_service.html', now=datetime.now())

@views.route('/products')
def products_page():
    try:
        # Get products from Firestore using Firebase Admin SDK
        db = firestore.client()
        products_ref = db.collection('products')
        products = []
        
        for doc in products_ref.stream():
            product = doc.to_dict()
            product['id'] = doc.id
            products.append(product)
            
        return render_template('products.html', products=products)
    except Exception as e:
        print(f"Firestore Error: {str(e)}")  # Add debug print
        flash(f'Error loading products: {str(e)}', 'error')
        return redirect(url_for('views.home'))

@views.route('/cart')
def cart():
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please login to view your cart', 'error')
            return redirect(url_for('auth.login'))

        db = firestore.client()
        
        # Get cart items
        cart_items = []
        total = 0
        
        cart_ref = db.collection('cart_items').where('user_id', '==', user_id)
        cart_docs = cart_ref.stream()

        for doc in cart_docs:
            item_data = doc.to_dict()
            item_data['id'] = doc.id
            
            # Ensure price is a string and convert to float
            try:
                price = float(str(item_data.get('price', '0')).replace('₱', '').replace(',', ''))
                quantity = int(item_data.get('quantity', 1))
                
                item_data['price'] = price
                total += (price * quantity)
                
                cart_items.append(item_data)
            except (ValueError, TypeError) as e:
                print(f"Error processing item {doc.id}: {str(e)}")
                continue

        return render_template('cart.html', 
                             cart_items=cart_items,
                             total=total, 
                             now=datetime.now())

    except Exception as e:
        print(f"Error loading cart: {str(e)}")
        flash('Unable to load cart items. Please try again.', 'error')
        return render_template('cart.html', 
                             cart_items=[],
                             total=0,
                             now=datetime.now())

@views.route('/submit-customize-request', methods=['POST'])
def submit_customize_request():
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': 'Please login to submit a request'})

    try:
        data = request.json
        db = firestore.client()

        # Get user details from Firebase Auth
        user = auth.get_user(session['user_id'])
        customer_name = user.display_name or user.email  # Use display name or fallback to email

        # Get product details
        product_ref = db.collection('products').document(data['product_id'])
        product = product_ref.get()

        if not product.exists:
            return jsonify({'success': False, 'error': 'Product not found'})

        product_data = product.to_dict()

        # Create customize request with actual user name
        customize_data = {
            'product_id': data['product_id'],
            'product_name': product_data['name'],
            'customer_id': session['user_id'],
            'customer_name': customer_name,  # Use the fetched name
            'width': data['width'],
            'height': data['height'],
            'instructions': data['instructions'],
            'status': 'pending',
            'created_at': firestore.SERVER_TIMESTAMP,
            'product_image': product_data.get('image_url', ''),
            'original_price': product_data.get('price', 0)
        }

        # Add to customize collection
        db.collection('customize_requests').add(customize_data)

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error submitting customize request: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@views.route('/transactions')
def transactions():
    try:
        db = firestore.client()
        user_id = session.get('user_id')

        # Get customize requests
        customize_ref = db.collection('customize_requests').where('customer_id', '==', user_id)
        customize_requests = []
        for doc in customize_ref.stream():
            request = doc.to_dict()
            request['id'] = doc.id
            customize_requests.append(request)

        # Get purchases
        purchases_ref = db.collection('purchases').where('user_id', '==', user_id)
        purchases = []
        for doc in purchases_ref.stream():
            purchase = doc.to_dict()
            purchase['id'] = doc.id
            purchases.append(purchase)

        return render_template('transactions.html', 
                            customize_requests=customize_requests,
                            purchases=purchases, 
                            now=datetime.now())
    except Exception as e:
        flash(f'Error loading transactions: {str(e)}', 'error')
        return redirect(url_for('views.home'))

@views.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    try:
        data = request.json
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please log in to add items to cart'})

        db = firestore.client()
        
        # Add to cart collection
        cart_item = {
            'user_id': user_id,
            'product_id': data['product_id'],
            'name': data['name'],
            'price': data['price'],
            'quantity': data['quantity'],
            'image_url': data['image_url'],
            'width': data['width'],
            'height': data['height'],
            'is_customized': data['is_customized'],
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('cart_items').add(cart_item)
        
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@views.route('/get-cart-count')
def get_cart_count():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'count': 0})
            
        db = firestore.client()
        cart_ref = db.collection('cart_items').where('user_id', '==', user_id)
        count = len(list(cart_ref.stream()))
        return jsonify({'count': count})
    except Exception as e:
        print(f"Error getting cart count: {str(e)}")
        return jsonify({'count': 0})

@views.route('/update-cart-quantity', methods=['POST'])
def update_cart_quantity():
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Invalid request format'}), 400
            
        data = request.get_json()
        item_id = data.get('item_id')
        new_quantity = int(data.get('quantity', 0))
        user_id = session.get('user_id')

        if not all([item_id, user_id]):
            return jsonify({'success': False, 'error': 'Missing required data'}), 400

        if not 1 <= new_quantity <= 10:
            return jsonify({'success': False, 'error': 'Invalid quantity'}), 400

        db = firestore.client()
        
        # Get the cart item
        cart_item_ref = db.collection('cart_items').document(item_id)
        cart_item = cart_item_ref.get()

        if not cart_item.exists:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        item_data = cart_item.to_dict()
        if item_data.get('user_id') != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Update the quantity
        cart_item_ref.update({
            'quantity': new_quantity,
            'updated_at': firestore.SERVER_TIMESTAMP
        })

        # Calculate item subtotal
        item_price = float(str(item_data.get('price', '0')).replace('₱', '').replace(',', ''))
        subtotal = item_price * new_quantity

        # Calculate new cart total
        cart_ref = db.collection('cart_items').where('user_id', '==', user_id)
        cart_items = cart_ref.stream()
        total = sum(
            float(str(item.to_dict().get('price', '0')).replace('₱', '').replace(',', '')) * 
            int(item.to_dict().get('quantity', 0)) 
            for item in cart_items
        )

        return jsonify({
            'success': True,
            'quantity': new_quantity,
            'subtotal': subtotal,
            'total': total
        })

    except ValueError as e:
        return jsonify({'success': False, 'error': 'Invalid number format'}), 400
    except Exception as e:
        print(f"Error updating cart quantity: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@views.route('/checkout')
def checkout():
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please login to proceed to checkout', 'error')
            return redirect(url_for('auth.login'))

        db = firestore.client()
        
        # Get cart items
        cart_items = []
        subtotal = 0
        shipping_fee = 150  # Fixed shipping fee, you can modify this based on your logic
        
        cart_ref = db.collection('cart_items').where('user_id', '==', user_id)
        cart_docs = cart_ref.stream()

        for doc in cart_docs:
            item_data = doc.to_dict()
            item_data['id'] = doc.id
            
            # Calculate price
            try:
                price = float(str(item_data.get('price', '0')).replace('₱', '').replace(',', ''))
                quantity = int(item_data.get('quantity', 1))
                
                item_data['price'] = price
                subtotal += (price * quantity)
                
                cart_items.append(item_data)
            except (ValueError, TypeError) as e:
                print(f"Error processing item {doc.id}: {str(e)}")
                continue

        # Calculate total
        total = subtotal + shipping_fee

        if not cart_items:
            flash('Your cart is empty', 'error')
            return redirect(url_for('views.cart'))

        # Get user details for pre-filling the form
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()

        return render_template('checkout.html',
                             cart_items=cart_items,
                             subtotal=subtotal,
                             shipping_fee=shipping_fee,
                             total=total,
                             user=user_data)

    except Exception as e:
        print(f"Error loading checkout page: {str(e)}")
        flash('Unable to load checkout page. Please try again.', 'error')
        return redirect(url_for('views.cart'))

@views.route('/place-order', methods=['POST'])
def place_order():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login to place order'})

        # Ensure we're getting JSON data
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Invalid request format'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Missing order data'}), 400

        # Validate the required fields
        required_fields = {
            'contact': ['firstName', 'lastName', 'email', 'phone'],
            'shipping': ['address', 'city', 'province', 'zipCode']
        }

        # Validate contact and shipping fields
        for field, subfields in required_fields.items():
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing {field} information'}), 400
            if not all(subfield in data[field] for subfield in subfields):
                return jsonify({'success': False, 'error': f'Missing required {field} details'}), 400

        # Validate payment_method separately
        payment_method = data.get('payment_method')
        if not payment_method:
            return jsonify({'success': False, 'error': 'Please select a payment method'}), 400

        # Validate payment method value
        valid_payment_methods = ['gcash', 'cod']
        if payment_method not in valid_payment_methods:
            return jsonify({'success': False, 'error': 'Invalid payment method selected'}), 400

        db = firestore.client()

        # Get cart items
        cart_ref = db.collection('cart_items').where('user_id', '==', user_id)
        cart_items = list(cart_ref.stream())

        if not cart_items:
            return jsonify({'success': False, 'error': 'Cart is empty'}), 400

        # Calculate totals
        items_data = []
        subtotal = 0

        for cart_item in cart_items:
            try:
                item = cart_item.to_dict()
                price = float(str(item.get('price', '0')).replace('₱', '').replace(',', ''))
                quantity = int(item.get('quantity', 1))
                item_total = price * quantity
                subtotal += item_total

                items_data.append({
                    'product_id': item.get('product_id'),
                    'name': item.get('name'),
                    'price': price,
                    'quantity': quantity,
                    'image_url': item.get('image_url'),
                    'is_customized': item.get('is_customized', False),
                    'width': item.get('width'),
                    'height': item.get('height'),
                    'subtotal': item_total
                })
            except (ValueError, TypeError) as e:
                print(f"Error processing cart item: {str(e)}")
                continue

        if not items_data:
            return jsonify({'success': False, 'error': 'Invalid cart items'}), 400

        shipping_fee = 150
        total = subtotal + shipping_fee

        # Generate order number
        order_count = len(list(db.collection('orders').stream()))
        order_number = f'ORD-{datetime.now().strftime("%Y%m%d")}-{order_count + 1:04d}'

        # Create order document
        order_data = {
            'order_number': order_number,
            'user_id': user_id,
            'user_email': auth.get_user(user_id).email,
            'contact': {
                'first_name': data['contact']['firstName'],
                'last_name': data['contact']['lastName'],
                'email': data['contact']['email'],
                'phone': data['contact']['phone']
            },
            'shipping': {
                'address': data['shipping']['address'],
                'city': data['shipping']['city'],
                'province': data['shipping']['province'],
                'zip_code': data['shipping']['zipCode']
            },
            'payment_method': data['payment_method'],
            'items': items_data,
            'subtotal': subtotal,
            'shipping_fee': shipping_fee,
            'total': total,
            'status': 'pending',
            'notes': data.get('notes', ''),
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'tracking_updates': [{
                'status': 'Order Placed',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'description': 'Your order has been received and is being processed.'
            }]
        }

        # Execute transaction
        transaction = db.transaction()

        @firestore.transactional
        def create_order_in_transaction(transaction, order_data):
            try:
                # Create the order
                order_ref = db.collection('orders').document()
                transaction.set(order_ref, order_data)

                # Create purchase record
                purchase_ref = db.collection('users').document(user_id).collection('purchases').document(order_ref.id)
                purchase_data = {
                    'order_id': order_ref.id,
                    'order_number': order_data['order_number'],
                    'total': order_data['total'],
                    'status': order_data['status'],
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'items_count': len(items_data),
                    'payment_method': order_data['payment_method'],
                    'shipping_address': f"{order_data['shipping']['address']}, {order_data['shipping']['city']}"
                }
                transaction.set(purchase_ref, purchase_data)

                # Clear cart items
                for cart_item in cart_items:
                    transaction.delete(cart_item.reference)

                return order_ref.id
            except Exception as e:
                print(f"Transaction error: {str(e)}")
                raise

        # Execute transaction
        try:
            order_id = create_order_in_transaction(transaction, order_data)
            return jsonify({
                'success': True,
                'orderId': order_id,
                'orderNumber': order_number,
                'message': 'Order placed successfully'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Failed to process order. Please try again.'
            }), 500

    except Exception as e:
        print(f"Error placing order: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to place order. Please try again.'
        }), 500

@views.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    try:
        data = request.json
        item_id = data['item_id']
        user_id = session.get('user_id')
        
        db = firestore.client()
        cart_item_ref = db.collection('cart_items').document(item_id)
        cart_item = cart_item_ref.get()
        
        if not cart_item.exists or cart_item.to_dict()['user_id'] != user_id:
            return jsonify({'success': False, 'error': 'Item not found'})
        
        # Delete the item
        cart_item_ref.delete()
        
        # Recalculate cart total
        cart_ref = db.collection('cart_items').where('user_id', '==', user_id)
        total = sum(float(item.to_dict().get('price', 0)) * int(item.to_dict().get('quantity', 0)) 
                   for item in cart_ref.stream())
        
        return jsonify({
            'success': True,
            'total': total
        })
        
    except Exception as e:
        print(f"Error removing cart item: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def calculate_cart_total(cart_items):
    total = 0
    for item in cart_items:
        item_price = float(item.get('price', 0))
        item_quantity = int(item.get('quantity', 0))
        total += item_price * item_quantity
    return total

@views.context_processor
def utility_processor():
    def get_cart_count():
        try:
            user_id = session.get('user_id')
            if not user_id:
                return 0
                
            db = firestore.client()
            cart_ref = db.collection('cart_items').where('user_id', '==', user_id)
            cart_docs = list(cart_ref.stream())
            return len(cart_docs)
        except Exception as e:
            print(f"Error getting cart count: {str(e)}")
            return 0
            
    return {
        'now': datetime.now(),
        'get_cart_count': get_cart_count
    }