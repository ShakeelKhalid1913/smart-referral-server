import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from werkzeug.security import check_password_hash
import json

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
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["Content-Type", "Authorization"])

# Initialize AWS services
aws_service = AWSService()

@application.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        email = data.get('email').lower()
        password = data.get('password')
        name = data.get('name')

        if not email or not password or not name:
            return jsonify({"error": "Email, password, and name are required"}), 400

        # Check if user already exists
        existing_user = aws_service.get_user(email)
        if existing_user:
            return jsonify({"error": "User already exists"}), 409

        # Create new user
        if aws_service.create_user(email, password, name):
            token = generate_token(email)
            return jsonify({
                "message": "Signup successful",
                "email": email,
                "name": name,
                "token": token
            }), 201
        else:
            return jsonify({"error": "Failed to create user"}), 500

    except Exception as e:
        print(f"Error in signup: {str(e)}")
        return jsonify({"error": str(e)}), 500

@application.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email').lower()
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # check if it is admin from .env
        if email == os.environ.get('admin_email') and password == os.environ.get('admin_password'):
            return jsonify({
                "message": "Login successful",
                "email": email,
                "token": "admin-token",
                "is_admin": True
            }), 200

        # Get user and verify password
        user_item = aws_service.get_user(email)
        if not user_item:
            return jsonify({"error": "Invalid credentials"}), 401

        stored_password = user_item.get('password', {}).get('S', '')
        if not check_password_hash(stored_password, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate token
        token = generate_token(email)

        return jsonify({
            "message": "Login successful",
            "email": email,
            "name": user_item.get('name', {}).get('S', ''),
            "token": token,
            "is_admin": False
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
            # Remove array notation if present
            category = key[:-2] if key.endswith('[]') else key
            if category not in files:
                files[category] = []
            files[category].append(request.files[key])

        # Upload files to S3
        for category, file_list in files.items():
            # Map frontend category names to backend category names
            category_map = {
                'social_media': 'social',
                'content_sharing': 'content',
            }
            backend_category = category_map.get(category, category)
            
            if backend_category == 'testimonial':
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
                            backend_category,
                            user_email
                        )
                        if url:
                            uploaded_files.append({
                                'type': backend_category,
                                'url': url,
                                'name': original_name
                            })
                        else:
                            upload_errors.append({
                                'file': original_name or backend_category,
                                'error': f'Failed to upload {backend_category} file'
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

@application.route('/api/links/<step_name>', methods=['GET'])
def get_step_links(step_name):
    try:
        links = aws_service.get_links_by_step(step_name.lower())
        return jsonify({
            "links": [
                {
                    "step_name": item['step_name']['S'],
                    "platform": item['platform']['S'],
                    "link": item['link']['S']
                }
                for item in links
            ]
        }), 200
    except Exception as e:
        print(f"Error getting links: {str(e)}")
        return jsonify({"error": "Failed to get links"}), 500

@application.route('/api/links', methods=['PUT'])
def update_link():
    try:
        data = request.get_json()
        step_name = data.get('step_name')
        platform = data.get('platform')
        new_link = data.get('link')

        if not all([step_name, platform, new_link]):
            return jsonify({"error": "Missing required fields"}), 400

        if aws_service.update_link(step_name.lower(), platform.lower(), new_link):
            return jsonify({"message": "Link updated successfully"}), 200
        return jsonify({"error": "Failed to update link"}), 500

    except Exception as e:
        print(f"Error updating link: {str(e)}")
        return jsonify({"error": "Failed to update link"}), 500

@application.route('/api/clients', methods=['GET'])
def get_all_clients():
    # get all clients from DynamoDB and then there media from s3 bucket {bucket/email/step_name/}
    try:
        clients = aws_service.get_all_clients()
        return jsonify({"clients": clients}), 200
    except Exception as e:
        print(f"Error getting clients: {str(e)}")
        return jsonify({"error": "Failed to get clients"}), 500
    
@application.route('/api/percentage', methods=['GET', 'PUT'])
def percentage():
    filename = 'data/percentage.txt'
    if request.method == 'PUT':
        data = request.get_json()
        percentage = data.get('percentage')
        with open(filename, 'w') as f:
            f.write(str(percentage))
        return jsonify({"message": "Percentage updated successfully"}), 200
    
    with open(filename, 'r') as f:
        percentage = f.read()
    return jsonify({"percentage": percentage}), 200

@application.route('/api/posttags', methods=['GET', 'PUT'])
def posttags():
    filename = 'data/hashtags.txt'
    
    if request.method == 'PUT':
        try:
            # Handle file upload
            file = request.files.get('media')
            if not file:
                return jsonify({"error": "No media file provided"}), 400

            # Get hashtags from form data
            hashtags_json = request.form.get('hashtags')
            if not hashtags_json:
                return jsonify({"error": "No hashtags provided"}), 400

            try:
                hashtags = json.loads(hashtags_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid hashtags format"}), 400

            # Save hashtags
            with open(filename, 'w') as f:
                f.write('\n'.join(hashtags))

            # Upload file to S3
            url, original_name = aws_service.upload_file_to_s3(
                file,
                'media',
                'admin'
            )
            
            if not url:
                return jsonify({"error": "Failed to upload media file"}), 500

            return jsonify({
                "message": "Post updated successfully",
                "url": url,
                "original_name": original_name,
                "hashtags": hashtags
            }), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # GET request - return existing hashtags and media
    try:
        hashtags = []
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                hashtags = [line.strip() for line in f if line.strip()]

        media_url = aws_service.get_post_image()
        if not media_url:
            return jsonify({"error": "Failed to get media URL"}), 500
        
        return jsonify({
            "hashtags": hashtags,
            "media": media_url
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@application.route('/api/media/download/<encoded_key>')
def download_media(encoded_key):
    try:
        # Get the download URL from S3
        url = aws_service.get_download_url(encoded_key)
        if not url:
            return jsonify({"error": "File not found"}), 404
            
        # Redirect to the pre-signed URL
        return redirect(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@application.route('/')
def index():
    return "Hello, World!"

if __name__ == "__main__":
    application.run(debug=True)