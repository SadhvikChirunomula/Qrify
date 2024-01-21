from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import qrcode
import base64
from io import BytesIO
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

def load_users_from_json():
    try:
        with open('users.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Load existing users from JSON file
try:
    with open('users.json', 'r') as file:
        users = json.load(file)
except FileNotFoundError:
    users = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']

        # Check if the username exists
        user_id = get_user_id_by_username(username)
        user = users.get(user_id)
        if user:
            # If no addressId is provided, show all user details
            return render_template('user_details.html', user=user)
        else:
            return render_template('login.html', error='Invalid username')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get user details from the registration form
        name = request.form['name']
        phone_number = request.form['phone_number']

        # Check if the username is already taken
        if not is_username_available(name):
            return render_template('register.html', error='Username already taken')

        # Save user details
        user_id = len(users) + 1
        users[user_id] = {'name': name, 'phone_number': phone_number, 'addresses': [], 'qr_codes': []}

        # Log in the user and redirect to the address page
        session['user_id'] = user_id
        return redirect(url_for('address'))

    return render_template('register.html')

@app.route('/address', methods=['GET', 'POST'])
def address():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get the address and generate a unique ID for it
        address = request.form['address']
        address_id = generate_unique_address_id(user_id, address)

        # Add the address and its ID to the user's list of addresses
        users[user_id]['addresses'].append({'id': address_id, 'address': address})

        # Generate QR code for the address
        qr_code_data = f"https://qrify-nb3b.onrender.com/user?id={user_id}&addressId={address_id}"  # Updated QR code data
        qr = generate_qr_code(qr_code_data)

        # Save the QR code to a BytesIO object
        qr_bytesio = BytesIO()
        qr.save(qr_bytesio)
        qr_bytesio.seek(0)

        # Encode the QR code as base64
        qr_base64 = base64.b64encode(qr_bytesio.read()).decode('utf-8')

        # Save QR code data along with user details to JSON file
        users[user_id]['qr_codes'] = users[user_id].get('qr_codes', [])
        users[user_id]['qr_codes'].append({'address_id': address_id, 'address': address, 'qr_code': qr_base64})
        save_data_to_json()

        return render_template('address.html', user=users[user_id])

    return render_template('address.html', user=users[user_id])

def generate_unique_address_id(user_id, address):
    # Generate a unique address ID using a combination of user ID and address
    return f"{user_id}-{hash(address)}"

@app.route('/user', methods=['GET'])
def user():
    user_id = request.args.get('id')
    address_id = request.args.get('addressId')

    # Load user data
    users = load_users_from_json()

    user = users.get(user_id)
    if user:
        if address_id:
            # If addressId is provided, show details for that specific address
            address = next((addr for addr in user.get('addresses', []) if addr['id'] == address_id), None)
            if address:
                return render_template('user_details.html', user=user, address=address)
            else:
                return "Address not found."
        else:
            # If no addressId is provided, show all user details
            return render_template('user_details.html', user=user)

    return "User not found."


@app.route('/api/user/<int:user_id>/address/<int:address_id>')
def api_user_address(user_id, address_id):
    user = users.get(user_id)
    if user:
        address = next((addr for addr in user['addresses'] if addr['id'] == address_id), None)
        if address:
            user_details = {
                'name': user.get('name', 'N/A'),
                'phone_number': user.get('phone_number', 'N/A'),
                'address': address['address'],
                'qr_code': next((qr['qr_code'] for qr in user['qr_codes'] if qr['address_id'] == address_id), 'N/A')
            }
            return jsonify(user_details)
    return jsonify({'error': 'User or address not found'}), 404

def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(data)
    qr.make(fit=True)

    # Create the QR code image
    img = qr.make_image(fill_color="black", back_color="white")

    return img

def save_data_to_json():
    with open('users.json', 'w') as file:
        json.dump(users, file)

def is_username_available(username):
    return all(user['name'] != username for user in users.values())

def get_user_id_by_username(username):
    for user_id, user in users.items():
        if user['name'] == username:
            return user_id
    return None

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
