import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
import json
from datetime import datetime, timedelta
import jwt
from utils.auth import generate_token, login_required, get_user_from_request
from services.aws_service import AWSService

# Initialize Flask app
application = Flask(__name__)
application.config['SECRET_KEY'] = 'your-secret-key'
application.config['RECAPTCHA_SECRET_KEY'] = os.environ.get('RECAPTCHA_SECRET_KEY')

google_captcha_url = "https://www.google.com/recaptcha/api/siteverify"

# Configure CORS
CORS(application,
     supports_credentials=True,
     origins=["https://app.smartreferralhub.com", "http://localhost:5173"],
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["Content-Type", "Authorization"],
     max_age=3600)

# Initialize AWS services
aws_service = AWSService()

@application.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email').lower()
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Check if it's a company account
        company = aws_service.get_item(aws_service.companies_table, {'email': email})
        if company:
            stored_password = company.get('password', {}).get('S', '')
            if not check_password_hash(stored_password, password):
                return jsonify({"error": "Invalid credentials"}), 401

            # Generate token for company
            token = generate_token(email)

            return jsonify({
                "message": "Login successful",
                "email": email,
                "name": company.get('name', {}).get('S', ''),
                "token": token,
                "is_company": True,
                "subscription_plan": company.get('subscription_plan', {}).get('S', ''),
                "subscription_status": company.get('subscription_status', {}).get('S', '')
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
            "is_company": False
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
        
        # Get total referrals
        total_referrals = aws_service.get_total_referrals(user_email)
        
        aws_service.update_form_approval_status(user_email, total_referrals, False, "Not approved by the company yet.")
        
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
        # Get company from request
        company_name = request.args.get('company_name')
        if not company_name:
            return jsonify({"error": "Company name is required"}), 400
        links = aws_service.get_links_by_step(company_name, step_name.lower())
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
        # Get company from request
        company_name = request.args.get('company_name')
        if not company_name:
            return jsonify({"error": "Company name is required"}), 400
        data = request.get_json()
        step_name = data.get('step_name')
        platform = data.get('platform')
        new_link = data.get('link')

        if not all([step_name, platform, new_link]):
            return jsonify({"error": "Missing required fields"}), 400

        if aws_service.update_link(company_name, step_name.lower(), platform.lower(), new_link):
            return jsonify({"message": "Link updated successfully"}), 200
        return jsonify({"error": "Failed to update link"}), 500

    except Exception as e:
        print(f"Error updating link: {str(e)}")
        return jsonify({"error": "Failed to update link"}), 500

@application.route('/api/clients', methods=['GET'])
def get_all_clients():
    # get all clients from DynamoDB and then there media from s3 bucket {bucket/email/step_name/}
    try:
        company_email = request.args.get('company_email')
        if not company_email:
            return jsonify({"error": "Company email is required"}), 400
            
        clients = aws_service.get_all_clients(company_email)
        return jsonify({"clients": clients}), 200
    except Exception as e:
        print(f"Error getting clients: {str(e)}")
        return jsonify({"error": "Failed to get clients"}), 500
    
@application.route('/api/discount', methods=['GET', 'PUT'])
def get_discount():
    try:
        # Get company email from request
        company_email = request.args.get('company_email')
        if not company_email:
            return jsonify({"error": "Company email is required"}), 400

        if request.method == 'PUT':
            data = request.get_json()
            settings = {
                'discount': data.get('discount', '100'),
                'multiplier': data.get('multiplier', '0.3')
            }
            
            if aws_service.update_company_settings(company_email, settings):
                return jsonify({"message": "Discount updated successfully"}), 200
            return jsonify({"error": "Failed to update discount"}), 500
        
        # GET request
        settings = aws_service.get_company_settings(company_email)
        if settings:
            return jsonify({
                "discount": settings['discount'],
                "multiplier": settings['multiplier']
            }), 200
        return jsonify({"error": "Failed to get discount settings"}), 500
        
    except Exception as e:
        print(f"Error in discount endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@application.route('/api/posttags', methods=['GET', 'PUT'])
def posttags():
    try:
        # Get company email from request
        company_email = request.args.get('company_email')
        if not company_email:
            return jsonify({"error": "Company email is required"}), 400
            
        if request.method == 'PUT':
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

            # Upload file to S3
            url, original_name = aws_service.upload_file_to_s3(
                file,
                'media',
                company_email  # Use company email instead of 'admin'
            )
            
            if not url:
                return jsonify({"error": "Failed to upload media file"}), 500

            # Update company settings with new hashtags and image
            settings = {
                'hashtags': hashtags,
                'post_image': url
            }
            
            if not aws_service.update_company_settings(company_email, settings):
                return jsonify({"error": "Failed to update settings"}), 500

            return jsonify({
                "message": "Post updated successfully",
                "url": url,
                "original_name": original_name,
                "hashtags": hashtags
            }), 200

        # GET request
        settings = aws_service.get_post_settings(company_email)
        return jsonify(settings), 200
            
    except Exception as e:
        print(f"Error in posttags endpoint: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

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
    
# on form submitted update referrals in user table and referrals score list
@application.route('/api/update-referrals-numbers', methods=['POST'])
@login_required
def update_referrals_numbers():
    try:
        user_email = get_user_from_request()
        if not user_email:
            return jsonify({"error": "User not authenticated"}), 401
        if not isinstance(user_email, str):
            return jsonify({"error": "Invalid user email"}), 401
            
        data = request.get_json()
        referral_score = data.get('referral_score')
        
        success = aws_service.update_referrals_numbers(user_email, referral_score)
        
        if success:
            return jsonify({"message": "Referrals updated successfully"}), 200
        else:
            return jsonify({"error": "Failed to update referrals"}), 500
    except Exception as e:
        print(f"Update referrals error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@application.route('/api/signup-company', methods=['POST'])
def signup_company():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        phone = data.get('phone')
        website = data.get('website')
        subscription_plan = data.get('subscription_plan')
        
        # Check if required fields are present
        if not all([email, password, name, phone, website, subscription_plan]):
            return jsonify({"error": "All fields are required"}), 400
            
        # Check if company already exists
        existing_company = aws_service.get_item(aws_service.companies_table, {'email': email})
        if existing_company:
            return jsonify({"error": "Company already exists"}), 400
            
        # Create company record
        company_data = {
            'email': email,
            'name': name,
            'password': generate_password_hash(password),
            'phone': phone,
            'website': website,
            'subscription_plan': subscription_plan,
            'subscription_status': 'active',
            'subscription_start_date': datetime.now().isoformat(),
            'subscription_end_date': (datetime.now() + timedelta(days=365 if subscription_plan == 'yearly' else 30)).isoformat(),
            'created_at': datetime.now().isoformat(),
            'is_company': True
        }
        
        # Save company to DynamoDB
        aws_service.put_item(aws_service.companies_table, company_data)
        
        aws_service.init_links(name, website)
        
        # Generate JWT token
        token = jwt.encode(
            {
                'email': email,
                'name': name,
                'is_company': True,
                'exp': datetime.utcnow() + timedelta(days=1)
            },
            application.config['SECRET_KEY']
        )
        
        return jsonify({
            'token': token,
            'email': email,
            'name': name,
            'is_company': True,
            'subscription_plan': subscription_plan,
            'subscription_status': 'active'
        }), 200
        
    except Exception as e:
        print(f"Error in company signup: {str(e)}")
        return jsonify({"error": "Failed to create company account"}), 500

@application.route('/api/customer/signup', methods=['POST'])
def customer_signup():
    try:
        data = request.get_json()
        email = data.get('email').lower()
        password = data.get('password')
        name = data.get('name')
        company_name = data.get('company_name')
        recaptcha_token = data.get('token')
        
        import requests
        
        # Verify recaptcha
        response = requests.post(
            google_captcha_url,
            data={
                "secret": application.config['RECAPTCHA_SECRET_KEY'],
                "response": recaptcha_token
            }
        )
        print(response.json())
        if not response.json().get('success'):
            return jsonify({"error": "Invalid recaptcha"}), 400
        
        # Clean company name
        company_name = company_name.replace("-", " ")

        if not all([email, password, name, company_name]):
            return jsonify({"error": "All fields are required"}), 400

        # Check if company exists
        company = aws_service.get_company_by_name(company_name)
        if not company:
            return jsonify({"error": "Invalid company"}), 404

        # Get company email from company data
        company_email = company['email']
        if not company_email:
            return jsonify({"error": "Invalid company data"}), 500

        # Check if user already exists
        existing_user = aws_service.get_user(email)
        if existing_user:
            return jsonify({"error": "User already exists"}), 400

        # Create user
        user_data = {
            'email': email,
            'password': generate_password_hash(password),
            'name': name,
            'company_name': company_name,
            'company_email': company_email,
            'created_at': datetime.now().isoformat(),
            'terms_accepted': False,
            'friends': [],
            'referrals_score': [],
            'total_referrals': 0
        }
        
        if not aws_service.create_user(user_data):
            return jsonify({"error": "Failed to create user"}), 500

        return jsonify({"message": "User created successfully"}), 201

    except Exception as e:
        print(f"Error in customer signup: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    

# get company in which user is logged in
@application.route('/api/get-company-name', methods=['GET'])
def get_company_name():
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({"error": "Email is required"}), 400
        company = aws_service.get_company_by_user_email(email)
        if not company:
            return jsonify({"error": "Company not found"}), 404
        return jsonify({"company_name": company.get('name'), "company_email": company.get('email')}), 200
    except Exception as e:
        print(f"Error in get company name: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@application.route('/api/company-exists', methods=["POST"])
def company_exists():
    try:
        company_name = request.args.get('company_name')

        if not company_name:
            return jsonify({"error": "Company name is required"}), 400
        company = aws_service.get_company_by_name(company_name)
        if not company:
            return jsonify({"exists": False}), 200
        return jsonify({"exists": True}), 200
    except Exception as e:
        print(f"Error in company exists: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@application.route('/api/approve-form', methods=['POST'])
@login_required
def approve_form():
    """Endpoint to approve or disapprove a form submission"""
    try:
        # Get data from request
        data = request.get_json()
        email = data.get('email')
        form_number = data.get('formNumber')
        is_approved = data.get('isApproved')
        reason = data.get('reason', '')

        # Validate required fields
        if not all([email, isinstance(form_number, int), isinstance(is_approved, bool)]):
            return jsonify({"error": "Missing or invalid required fields"}), 400

        # If disapproving, reason is required
        if not is_approved and not reason:
            return jsonify({"error": "Reason is required for disapproval"}), 400

        # Get the current user (company) from the request
        current_user = get_user_from_request()
        if not current_user:
            return jsonify({"error": "Unauthorized"}), 401

        # Update form approval status
        success = aws_service.update_form_approval_status(
            user_email=email,
            form_number=form_number,
            is_approved=is_approved,
            reason=reason
        )

        if not success:
            return jsonify({"error": "Failed to update form status"}), 500

        return jsonify({
            "message": f"Form {'approved' if is_approved else 'disapproved'} successfully",
            "status": {
                "is_approved": is_approved,
                "reason": reason,
                "updated_at": datetime.now().isoformat()
            }
        }), 200

    except Exception as e:
        print(f"Error in approve form: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@application.route('/')
def index():
    return "Hello, World!"

if __name__ == "__main__":
    application.run(debug=True)