from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Friend:
    name: str
    email: str
    phone: str

@dataclass
class User:
    email: str
    password_hash: str
    friends: List[Friend]
    created_at: datetime

    @classmethod
    def from_dynamo_item(cls, item):
        """Create a User instance from DynamoDB item"""
        if not item:
            return None
            
        return cls(
            email=item['email']['S'],
            password_hash=item['password']['S'],
            friends=[
                Friend(**{k: v['S'] for k, v in friend['M'].items()})
                for friend in item.get('friends', {}).get('L', [])
            ],
            created_at=datetime.fromtimestamp(int(item['created_at']['N']))
        )

    def to_dynamo_item(self):
        """Convert User instance to DynamoDB item format"""
        return {
            'email': {'S': self.email},
            'password': {'S': self.password_hash},
            'friends': {'L': [
                {'M': {
                    'name': {'S': friend.name},
                    'email': {'S': friend.email},
                    'phone_number': {'S': friend.phone_number}
                }}
                for friend in self.friends
            ]},
            'created_at': {'N': str(int(self.created_at.timestamp()))}
        }
