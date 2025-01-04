from dataclasses import dataclass
from typing import List
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
    total_referrals: int
    friends: List[List[Friend]]  # 2D list of Friend objects
    referrals_score: List[int]
    created_at: datetime

    @classmethod
    def from_dynamo_item(cls, item):
        """Create a User instance from DynamoDB item"""
        if not item:
            return None

        return cls(
            email=item['email']['S'],
            password_hash=item['password']['S'],
            created_at=datetime.fromtimestamp(int(item['created_at']['N'])),
            total_referrals=int(item['total_referrals']['N']),
            referrals_score=[int(x) for x in item['referrals_score']['L']],
            friends=[
                [
                    Friend(
                        name=friend['M']['name']['S'],
                        email=friend['M']['email']['S'],
                        phone=friend['M']['phone_number']['S']
                    )
                    for friend in friend_group['L']
                ]
                for friend_group in item['friends']['L']
            ]
        )

    def to_dynamo_item(self):
        """Convert User instance to DynamoDB item format"""
        return {
            'email': {'S': self.email},
            'password': {'S': self.password_hash},
            'created_at': {'N': str(int(self.created_at.timestamp()))},
            'total_referrals': {'N': str(self.total_referrals)},
            'referrals_score': {'L': [{'N': str(score)} for score in self.referrals_score]},
            'friends': {
                'L': [
                    {
                        'L': [
                            {
                                'M': {
                                    'name': {'S': friend.name},
                                    'email': {'S': friend.email},
                                    'phone_number': {'S': friend.phone}
                                }
                            }
                            for friend in friend_group
                        ]
                    }
                    for friend_group in self.friends
                ]
            }
        }
