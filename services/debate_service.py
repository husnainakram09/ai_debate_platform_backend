import logging
from typing import List, Optional
from datetime import datetime
from models.debate import Debate, DebateArgument
from services.personality_service import PersonalityService
from bson import ObjectId
import pymongo

logger = logging.getLogger(__name__)

class DebateService:
    def __init__(self, db):
        self.db = db
        self.debates_collection = db.debates
        self.personality_service = PersonalityService()
    
    def create_debate(self, topic: str, creator_id: str = None) -> Debate:
        """Create a new debate"""
        try:
            print('dateee',topic,creator_id)
            debate = Debate(topic, creator_id)
            # Get participating personalities
            personalities = self.personality_service.get_debate_personalities()
            debate.participants = [p.name for p in personalities]
            
            # Save to database
            result = self.debates_collection.insert_one(debate._dict())
            debate._id = result.inserted_id
            
            logger.info(f"Created debate with ID: {debate._id}, topic: {topic[:50]}...")
            return debate
            
        except Exception as e:
            logger.error(f"Error creating debate: {str(e)}")
            raise
    
    def get_debate(self, debate_id: str) -> Optional[Debate]:
        """Get a debate by ID"""
        try:
            debate_data = self.debates_collection.find_one({'_id': ObjectId(debate_id)})
            # debate_data = self.debates_collection.find_one({'_id': debate_id})
            if debate_data:
                return Debate.from_dict(debate_data)
            return None
        except Exception as e:
            logger.error(f"Error getting debate {debate_id}: {str(e)}")
            return None
    
    def get_debates_paginated(self, page: int = 1, limit: int = 10, status: str = None) -> List[Debate]:
        """Get debates with pagination"""
        try:
            skip = (page - 1) * limit
            query = {}
            
            if status:
                query['status'] = status
            
            debates_data = (self.debates_collection
                          .find(query)
                          .sort('created_at', -1)
                          .skip(skip)
                          .limit(limit))
            
            return [Debate.from_dict(data) for data in debates_data]
            
        except Exception as e:
            logger.error(f"Error getting paginated debates: {str(e)}")
            return []
    
    def delete_debate(self, debate_id: str) -> bool:
        """Delete a debate (admin function)"""
        try:
            result = self.debates_collection.delete_one({'_id': ObjectId(debate_id)})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted debate {debate_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting debate {debate_id}: {str(e)}")
            return False
    
    def get_debates_count(self, status: str = None) -> int:
        """Get total count of debates"""
        try:
            query = {}
            if status:
                query['status'] = status
            
            return self.debates_collection.count_documents(query)
            
        except Exception as e:
            logger.error(f"Error counting debates: {str(e)}")
            return 0
    
    def start_debate(self, debate_id: str) -> Optional[Debate]:
        """Start a debate"""
        try:
            result = self.debates_collection.update_one(
                {'_id': ObjectId(debate_id), 'status': 'created'},
                # {'_id': debate_id, 'status': 'created'},
                {
                    '$set': {
                        'status': 'in_progress',
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Started debate {debate_id}")
                return self.get_debate(debate_id)
            
            logger.warning(f"Could not start debate {debate_id} - may already be started")
            return None
            
        except Exception as e:
            logger.error(f"Error starting debate {debate_id}: {str(e)}")
            return None
    
    def add_argument(self, debate_id: str, argument: DebateArgument) -> bool:
        """Add an argument to a debate"""
        try:
            result = self.debates_collection.update_one(
                {'_id': ObjectId(debate_id)},
                {
                    '$push': {'arguments': argument._dict()},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Added argument from {argument.personality_id} to debate {debate_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding argument to debate {debate_id}: {str(e)}")
            return False
    
    def add_multiple_arguments(self, debate_id: str, arguments: List[DebateArgument]) -> bool:
        """Add multiple arguments to a debate at once"""
        try:
            argument_dicts = [arg._dict() for arg in arguments]
            
            result = self.debates_collection.update_one(
                {'_id': ObjectId(debate_id)},
                {
                    '$push': {'arguments': {'$each': argument_dicts}},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Added {len(arguments)} arguments to debate {debate_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding multiple arguments to debate {debate_id}: {str(e)}")
            return False
    
    def update_round(self, debate_id: str, round_number: int) -> bool:
        """Update the current round of a debate"""
        try:
            result = self.debates_collection.update_one(
                {'_id': ObjectId(debate_id)},
                {
                    '$set': {
                        'current_round': round_number,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated debate {debate_id} to round {round_number}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating round for debate {debate_id}: {str(e)}")
            return False
    
    def end_debate(self, debate_id: str) -> bool:
        """End a debate"""
        try:
            result = self.debates_collection.update_one(
                {'_id': ObjectId(debate_id)},
                {
                    '$set': {
                        'status': 'completed',
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Ended debate {debate_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error ending debate {debate_id}: {str(e)}")
            return False
    
    def judge_debate(self, debate_id: str, winner: str, reasoning: str = "", judge_id: str = None) -> bool:
        """Judge a debate and declare winner"""
        try:
            result = self.debates_collection.update_one(
                {'_id': ObjectId(debate_id)},
                {
                    '$set': {
                        'status': 'judged',
                        'winner': winner,
                        'judge_decision': reasoning,
                        'judge_id': judge_id,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Update personality stats
                self.personality_service.update_personality_stats(winner, True)
                
                # Update stats for all other participants
                debate = self.get_debate(debate_id)
                if debate:
                    for participant in debate.participants:
                        if participant != winner:
                            self.personality_service.update_personality_stats(participant, False)
                
                logger.info(f"Judged debate {debate_id}, winner: {winner}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error judging debate {debate_id}: {str(e)}")
            return False
    
    def add_vote(self, debate_id: str, personality_id: str, voter_id: str = "anonymous") -> bool:
        """Add a vote for a personality in a debate"""
        try:
            # Check if voter has already voted
            debate = self.get_debate(debate_id)
            if not debate:
                return False
            
            # Initialize votes if not present
            if not hasattr(debate, 'voter_records'):
                voter_records = {}
            else:
                voter_records = getattr(debate, 'voter_records', {})
            
            # Check if voter already voted
            if voter_id in voter_records:
                logger.warning(f"Voter {voter_id} already voted in debate {debate_id}")
                return False
            
            # Add vote
            result = self.debates_collection.update_one(
                {'_id': ObjectId(debate_id)},
                {
                    '$inc': {
                        f'votes.{personality_id}': 1,
                        'total_votes': 1
                    },
                    '$set': {
                        f'voter_records.{voter_id}': personality_id,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Added vote for {personality_id} in debate {debate_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding vote to debate {debate_id}: {str(e)}")
            return False
    
    def get_recent_debates(self, limit: int = 10) -> List[Debate]:
        """Get recent debates"""
        try:
            debates_data = (self.debates_collection
                          .find()
                          .sort('created_at', -1)
                          .limit(limit))
            
            return [Debate.from_dict(data) for data in debates_data]
            
        except Exception as e:
            logger.error(f"Error getting recent debates: {str(e)}")
            return []
    
    def get_debates_by_status(self, status: str, limit: int = None) -> List[Debate]:
        """Get debates by status"""
        try:
            query = {'status': status}
            cursor = self.debates_collection.find(query).sort('created_at', -1)
            
            if limit:
                cursor = cursor.limit(limit)
            
            return [Debate.from_dict(data) for data in cursor]
            
        except Exception as e:
            logger.error(f"Error getting debates by status {status}: {str(e)}")
            return []
    
    def get_personality_leaderboard(self):
        """Get personality leaderboard based on wins"""
        return self.personality_service.get_leaderboard()
    
    def get_total_arguments_count(self) -> int:
        """Get total number of arguments across all debates"""
        try:
            pipeline = [
                {'$project': {'argument_count': {'$size': '$arguments'}}},
                {'$group': {'_id': None, 'total': {'$sum': '$argument_count'}}}
            ]
            
            result = list(self.debates_collection.aggregate(pipeline))
            
            if result:
                return result[0]['total']
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting total arguments count: {str(e)}")
            return 0
    
    def get_debate_analytics(self, debate_id: str) -> dict:
        """Get analytics for a specific debate"""
        try:
            debate = self.get_debate(debate_id)
            if not debate:
                return {}
            
            analytics = {
                'total_arguments': len(debate.arguments),
                'arguments_by_round': {},
                'arguments_by_personality': {},
                'total_votes': debate.total_votes,
                'vote_distribution': debate.votes,
                'duration_minutes': 0
            }
            
            # Calculate arguments by round
            for arg in debate.arguments:
                round_num = arg.get('round_number', 1)
                analytics['arguments_by_round'][round_num] = analytics['arguments_by_round'].get(round_num, 0) + 1
            
            # Calculate arguments by personality
            for arg in debate.arguments:
                personality = arg.get('personality_id', 'Unknown')
                analytics['arguments_by_personality'][personality] = analytics['arguments_by_personality'].get(personality, 0) + 1
            
            # Calculate duration if debate is completed
            if debate.status in ['completed', 'judged'] and debate.created_at and debate.updated_at:
                duration = debate.updated_at - debate.created_at
                analytics['duration_minutes'] = round(duration.total_seconds() / 60, 2)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting debate analytics for {debate_id}: {str(e)}")
            return {}
    
    def search_debates(self, query: str, limit: int = 10) -> List[Debate]:
        """Search debates by topic"""
        try:
            search_query = {
                'topic': {'$regex': query, '$options': 'i'}
            }
            
            debates_data = (self.debates_collection
                          .find(search_query)
                          .sort('created_at', -1)
                          .limit(limit))
            
            return [Debate.from_dict(data) for data in debates_data]
            
        except Exception as e:
            logger.error(f"Error searching debates: {str(e)}")
            return []