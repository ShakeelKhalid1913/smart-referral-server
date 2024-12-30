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

        # Create tables if they don't exist
        self._create_users_table_if_not_exists()
        self._create_links_table_if_not_exists()

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
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"{user_email}/{file_type}/{unique_filename}",
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
            # get predesigned url for admin/post/post.png 
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': 'admin/post/post.png'
                },
                ExpiresIn=3600
            )
            return response
        except Exception as e:
            print(f"Error getting post image: {str(e)}")
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
                    'friends': {'L': []},
                    'terms_accepted': {'BOOL': False},
                    'created_at': {'S': datetime.utcnow().isoformat()}
                }
            )
            return True
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return False

    def update_user_friends(self, email: str, friends: list):
        """Update user's friends list in DynamoDB"""
        try:
            # Convert friend data to DynamoDB format
            dynamo_friends = []
            for friend in friends:
                dynamo_friend = {
                    'M': {
                        'name': {'S': friend['name']},
                        'email': {'S': friend['email']},
                        'phone': {'S': str(friend['phone'])}
                    }
                }
                dynamo_friends.append(dynamo_friend)

            self.dynamodb.update_item(
                TableName=self.users_table,
                Key={'email': {'S': email}},
                UpdateExpression='SET friends = :friends',
                ExpressionAttributeValues={
                    ':friends': {'L': dynamo_friends}
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
        try:
            # Scan the users table to get all users
            response = self.dynamodb.scan(
                TableName=self.users_table,
                ProjectionExpression="email, #n, friends, terms_accepted",
                ExpressionAttributeNames={'#n': 'name'}
            )
            
            clients = []
            for item in response.get('Items', []):
                client = {
                    'email': item.get('email', {}).get('S', ''),
                    'name': item.get('name', {}).get('S', ''),
                    'terms_accepted': item.get('terms_accepted', {}).get('BOOL', False),
                    'friends': [],
                    'media': {}
                }
                
                # Convert DynamoDB friends list to Python list
                if 'friends' in item and 'L' in item['friends']:
                    client['friends'] = [
                        {
                            'name': friend_item['M']['name']['S'],
                            'phone': friend_item['M']['phone']['S'],
                            'email': friend_item['M']['email']['S']
                        }
                        for friend_item in item['friends']['L']
                    ]
                
                # List objects in S3 for this user's email
                try:
                    s3_response = self.s3_client.list_objects_v2(
                        Bucket=self.bucket_name,
                        Prefix=f"{client['email']}/"
                    )
                    
                    # Group media by step
                    for obj in s3_response.get('Contents', []):
                        key_parts = obj['Key'].split('/')
                        if len(key_parts) >= 3:  # email/step_name/filename
                            step_name = key_parts[1]
                            filename = key_parts[2]
                            
                            if step_name not in client['media']:
                                client['media'][step_name] = []
                                
                            # Generate pre-signed URL for the media file
                            url = self.s3_client.generate_presigned_url(
                                'get_object',
                                Params={
                                    'Bucket': self.bucket_name,
                                    'Key': obj['Key']
                                },
                                ExpiresIn=3600  # URL expires in 1 hour
                            )
                            
                            client['media'][step_name].append({
                                'filename': filename,
                                'url': url,
                                'uploaded_at': obj['LastModified'].isoformat()
                            })
                            
                except self.s3_client.exceptions.NoSuchKey:
                    # No media files found for this user
                    pass
                
                clients.append(client)
            
            return clients
            
        except Exception as e:
            print(f"Error getting clients: {str(e)}")
            raise e
