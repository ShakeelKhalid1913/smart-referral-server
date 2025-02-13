import boto3
import os
from datetime import datetime
import random
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

class AWSService:
    def __init__(self):
        self.aws_access_key_id = os.environ.get('aws_access_key_id')
        self.aws_secret_access_key = os.environ.get('aws_secret_access_key')
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            region_name='us-west-1',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )
        
        # Initialize DynamoDB client
        self.dynamodb = boto3.client(
            'dynamodb',
            region_name='us-west-1',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )
        
        self.bucket_name = 'smartreferralhub-bucket'
        self.users_table = 'smart-referral-users'
        self.links_table = 'smart-referral-links'
        self.companies_table = 'smart-referral-companies'
        self.signup_tokens_table = 'smart-referral-signup-tokens'
        self.form_approvals_table = 'smart-referral-form-approvals'

        # Create tables if they don't exist
        self._create_users_table_if_not_exists()
        self._create_links_table_if_not_exists()
        self._create_companies_table_if_not_exists()
        # self._create_signup_tokens_table_if_not_exists()
        self._create_form_approvals_table_if_not_exists()

    def _create_users_table_if_not_exists(self):
        """Create the users table if it doesn't exist"""
        try:
            self.dynamodb.describe_table(TableName=self.users_table)
        except self.dynamodb.exceptions.ResourceNotFoundException:
            print(f"Creating users table: {self.users_table}")
            self.dynamodb.create_table(
                TableName=self.users_table,
                KeySchema=[
                    {'AttributeName': 'email', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'email', 'AttributeType': 'S'},
                    {'AttributeName': 'name', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            # Wait for the table to be created
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=self.users_table)
            print(f"Users table created: {self.users_table}")

    def _create_links_table_if_not_exists(self):
        """Create the links table if it doesn't exist"""
        try:
            self.dynamodb.describe_table(TableName=self.links_table)
        except self.dynamodb.exceptions.ResourceNotFoundException:
            print(f"Creating links table: {self.links_table}")
            self.dynamodb.create_table(
                TableName=self.links_table,
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},
                    {'AttributeName': 'step_name', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'StepNameIndex',
                        'KeySchema': [
                            {'AttributeName': 'step_name', 'KeyType': 'HASH'}
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            # Wait for the table to be created
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=self.links_table)
            print(f"Links table created: {self.links_table}")

    def _create_companies_table_if_not_exists(self):
        """Create the companies table if it doesn't exist"""
        try:
            self.dynamodb.describe_table(TableName=self.companies_table)
        except self.dynamodb.exceptions.ResourceNotFoundException:
            print(f"Creating companies table: {self.companies_table}")
            self.dynamodb.create_table(
                TableName=self.companies_table,
                KeySchema=[
                    {'AttributeName': 'email', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'email', 'AttributeType': 'S'},
                    {'AttributeName': 'subscription_status', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'SubscriptionStatusIndex',
                        'KeySchema': [
                            {'AttributeName': 'subscription_status', 'KeyType': 'HASH'}
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            
            # Wait for the table to be created
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=self.companies_table)
            print(f"Companies table created: {self.companies_table}")
            
            # Add default settings for new companies
            self.dynamodb.put_item(
                TableName=self.companies_table,
                Item={
                    'email': {'S': 'default'},
                    'subscription_status': {'S': 'default'},
                    'discount': {
                        'M': {
                            'limit': {'N': '100'},
                            'multiplier': {'N': '0.3'}
                        }
                    },
                    'hashtags': {
                        'L': []
                    }
                }
            )

    def _create_form_approvals_table_if_not_exists(self):
        """Create the form approvals table if it doesn't exist"""
        try:
            self.dynamodb.describe_table(TableName=self.form_approvals_table)
        except self.dynamodb.exceptions.ResourceNotFoundException:
            print(f"Creating form approvals table: {self.form_approvals_table}")
            self.dynamodb.create_table(
                TableName=self.form_approvals_table,
                KeySchema=[
                    {'AttributeName': 'form_id', 'KeyType': 'HASH'}  # form_id will be in format "useremail#form{number}"
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'form_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            # Wait for the table to be created
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=self.form_approvals_table)

    def generate_file_name(self, file_type: str) -> str:
        """Generate a unique file name with timestamp and random number"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = f"{random.randint(10000000, 99999999)}"
        return f"{timestamp}_{random_suffix}"

    def upload_file_to_s3(self, file, file_type: str, user_email: str):
        """Upload a file to S3 and return the URL and original filename"""
        try:
            original_filename = secure_filename(file.filename)
            unique_filename = self.generate_file_name(file_type)
            # add file extension
            unique_filename += os.path.splitext(original_filename)[1]
            content_type = file.content_type
            
            # check user_email is company_email
            company_email = self.get_company_by_email(user_email)
            
            # if user_email is "admin" then file name will be "post"
            if company_email is not None:
                file_type = "post"
                unique_filename = f"post{os.path.splitext(original_filename)[1]}"
                
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=f"{user_email}/{file_type}/{unique_filename}",
                    Body=file.read(),
                    ContentType=content_type
                )
                
                # Generate URL
                url = f"https://{self.bucket_name}.s3.amazonaws.com//{user_email}/{file_type}/{unique_filename}"
                return url, original_filename
            
            current_referral_number = self.get_total_referrals(user_email)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"{user_email}/{current_referral_number}/{file_type}/{unique_filename}",
                Body=file.read(),
                ContentType=content_type
            )
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.amazonaws.com/{user_email}/{file_type}/{unique_filename}"
            return url, original_filename
            
        except Exception as e:
            print(f"Error uploading file to S3: {str(e)}")
            return None, None
    
    def get_company_by_name(self, company_name):
        """Get company details from DynamoDB by company name
        
        Args:
            company_name (str): Name of the company to fetch
            
        Returns:
            dict: Company details if found, None otherwise
        """
        try:
            # Query the companies table using the name
            response = self.dynamodb.scan(
                TableName=self.companies_table,
                FilterExpression='contains(#name, :name)',
                ExpressionAttributeNames={
                    '#name': 'name'
                },
                ExpressionAttributeValues={
                    ':name': {'S': company_name}
                }
            )
            
            if 'Items' in response and len(response['Items']) > 0:
                item = response['Items'][0]
                return {
                    'email': item.get('email', {}).get('S'),
                    'name': item.get('name', {}).get('S'),
                    'subscription_status': item.get('subscription_status', {}).get('S'),
                    'phone': item.get('phone', {}).get('S'),
                    'website': item.get('website', {}).get('S')
                }
            return None
            
        except Exception as e:
            print(f"Error getting company by name: {str(e)}")
            return None
    
    def get_company_by_email(self, email):
        try:
            response = self.dynamodb.get_item(
                TableName=self.companies_table,
                Key={'email': {'S': email}}
            )
            
            if 'Item' in response and 'company_name' in response['Item']:
                company_name = response['Item']['company_name']['S']
                return self.get_company_by_name(company_name)
            return None
        except Exception as e:
            print(f"Error getting company by email: {str(e)}")
            return None
            
    def get_post_image(self):
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket_name)
            if 'Contents' in response:
                for item in response['Contents']:
                    key = item['Key']
                    if key.endswith('.png') or key.endswith('.jpg') or key.endswith('.jpeg'):
                        return key
            return None
        except Exception as e:
            print(f"Error getting post image: {str(e)}")
            return None
        
    def get_company_by_user_email(self, email):
        try:
            response = self.dynamodb.get_item(
                TableName=self.users_table,
                Key={'email': {'S': email}}
            )
            
            if 'Item' in response and 'company_name' in response['Item']:
                company_name = response['Item']['company_name']['S']
                return self.get_company_by_name(company_name)
            return None
        except Exception as e:
            print(f"Error getting company by email: {str(e)}")
            return None
            
    def get_post_image(self):
        try:
            # Generate a clean download URL instead of direct S3 URL
            key = 'admin/post/post.png'
            if not self.check_file_exists(key):
                return None
                
            # Return a clean API endpoint URL instead of S3 URL
            return f"/media/download/{self.encode_key(key)}"
            
        except Exception as e:
            print(f"Error getting post image: {str(e)}")
            return None
            
    def check_file_exists(self, key: str):
        """Check if a file exists in S3"""
        try:
            print(f"Checking if file exists in S3: {key}")
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as e:
            print(f"File does not exist in S3: {key}, Error: {str(e)}")
            return False
            
    def encode_key(self, key: str) -> str:
        """Encode the S3 key to a URL-safe string"""
        import base64
        encoded = base64.urlsafe_b64encode(key.encode()).decode()
        print(f"Encoded key: {key} -> {encoded}")
        return encoded
        
    def decode_key(self, encoded_key: str) -> str:
        """Decode the URL-safe string back to S3 key"""
        import base64
        try:
            decoded = base64.urlsafe_b64decode(encoded_key.encode()).decode()
            print(f"Decoded key: {encoded_key} -> {decoded}")
            return decoded
        except Exception as e:
            print(f"Error decoding key: {encoded_key}, Error: {str(e)}")
            return None
        
    def get_download_url(self, encoded_key: str):
        """Generate a pre-signed URL for downloading"""
        try:
            key = self.decode_key(encoded_key)
            if not key:
                print("Failed to decode key")
                return None
                
            if not self.check_file_exists(key):
                print("File does not exist in S3")
                return None
                
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                    'ResponseContentDisposition': 'attachment'
                },
                ExpiresIn=300  # URL expires in 5 minutes
            )
            print(f"Generated presigned URL for key: {key}")
            return url
        except Exception as e:
            print(f"Error generating download URL: {str(e)}")
            return None

    def get_user(self, email: str):
        """Get user from DynamoDB"""
        try:
            response = self.dynamodb.get_item(
                TableName=self.users_table,
                Key={'email': {'S': email}}
            )
            return response.get('Item')
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            return None

    def create_user(self, user_data: dict) -> bool:
        """Create a new user in DynamoDB
        
        Args:
            user_data (dict): User data containing:
                - email: User's email (required)
                - password: Hashed password (required)
                - name: User's name (required)
                - company_name: Name of associated company (required for customers)
                - company_email: Email of associated company (required for customers)
                - created_at: ISO format timestamp
                
        Returns:
            bool: True if user was created successfully, False otherwise
        """
        try:
            # Validate required fields
            required_fields = ['email', 'password', 'name', 'company_name', 'company_email', 'created_at']
            if not all(field in user_data for field in required_fields):
                print(f"Missing required fields. Required: {required_fields}, Got: {list(user_data.keys())}")
                return False

            # Create DynamoDB item
            item = {
                'email': {'S': user_data['email']},
                'password': {'S': user_data['password']},
                'name': {'S': user_data['name']},
                'company_name': {'S': user_data['company_name']},
                'company_email': {'S': user_data['company_email']},
                'created_at': {'S': user_data['created_at']},
                'terms_accepted': {'BOOL': user_data.get('terms_accepted', False)},
                'friends': {'L': []},
                'referrals_score': {'L': []},
                'total_referrals': {'N': '0'}
            }
           
            # Try to create the user
            print(f"Creating user in DynamoDB: {user_data['email']}")
            self.dynamodb.put_item(
                TableName=self.users_table,
                Item=item,
                ConditionExpression='attribute_not_exists(email)'
            )
            print(f"Successfully created user: {user_data['email']}")
            return True
        except self.dynamodb.exceptions.ConditionalCheckFailedException:
            print(f"User already exists with email: {user_data['email']}")
            return False
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return False

    def update_user_friends(self, email: str, friends: list):
        """
        Update user's friends list in DynamoDB by adding a new group of friends
        Each group represents friends from one form submission
        """
        try:
            # First get the current friends list to check if it exists
            response = self.dynamodb.get_item(
                TableName=self.users_table,
                Key={'email': {'S': email}}
            )
            
            # Create friends group in DynamoDB format
            friends_group = {
                'L': [
                    {
                        'M': {
                            'name': {'S': friend.get('name', '')},
                            'email': {'S': friend.get('email', '')},
                            'phone_number': {'S': friend.get('phone', '')}
                        }
                    }
                    for friend in friends
                ]
            }

            if 'Item' not in response or 'friends' not in response['Item']:
                # If no friends list exists, create a new one with this group
                self.dynamodb.update_item(
                    TableName=self.users_table,
                    Key={'email': {'S': email}},
                    UpdateExpression='SET friends = :friends',
                    ExpressionAttributeValues={
                        ':friends': {'L': [friends_group]}
                    }
                )
            else:
                # If friends list exists, append new group
                self.dynamodb.update_item(
                    TableName=self.users_table,
                    Key={'email': {'S': email}},
                    UpdateExpression='SET friends = list_append(if_not_exists(friends, :empty_list), :new_group)',
                    ExpressionAttributeValues={
                        ':empty_list': {'L': []},
                        ':new_group': {'L': [friends_group]}
                    }
                )
            return True
        except Exception as e:
            print(f"Error updating friends: {str(e)}")
            return False

    def update_terms_acceptance(self, email: str, accepted: bool) -> bool:
        """Update user's terms acceptance status"""
        try:
            self.dynamodb.update_item(
                TableName=self.users_table,
                Key={'email': {'S': email}},
                UpdateExpression='SET terms_accepted = :accepted',
                ExpressionAttributeValues={
                    ':accepted': {'BOOL': accepted}
                }
            )
            return True
        except Exception as e:
            print(f"Error updating terms acceptance: {str(e)}")
            return False

    def check_terms_accepted(self, email: str) -> bool:
        """Check if user has accepted terms"""
        try:
            response = self.dynamodb.get_item(
                TableName=self.users_table,
                Key={'email': {'S': email}},
                ProjectionExpression='terms_accepted'
            )
            if 'Item' in response:
                return response['Item'].get('terms_accepted', {'BOOL': False})['BOOL']
            return False
        except Exception as e:
            print(f"Error checking terms acceptance: {str(e)}")
            return False

    def get_links_by_step(self, company_name: str, step_name: str):
        """Get all links for a specific step and company using StepNameIndex"""
        try:
            # Query the secondary index
            response = self.dynamodb.query(
                TableName=self.links_table,
                IndexName='StepNameIndex',
                KeyConditionExpression='step_name = :step_name',
                FilterExpression='begins_with(id, :id_prefix)',
                ExpressionAttributeValues={
                    ':step_name': {'S': step_name},
                    ':id_prefix': {'S': f"{company_name}#"}
                }
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting links: {str(e)}")
            return []

    def update_link(self, company_name: str, step_name: str, platform: str, new_link: str):
        """Update a specific link"""
        try:
            # Construct the id key with company_name, step_name, and platform
            id_key = f"{company_name}#{step_name}#{platform}"
            
            # Perform the update operation
            self.dynamodb.update_item(
                TableName=self.links_table,
                Key={
                    'id': {'S': id_key}  # Update the id key with the new format
                },
                UpdateExpression='SET #link = :link',
                ExpressionAttributeNames={
                    '#link': 'link'  # Map 'link' to avoid reserved keywords
                },
                ExpressionAttributeValues={
                    ':link': {'S': new_link}  # Bind the new link value
                }
            )
            return True
        except Exception as e:
            print(f"Error updating link: {str(e)}")
            return False

    def get_all_clients(self, company_email):
        """Get all clients and their media from DynamoDB and S3"""
        # try:
            # Scan the users table to get all users
        response = self.dynamodb.scan(
            TableName=self.users_table
        )
        
        clients = {}
        for item in response.get('Items', []):
            # if item has company email, then it's a client
            if item.get('company_email', {}).get('S', '') != company_email:
                continue
            total_referrals = item.get('total_referrals', {}).get('N', '0')
            email = item.get('email', {}).get('S', '')
            name = item.get('name', {}).get('S', '')
            terms_accepted = item.get('terms_accepted', {}).get('BOOL', False)
            friends = item.get('friends', {}).get('L', [])
            referrals_score = item.get('referrals_score', {}).get('L', [])
                            
            client = {
                'email': email,
                'name': name,
                'terms_accepted': terms_accepted,
                'total_referrals': total_referrals,
            }
            clients[email] = {}
            clients[email]['info'] = client
            clients[email]['data'] = []
            
            # get list of friends
            friends = item.get('friends', {}).get('L', [])
            # get list of scores
            referrals_score = item.get('referrals_score', {}).get('L', [])
            
            for i in range(int(total_referrals)):
                client_single_referral_data = {}
                client_single_referral_data['status'] = self.get_form_approval_status(email, i)
                
                client_single_referral_data['score'] = referrals_score[i].get('N', '0')
                
                # get ith group of friends
                friends_group = friends[i].get('L', [])
                
                client_single_referral_data['friends'] = []
                for j in range(len(friends_group)):
                    client_single_referral_data['friends'].append({
                        'name': friends_group[j].get('M', {}).get('name', {}).get('S', ''),
                        'email': friends_group[j].get('M', {}).get('email', {}).get('S', ''),
                        'phone': friends_group[j].get('M', {}).get('phone_number', {}).get('S', '')
                    })
                    
                    
                    
                try:
                    s3_response = self.s3_client.list_objects_v2(
                        Bucket=self.bucket_name,
                        Prefix=f"{email}/{i}/"
                    )
                    
                    client_single_referral_data['media'] = {}
                    
                    # Group media by step
                    for obj in s3_response.get('Contents', []):
                        key_parts = obj['Key'].split('/')
                        if len(key_parts) >= 4:
                            
                            step_name = key_parts[2]
                            filename = key_parts[3]
                            
                            if step_name not in client_single_referral_data['media']:
                                client_single_referral_data['media'][step_name] = []
                                
                            # Generate pre-signed URL for the media file
                            url = self.s3_client.generate_presigned_url(
                                'get_object',
                                Params={
                                    'Bucket': self.bucket_name,
                                    'Key': obj['Key']
                                },
                                ExpiresIn=3600  # URL expires in 1 hour
                            )
                            
                            client_single_referral_data['media'][step_name].append({
                                'filename': filename,
                                'url': url,
                                'uploaded_at': obj['LastModified'].isoformat()
                            })
                            
                    
                except self.s3_client.exceptions.NoSuchKey as e:
                    print(e)
                
                clients[email]['data'].append(client_single_referral_data)
        return clients
            
        # except Exception as e:
        #     print(f"Error getting clients: {str(e)}")
        #     raise e
        
    def get_total_referrals(self, email: str) -> int:
        try:
            response = self.dynamodb.get_item(
                TableName=self.users_table,
                Key={'email': {'S': email}}
            )
            return int(response.get('Item', {}).get('total_referrals', {}).get('N', '0'))
        except Exception as e:
            print(f"Error getting total referrals: {str(e)}")
            return 0

    def update_user_total_referrals(self, email: str):
        try:
            # update total referrals + 1
            self.dynamodb.update_item(
                TableName=self.users_table,
                Key={'email': {'S': email}},
                UpdateExpression='SET total_referrals = total_referrals + :inc',
                ExpressionAttributeValues={
                    ':inc': {'N': '1'}
                }
            )
            return True
        except Exception as e:
            print(f"Error updating total referrals: {str(e)}")
            return False
    
    def update_referrals_numbers(self, email: str, referral_score: int):
        try:
            self.update_user_total_referrals(email)
            # append new score in referrals_score list
            self.dynamodb.update_item(
                TableName=self.users_table,
                Key={'email': {'S': email}},
                UpdateExpression='SET referrals_score = list_append(if_not_exists(referrals_score, :empty_list), :new_score)',
                ExpressionAttributeValues={
                    ':empty_list': {'L': []},
                    ':new_score': {'L': [{'N': str(referral_score)}]}  # Format as DynamoDB number type
                }
            )
            return True
        except Exception as e:
            print(f"Error updating referrals numbers: {str(e)}")
            return False

    def get_item(self, table_name: str, key: dict) -> dict:
        """Get an item from DynamoDB table"""
        try:
            response = self.dynamodb.get_item(
                TableName=table_name,
                Key={k: {'S': v} for k, v in key.items()}
            )
            return response.get('Item')
        except Exception as e:
            print(f"Error getting item from {table_name}: {str(e)}")
            return None

    def put_item(self, table_name: str, item: dict) -> bool:
        """Put an item into DynamoDB table"""
        try:
            # Convert Python types to DynamoDB types
            dynamodb_item = {}
            for k, v in item.items():
                if isinstance(v, str):
                    dynamodb_item[k] = {'S': v}
                elif isinstance(v, bool):
                    dynamodb_item[k] = {'BOOL': v}
                elif isinstance(v, (int, float)):
                    dynamodb_item[k] = {'N': str(v)}
                else:
                    dynamodb_item[k] = {'S': str(v)}

            self.dynamodb.put_item(
                TableName=table_name,
                Item=dynamodb_item
            )
            return True
        except Exception as e:
            print(f"Error putting item into {table_name}: {str(e)}")
            return False

    def query_items(self, table_name: str, index_name: str, key_condition: dict) -> list:
        """Query items from DynamoDB table using a secondary index"""
        try:
            # Build the key condition expression and attribute values
            key_condition_expr = []
            expr_attr_names = {}
            expr_attr_values = {}
            
            for k, v in key_condition.items():
                key_condition_expr.append(f"#{k} = :{k}")
                expr_attr_names[f"#{k}"] = k
                if isinstance(v, str):
                    expr_attr_values[f":{k}"] = {'S': v}
                elif isinstance(v, bool):
                    expr_attr_values[f":{k}"] = {'BOOL': v}
                elif isinstance(v, (int, float)):
                    expr_attr_values[f":{k}"] = {'N': str(v)}
                else:
                    expr_attr_values[f":{k}"] = {'S': str(v)}

            response = self.dynamodb.query(
                TableName=table_name,
                IndexName=index_name,
                KeyConditionExpression=' AND '.join(key_condition_expr),
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values
            )
            
            return response.get('Items', [])
        except Exception as e:
            print(f"Error querying items from {table_name}: {str(e)}")
            return []

    def get_company_settings(self, company_email: str) -> dict:
        """Get company-specific settings from DynamoDB
        
        Args:
            company_email: Company's email
            
        Returns:
            dict: Company settings including discount and hashtags
        """
        try:
            response = self.dynamodb.get_item(
                TableName=self.companies_table,
                Key={'email': {'S': company_email}},
                ProjectionExpression='discount, hashtags'
            )
            
            if 'Item' in response:
                item = response['Item']
                return {
                    'discount': item.get('discount', {}).get('M', {}).get('limit', {}).get('N', '100'),
                    'multiplier': item.get('discount', {}).get('M', {}).get('multiplier', {}).get('N', '0.3'),
                    'hashtags': [tag['S'] for tag in item.get('hashtags', {}).get('L', [])]
                }
            
            # Return default values if no settings found
            return {
                'discount': '100',
                'multiplier': '0.3',
                'hashtags': []
            }
            
        except Exception as e:
            print(f"Error getting company settings: {str(e)}")
            return None
            
    def update_company_settings(self, company_email: str, settings: dict) -> bool:
        """Update company-specific settings in DynamoDB
        
        Args:
            company_email: Company's email
            settings: Dict containing settings to update:
                - discount: Score limit for discount
                - multiplier: Discount multiplier
                - hashtags: List of hashtags
                
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            update_expr_parts = []
            expr_attr_values = {}
            
            # Update discount settings if provided
            if 'discount' in settings or 'multiplier' in settings:
                discount_attr = {
                    'M': {
                        'limit': {'N': str(settings.get('discount', '100'))},
                        'multiplier': {'N': str(settings.get('multiplier', '0.3'))}
                    }
                }
                update_expr_parts.append('discount = :discount')
                expr_attr_values[':discount'] = discount_attr
            
            # Update hashtags settings if provided
            if 'hashtags' in settings:
                hashtags_attr = {
                    'L': [{'S': tag} for tag in settings.get('hashtags', [])]
                }
                update_expr_parts.append('hashtags = :hashtags')
                expr_attr_values[':hashtags'] = hashtags_attr
            
            if not update_expr_parts:
                return True  # Nothing to update
                
            update_expression = 'SET ' + ', '.join(update_expr_parts)
            
            self.dynamodb.update_item(
                TableName=self.companies_table,
                Key={'email': {'S': company_email}},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expr_attr_values
            )
            return True
            
        except Exception as e:
            print(f"Error updating company settings: {str(e)}")
            return False

    def get_post_settings(self, company_email: str) -> dict:
        """Get company post settings including hashtags and post image
        
        Args:
            company_email: Company's email
            
        Returns:
            dict: Post settings including hashtags list and post image URL
        """
        try:
            # Get hashtags from DynamoDB
            response = self.dynamodb.get_item(
                TableName=self.companies_table,
                Key={'email': {'S': company_email}},
                ProjectionExpression='hashtags'
            )
            
            hashtags = []
            if 'Item' in response and 'hashtags' in response['Item']:
                hashtags = [tag['S'] for tag in response['Item']['hashtags'].get('L', [])]
            
            # Get post image from S3
            post_image_url = None
            try:
                # List objects in the company's post directory
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=f"{company_email}/post/",
                    MaxKeys=1
                )
                
                # Get the first image if any exists
                if 'Contents' in response and len(response['Contents']) > 0:
                    key = response['Contents'][0]['Key']
                    post_image_url = f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
            except Exception as e:
                print(f"Error getting post image: {str(e)}")
            
            return {
                'hashtags': hashtags,
                'media': post_image_url
            }
            
        except Exception as e:
            print(f"Error getting post settings: {str(e)}")
            return {
                'hashtags': [],
                'media': None
            }
  
    def init_links(self, company_name: str, company_web: str):
        # Initial links data
        initial_links = [
            # Reviews
            {'step_name': 'reviews', 'platform': 'yelp', 'link': company_web},
            {'step_name': 'reviews', 'platform': 'facebook', 'link': company_web},
            {'step_name': 'reviews', 'platform': 'sitejabber', 'link': company_web},
            
            # Social Media
            {'step_name': 'social media', 'platform': 'linkedin', 'link': company_web},
            {'step_name': 'social media', 'platform': 'youtube', 'link': company_web},
            {'step_name': 'social media', 'platform': 'facebook', 'link': company_web},
            {'step_name': 'social media', 'platform': 'instagram', 'link': company_web},
            
            # Content Sharing
            {'step_name': 'content', 'platform': 'facebook', 'link': company_web},
            {'step_name': 'content', 'platform': 'instagram', 'link': company_web},
            
            # Tagging
            {'step_name': 'tagging', 'platform': 'facebook', 'link': company_web},
            {'step_name': 'tagging', 'platform': 'instagram', 'link': company_web}
        ]

        # Insert initial links
        for link_data in initial_links:
            link = {
                'id': {'S': f"{company_name}#{link_data['step_name']}#{link_data['platform']}"},
                'step_name': {'S': link_data['step_name']},
                'platform': {'S': link_data['platform']},
                'link': {'S': link_data['link']},
                'created_at': {'N': str(int(datetime.now().timestamp()))}
            }
            try:
                response = self.dynamodb.put_item(
                    TableName=self.links_table,
                    Item=link
                )
                print(f"Added link: {link_data['step_name']} - {link_data['platform']}")
            except Exception as e:
                print(f"Error adding link {link_data['step_name']} - {link_data['platform']}: {str(e)}")

    def get_file_url(self, key: str) -> str:
        """Generate a presigned URL for the given S3 key"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=3600  # URL expires in 1 hour
            )
            print(f"Generated presigned URL for key: {key}")
            return url
        except Exception as e:
            print(f"Error generating file URL: {str(e)}")
            return None

    def update_form_approval_status(self, user_email: str, form_number: int, is_approved: bool, reason: str = None):
        """Update the approval status of a specific form
        Args:
            user_email (str): Email of the user who submitted the form
            form_number (int): Number of the form
            is_approved (bool): Whether the form is approved or not
            reason (str, optional): Reason for rejection if form is not approved
        """
        form_id = f"{user_email}#form{form_number}"
        try:
            item = {
                'form_id': {'S': form_id},
                'is_approved': {'BOOL': is_approved},
                'updated_at': {'S': datetime.now().isoformat()}
            }
            
            # Add reason if provided or if form is rejected
            if reason is not None or not is_approved:
                item['reason'] = {'S': reason if reason is not None else ''}
            
            self.dynamodb.put_item(
                TableName=self.form_approvals_table,
                Item=item
            )
            return True
        except Exception as e:
            print(f"Error updating form approval status: {str(e)}")
            return False

    def get_form_approval_status(self, user_email: str, form_number: int):
        """Get the approval status of a specific form"""
        form_id = f"{user_email}#form{form_number}"
        try:
            response = self.dynamodb.get_item(
                TableName=self.form_approvals_table,
                Key={
                    'form_id': {'S': form_id}
                }
            )
            if 'Item' in response:
                result = {
                    'is_approved': response['Item']['is_approved']['BOOL'],
                    'updated_at': response['Item']['updated_at']['S']
                }
                # Add reason if it exists
                if 'reason' in response['Item']:
                    result['reason'] = response['Item']['reason']['S']
                return result
            return None
        except Exception as e:
            print(f"Error getting form approval status: {str(e)}")
            return None

    def get_all_form_approvals_for_user(self, user_email: str):
        """Get all form approval statuses for a specific user"""
        try:
            response = self.dynamodb.scan(
                TableName=self.form_approvals_table,
                FilterExpression='begins_with(form_id, :email)',
                ExpressionAttributeValues={
                    ':email': {'S': user_email}
                }
            )
            return [
                {
                    'form_id': item['form_id']['S'],
                    'is_approved': item['is_approved']['BOOL'],
                    'updated_at': item['updated_at']['S'],
                    'reason': item.get('reason', {}).get('S', '') if not item['is_approved']['BOOL'] else None
                }
                for item in response.get('Items', [])
            ]
        except Exception as e:
            print(f"Error getting user form approvals: {str(e)}")
            return []