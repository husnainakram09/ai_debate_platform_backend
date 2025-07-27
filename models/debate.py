from datetime import datetime
from typing import List, Dict, Optional
from bson import ObjectId

class Debate:
    def __init__(self, topic: str, creator_id: str = None, debate_id: str = None):
        # self._id = ObjectId(debate_id) if debate_id else ObjectId()
        self._id = ObjectId(debate_id) if debate_id and not isinstance(debate_id, ObjectId) else debate_id or ObjectId()
        self.topic = topic
        self.creator_id = creator_id
        self.status = "created"  # created, in_progress, completed, judged
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.participants = []  # List of personality names
        self.arguments = []  # List of DebateArgument dicts
        self.current_round = 1
        self.max_rounds = 3
        self.winner = None
        self.judge_decision = None
        self.judge_id = None
        self.votes = {}  # {personality_id: vote_count}
        self.total_votes = 0

    def _dict(self):
        return {
            # '_id': str(self._id),
            '_id': self._id,
            'topic': self.topic,
            'creator_id': self.creator_id,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'participants': self.participants,
            'arguments': self.arguments,
            'current_round': self.current_round,
            'max_rounds': self.max_rounds,
            'winner': self.winner,
            'judge_decision': self.judge_decision,
            'judge_id': self.judge_id,
            'votes': self.votes,
            'total_votes': self.total_votes
        }
    
    def to_dict(self):
        data = self._dict()
        data['_id'] = str(self._id)  # Convert to string only for API
        for arg in data['arguments']:
            if '_id' in arg and isinstance(arg['_id'], ObjectId):
                arg['_id'] = str(arg['_id'])
            # if 'personality_id' in arg and isinstance(arg['personality_id'], ObjectId):
            #     arg['personality_id'] = str(arg['personality_id'])
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        # debate = cls(data['topic'], data.get('creator_id'), str(data['_id']))
        debate = cls(data['topic'], data.get('creator_id'), data['_id'])
        debate.status = data.get('status', 'created')
        debate.created_at = data.get('created_at', datetime.utcnow())
        debate.updated_at = data.get('updated_at', datetime.utcnow())
        debate.participants = data.get('participants', [])
        debate.arguments = data.get('arguments', [])
        debate.current_round = data.get('current_round', 1)
        debate.max_rounds = data.get('max_rounds', 3)
        debate.winner = data.get('winner')
        debate.judge_decision = data.get('judge_decision')
        debate.judge_id = data.get('judge_id')
        debate.votes = data.get('votes', {})
        debate.total_votes = data.get('total_votes', 0)
        return debate
    
    def get_arguments_by_round(self, round_number: int) -> List[Dict]:
        """Get all arguments for a specific round"""
        return [arg for arg in self.arguments if arg.get('round_number') == round_number]
    
    def get_arguments_by_personality(self, personality_id: str) -> List[Dict]:
        """Get all arguments by a specific personality"""
        return [arg for arg in self.arguments if arg.get('personality_id') == personality_id]
    
    def is_complete(self) -> bool:
        """Check if debate is complete"""
        return self.status in ['completed', 'judged']
    
    def can_proceed_to_next_round(self) -> bool:
        """Check if debate can proceed to next round"""
        return (self.status == 'in_progress' 
                and self.current_round < self.max_rounds
                and len(self.get_arguments_by_round(self.current_round)) >= len(self.participants))

class DebateArgument:
    def __init__(self, personality_id: str, content: str, round_number: int, 
                 argument_id: str = None):
        self._id = ObjectId(argument_id) if argument_id else ObjectId()
        self.personality_id = personality_id
        self.content = content
        self.round_number = round_number
        self.timestamp = datetime.utcnow()
        self.votes = 0
        self.response_to = None  # ID of argument this responds to
        self.tags = []  # Optional tags for categorization
        
    def _dict(self):
        return {
            # '_id': str(self._id),
            '_id': self._id,
            'personality_id': self.personality_id,
            'content': self.content,
            'round_number': self.round_number,
            'timestamp': self.timestamp,
            'votes': self.votes,
            'response_to': self.response_to,
            'tags': self.tags
        }
    
    def to_dict(self):
        data = self._dict()
        data['_id'] = str(self._id)  # Convert to string only for API
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        argument = cls(
            data['personality_id'],
            data['content'],
            data['round_number'],
            str(data.get('_id'))
        )
        argument.timestamp = data.get('timestamp', datetime.utcnow())
        argument.votes = data.get('votes', 0)
        argument.response_to = data.get('response_to')
        argument.tags = data.get('tags', [])
        return argument
    
    def add_vote(self):
        """Add a vote to this argument"""
        self.votes += 1
    
    def is_recent(self, minutes: int = 30) -> bool:
        """Check if argument was created recently"""
        time_diff = datetime.utcnow() - self.timestamp
        return time_diff.total_seconds() < (minutes * 60)

class DebateRound:
    def __init__(self, round_number: int, debate_id: str):
        self.round_number = round_number
        self.debate_id = debate_id
        self.arguments = []
        self.started_at = datetime.utcnow()
        self.completed_at = None
        self.status = "in_progress"  # in_progress, completed
        
    def add_argument(self, argument: DebateArgument):
        """Add argument to this round"""
        self.arguments.append(argument)
    
    def complete_round(self):
        """Mark round as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
    
    def is_complete(self, expected_participants: int) -> bool:
        """Check if round is complete based on expected participants"""
        return len(self.arguments) >= expected_participants
    
    def _dict(self):
        return {
            'round_number': self.round_number,
            'debate_id': self.debate_id,
            'arguments': [arg._dict() for arg in self.arguments],
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'status': self.status
        }
    
    def to_dict(self):
        data = self.to_dict()
        data['_id'] = str(self._id)  # Convert to string only for API
        return data