import boto3
import os
from datetime import datetime
from dotenv import load_dotenv

def init_links():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get AWS credentials from environment variables
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if not aws_access_key_id or not aws_secret_access_key:
        print("Error: AWS credentials not found in environment variables")
        return
    
    try:
        dynamodb = boto3.client(
            'dynamodb',
            region_name='us-west-1',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        
        table_name = 'smart-referral-links'
        
        # Initial links data
        initial_links = [
            # Reviews
            {'step_name': 'reviews', 'platform': 'yelp', 'link': 'https://www.yelp.com/biz/credit-repair-co-lomita-5'},
            {'step_name': 'reviews', 'platform': 'facebook', 'link': 'https://www.facebook.com/pg/Creditrepairconet/reviews/?ref=page_internal'},
            {'step_name': 'reviews', 'platform': 'sitejabber', 'link': 'https://www.sitejabber.com/reviews/creditrepairco.net'},
            
            # Social Media
            {'step_name': 'social media', 'platform': 'linkedin', 'link': 'https://www.linkedin.com/in/dimitri-malyshev-6582a78/'},
            {'step_name': 'social media', 'platform': 'youtube', 'link': 'https://www.youtube.com/channel/UCcqbg0H35b6CJkVWYpDjeXw/feed'},
            {'step_name': 'social media', 'platform': 'facebook', 'link': 'https://www.facebook.com/Creditrepairconet'},
            {'step_name': 'social media', 'platform': 'instagram', 'link': 'https://www.instagram.com/creditrepairco/'},
            
            # Content Sharing
            {'step_name': 'content', 'platform': 'facebook', 'link': 'https://www.facebook.com/Creditrepairconet'},
            {'step_name': 'content', 'platform': 'instagram', 'link': 'https://www.instagram.com/creditrepairco/'},
            
            # Tagging
            {'step_name': 'tagging', 'platform': 'facebook', 'link': 'https://www.facebook.com/Creditrepairconet'},
            {'step_name': 'tagging', 'platform': 'instagram', 'link': 'https://www.instagram.com/creditrepairco/'}
        ]

        # Insert initial links
        for link_data in initial_links:
            link = {
                'id': {'S': f"{link_data['step_name']}#{link_data['platform']}"},
                'step_name': {'S': link_data['step_name']},
                'platform': {'S': link_data['platform']},
                'link': {'S': link_data['link']},
                'created_at': {'N': str(int(datetime.now().timestamp()))}
            }
            try:
                response = dynamodb.put_item(
                    TableName=table_name,
                    Item=link
                )
                print(f"Added link: {link_data['step_name']} - {link_data['platform']}")
            except Exception as e:
                print(f"Error adding link {link_data['step_name']} - {link_data['platform']}: {str(e)}")
                
    except Exception as e:
        print(f"Error connecting to DynamoDB: {str(e)}")

if __name__ == "__main__":
    init_links()
