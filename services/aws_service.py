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

        # Create tables if they don't exist
        self._create_users_table_if_not_exists()
        self._create_links_table_if_not_exists()
        self._create_companies_table_if_not_exists()

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
            
            # if user_email is "admin" then file name will be "post"
            if user_email == "admin":
                file_type = "post"
                unique_filename = f"post{os.path.splitext(original_filename)[1]}"
            
            current_referral_number = self.get_tota_referrals(user_email)
            
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
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except:
            return False
            
    def encode_key(self, key: str) -> str:
        """Encode the S3 key to a URL-safe string"""
        import base64
        return base64.urlsafe_b64encode(key.encode()).decode()
        
    def decode_key(self, encoded_key: str) -> str:
        """Decode the URL-safe string back to S3 key"""
        import base64
        return base64.urlsafe_b64decode(encoded_key.encode()).decode()
        
    def get_download_url(self, encoded_key: str):
        """Generate a pre-signed URL for downloading"""
        try:
            key = self.decode_key(encoded_key)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                    'ResponseContentDisposition': 'attachment'
                },
                ExpiresIn=300  # URL expires in 5 minutes
            )
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

    def create_user(self, email: str, password: str, name: str):
        """Create a new user in DynamoDB"""
        try:
            hashed_password = generate_password_hash(password)
            
            self.dynamodb.put_item(
                TableName=self.users_table,
                Item={
                    'email': {'S': email},
                    'password': {'S': hashed_password},
                    'name': {'S': name},
                    'terms_accepted': {'BOOL': False},
                    'created_at': {'S': datetime.utcnow().isoformat()},
                    'total_referrals': {'N': '0'},
                    'friends': {'L': []},  # Store as a 2D array
                    'referrals_score': {'L': []}
                }
            )
            return True
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

    def get_links_by_step(self, step_name: str):
        """Get all links for a specific step"""
        try:
            response = self.dynamodb.query(
                TableName=self.links_table,
                IndexName='StepNameIndex',
                KeyConditionExpression='step_name = :step_name',
                ExpressionAttributeValues={
                    ':step_name': {'S': step_name}
                }
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting links: {str(e)}")
            return []

    def update_link(self, step_name: str, platform: str, new_link: str):
        """Update a specific link"""
        try:
            self.dynamodb.update_item(
                TableName=self.links_table,
                Key={
                    'id': {'S': f"{step_name}#{platform}"}
                },
                UpdateExpression='SET #link = :link',
                ExpressionAttributeNames={
                    '#link': 'link'
                },
                ExpressionAttributeValues={
                    ':link': {'S': new_link}
                }
            )
            return True
        except Exception as e:
            print(f"Error updating link: {str(e)}")
            return False

    def get_all_clients(self):
        """Get all clients and their media from DynamoDB and S3"""
        # try:
            # Scan the users table to get all users
        response = self.dynamodb.scan(
            TableName=self.users_table
        )
        
        clients = {}
        for item in response.get('Items', []):
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
        
    def get_tota_referrals(self, email: str) -> int:
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