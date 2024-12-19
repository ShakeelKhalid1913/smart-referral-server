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

    def get_user(self, email: str):
        """Get user from DynamoDB"""
        try:
            response = self.dynamodb.get_item(
                TableName='users',
                Key={'email': {'S': email}}
            )
            return response.get('Item')
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            return None

    def create_user(self, email: str, password: str) -> bool:
        """Create a new user in DynamoDB"""
        try:
            password_hash = generate_password_hash(password)
            self.dynamodb.put_item(
                TableName='users',
                Item={
                    'email': {'S': email},
                    'password': {'S': password_hash},
                    'friends': {'L': []},
                    'terms_accepted': {'BOOL': False},
                    'created_at': {'N': str(int(datetime.now().timestamp()))}
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
                TableName='users',
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
                TableName='users',
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
                TableName='users',
                Key={'email': {'S': email}},
                ProjectionExpression='terms_accepted'
            )
            if 'Item' in response:
                return response['Item'].get('terms_accepted', {'BOOL': False})['BOOL']
            return False
        except Exception as e:
            print(f"Error checking terms acceptance: {str(e)}")
            return False
