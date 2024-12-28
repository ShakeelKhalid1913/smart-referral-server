from dataclasses import dataclass
from typing import List
from datetime import datetime

@dataclass
class ReferralLink:
    step_name: str  # reviews, social media, content, tagging
    platform: str   # social media name
    link: str       # actual URL
    created_at: datetime

    @classmethod
    def from_dynamo_item(cls, item):
        """Create a ReferralLink instance from DynamoDB item"""
        if not item:
            return None
            
        return cls(
            step_name=item['step_name']['S'],
            platform=item['platform']['S'],
            link=item['link']['S'],
            created_at=datetime.fromtimestamp(int(item['created_at']['N']))
        )

    def to_dynamo_item(self):
        """Convert ReferralLink instance to DynamoDB item format"""
        return {
            'id': {'S': f"{self.step_name}#{self.platform}"},  # Composite key
            'step_name': {'S': self.step_name},
            'platform': {'S': self.platform},
            'link': {'S': self.link},
            'created_at': {'N': str(int(self.created_at.timestamp()))}
        }
