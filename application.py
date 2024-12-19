from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import check_password_hash

from utils.auth import generate_token, login_required, get_user_from_request
from services.aws_service import AWSService
from models.user import User, Friend


# Initialize Flask app
application = Flask(__name__)
application.config['SECRET_KEY'] = 'your-secret-key'

# Configure CORS
CORS(application,
     supports_credentials=True,
     origins=["https://smartreferralhub.com", "http://localhost:5173"],
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

# Initialize AWS services
aws_service = AWSService()

@application.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        email = data.get('email').lower()
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Check if user exists
        if aws_service.get_user(email):
            return jsonify({"error": "User already exists"}), 400

        # Create new user
        if not aws_service.create_user(email, password):
            return jsonify({"error": "Failed to create user"}), 500

        # Generate token
        token = generate_token(email)

        return jsonify({
            "message": "Signup successful",
            "email": email,
            "token": token
        }), 200

    except Exception as e:
        print(f"Signup error: {str(e)}")
        return jsonify({"error": "Signup failed"}), 500

@application.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email').lower()
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Get user and verify password
        user_item = aws_service.get_user(email)
        if not user_item:
            return jsonify({"error": "Invalid credentials"}), 401

        user = User.from_dynamo_item(user_item)
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401
        if not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate token
        token = generate_token(email)

        return jsonify({
            "message": "Login successful",
            "email": email,
            "token": token
        }), 200

    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed"}), 500

@application.route('/api/check-auth', methods=['GET'])
def check_auth():
    user_email = get_user_from_request()
    if not user_email:
        return jsonify({
            "authenticated": False,
            "email": ""
        }), 200

    return jsonify({
        "authenticated": True,
        "email": user_email
    }), 200

@application.route('/api/logout', methods=['POST'])
def logout():
    return jsonify({"message": "Logout successful"}), 200

@application.route('/api/upload', methods=['POST'])
@login_required
def upload_files():
    try:
        user_email = get_user_from_request()
        if not user_email:
            return jsonify({"error": "User not authenticated"}), 401
        if not isinstance(user_email, str):
            return jsonify({"error": "Invalid user email"}), 401
            
        upload_errors = []
        uploaded_files = []
        
        # Process files
        files = {}
        for key in request.files:
            if key.endswith('[]'):
                category = key[:-2]
                if category not in files:
                    files[category] = []
                files[category].append(request.files[key])
            else:
                files[key] = [request.files[key]]

        # Upload files to S3
        for category, file_list in files.items():
            if category == 'testimonial':
                if file_list and file_list[0].filename:
                    url, original_name = aws_service.upload_file_to_s3(
                        file_list[0],
                        'testimonial',
                        user_email
                    )
                    if url:
                        uploaded_files.append({
                            'type': 'testimonial',
                            'url': url,
                            'name': original_name
                        })
                    else:
                        upload_errors.append({
                            'file': original_name or 'testimonial',
                            'error': 'Failed to upload testimonial video'
                        })
            else:
                for file in file_list:
                    if file and file.filename:
                        url, original_name = aws_service.upload_file_to_s3(
                            file,
                            category,
                            user_email
                        )
                        if url:
                            uploaded_files.append({
                                'type': category,
                                'url': url,
                                'name': original_name
                            })
                        else:
                            upload_errors.append({
                                'file': original_name or category,
                                'error': f'Failed to upload {category} file'
                            })

        return jsonify({
            "message": "Files processed successfully",
            "errors": upload_errors if upload_errors else None,
            "uploaded": uploaded_files
        }), 200

    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@application.route("/api/submit", methods=['POST'])
@login_required
def submit():
    try:
        user_email = get_user_from_request()
        if not user_email:
            return jsonify({"error": "User not authenticated"}), 401
        if not isinstance(user_email, str):
            return jsonify({"error": "Invalid user email"}), 401
            
        data = request.get_json()
        friends = data.get('friends', [])

        # Update user's friends list
        if not aws_service.update_user_friends(user_email, friends):
            return jsonify({"error": "Failed to update friends list"}), 500
        
        return jsonify({
            "message": "Form submitted successfully"
        }), 200
        
    except Exception as e:
        print(f"Submit error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@application.route('/api/terms/status', methods=['GET'])
@login_required
def check_terms_status():
    try:
        user_email = get_user_from_request()
        if not user_email:
            return jsonify({"error": "User not authenticated"}), 401
        if not isinstance(user_email, str):
            return jsonify({"error": "Invalid user email"}), 401
            
        has_accepted = aws_service.check_terms_accepted(user_email)
        
        return jsonify({
            "accepted": has_accepted
        }), 200
        
    except Exception as e:
        print(f"Check terms status error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@application.route('/api/terms/accept', methods=['POST'])
@login_required
def accept_terms():
    try:
        user_email = get_user_from_request()
        if not user_email:
            return jsonify({"error": "User not authenticated"}), 401
        if not isinstance(user_email, str):
            return jsonify({"error": "Invalid user email"}), 401
            
        success = aws_service.update_terms_acceptance(user_email, True)
        
        if success:
            return jsonify({"message": "Terms accepted successfully"}), 200
        else:
            return jsonify({"error": "Failed to accept terms"}), 500
        
    except Exception as e:
        print(f"Accept terms error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@application.route('/')
def index():
    return "Hello, World!"

if __name__ == "__main__":
    application.run()