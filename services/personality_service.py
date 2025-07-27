import logging
from typing import List, Optional
from models.personality import AIPersonality, DEFAULT_PERSONALITIES
from utils.database import get_db
from datetime import datetime

logger = logging.getLogger(__name__)

class PersonalityService:
    def __init__(self):
        print("helllooo persoanaluit")
        self.db = get_db()
        self.personalities_collection = self.db.personalities
        self._initialize_personalities()
    
    def _initialize_personalities(self):
        """Initialize default personalities if they don't exist"""
        try:
            existing_count = self.personalities_collection.count_documents({})
            
            if existing_count == 0:
                logger.info("Initializing default personalities...")
                personalities_data = []
                
                for p_data in DEFAULT_PERSONALITIES:
                    personality = AIPersonality(
                        name=p_data['name'],
                        description=p_data['description'],
                        personality_traits=p_data['personality_traits'],
                        debate_style=p_data['debate_style'],
                        system_prompt=p_data['system_prompt']
                    )
                    personalities_data.append(personality.to_dict())
                
                self.personalities_collection.insert_many(personalities_data)
                logger.info(f"Initialized {len(personalities_data)} default personalities")
            else:
                logger.info(f"Found {existing_count} existing personalities")
                
        except Exception as e:
            logger.error(f"Error initializing personalities: {str(e)}")
    
    def get_all_personalities(self) -> List[AIPersonality]:
        """Get all personalities"""
        try:
            personalities_data = self.personalities_collection.find()
            personalities = [AIPersonality.from_dict(data) for data in personalities_data]
            logger.info(f"Retrieved {len(personalities)} personalities")
            return personalities
        except Exception as e:
            logger.error(f"Error getting personalities: {str(e)}")
            return []
    
    def get_debate_personalities(self) -> List[AIPersonality]:
        """Get personalities for debate (all active personalities)"""
        try:
            # You could add filtering logic here if needed (e.g., only active personalities)
            personalities_data = self.personalities_collection.find()
            personalities = [AIPersonality.from_dict(data) for data in personalities_data]
            return personalities
        except Exception as e:
            logger.error(f"Error getting debate personalities: {str(e)}")
            return []
    
    def get_personality_by_name(self, name: str) -> Optional[AIPersonality]:
        """Get a specific personality by name"""
        try:
            personality_data = self.personalities_collection.find_one({'name': name})
            if personality_data:
                return AIPersonality.from_dict(personality_data)
            return None
        except Exception as e:
            logger.error(f"Error getting personality {name}: {str(e)}")
            return None
    
    def update_personality_stats(self, personality_name: str, won: bool, votes_received: int = 0):
        """Update personality statistics"""
        try:
            # Get current personality data to calculate new averages
            personality_data = self.personalities_collection.find_one({'name': personality_name})
            
            if not personality_data:
                logger.warning(f"Personality {personality_name} not found for stats update")
                return
            
            current_total_debates = personality_data.get('total_debates', 0)
            current_total_arguments = personality_data.get('total_arguments', 0)
            current_average_votes = personality_data.get('average_votes', 0.0)
            current_wins = personality_data.get('wins', 0)
            
            # Calculate new values
            new_total_debates = current_total_debates + 1
            new_total_arguments = current_total_arguments + 1
            new_wins = current_wins + (1 if won else 0)
            
            # Calculate new average votes
            if new_total_arguments > 1:
                new_average_votes = ((current_average_votes * current_total_arguments) + votes_received) / new_total_arguments
            else:
                new_average_votes = votes_received
            
            # Update document
            update_data = {
                '$set': {
                    'total_debates': new_total_debates,
                    'total_arguments': new_total_arguments,
                    'wins': new_wins,
                    'average_votes': round(new_average_votes, 2),
                    'updated_at': datetime.utcnow()
                }
            }
            
            result = self.personalities_collection.update_one(
                {'name': personality_name},
                update_data
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated stats for {personality_name}: wins={new_wins}, debates={new_total_debates}")
            else:
                logger.warning(f"Failed to update stats for {personality_name}")
            
        except Exception as e:
            logger.error(f"Error updating stats for {personality_name}: {str(e)}")
    
    def get_leaderboard(self) -> List[dict]:
        """Get personality leaderboard sorted by wins and win rate"""
        try:
            personalities = self.personalities_collection.find().sort([
                ('wins', -1),  # Primary sort by wins
                ('total_debates', -1)  # Secondary sort by total debates
            ])
            
            leaderboard = []
            
            for p_data in personalities:
                personality = AIPersonality.from_dict(p_data)
                win_rate = personality.get_win_rate()
                
                leaderboard_entry = {
                    'name': personality.name,
                    'description': personality.description,
                    'personality_traits': personality.personality_traits,
                    'debate_style': personality.debate_style,
                    'wins': personality.wins,
                    'total_debates': personality.total_debates,
                    'total_arguments': personality.total_arguments,
                    'win_rate': win_rate,
                    'average_votes': personality.average_votes,
                    'updated_at': personality.updated_at
                }
                
                leaderboard.append(leaderboard_entry)
            
            logger.info(f"Generated leaderboard with {len(leaderboard)} personalities")
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {str(e)}")
            return []
    
    def get_personality_stats(self, personality_name: str) -> dict:
        """Get detailed stats for a specific personality"""
        try:
            personality_data = self.personalities_collection.find_one({'name': personality_name})
            
            if not personality_data:
                return {}
            
            personality = AIPersonality.from_dict(personality_data)
            
            stats = {
                'name': personality.name,
                'wins': personality.wins,
                'total_debates': personality.total_debates,
                'total_arguments': personality.total_arguments,
                'win_rate': personality.get_win_rate(),
                'average_votes': personality.average_votes,
                'losses': personality.total_debates - personality.wins,
                'arguments_per_debate': round(personality.total_arguments / personality.total_debates, 2) if personality.total_debates > 0 else 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats for {personality_name}: {str(e)}")
            return {}
    
    def create_personality(self, name: str, description: str, personality_traits: List[str], 
                          debate_style: str, system_prompt: str) -> Optional[AIPersonality]:
        """Create a new personality (admin function)"""
        try:
            # Check if personality already exists
            existing = self.personalities_collection.find_one({'name': name})
            if existing:
                logger.warning(f"Personality {name} already exists")
                return None
            
            personality = AIPersonality(
                name=name,
                description=description,
                personality_traits=personality_traits,
                debate_style=debate_style,
                system_prompt=system_prompt
            )
            
            result = self.personalities_collection.insert_one(personality.to_dict())
            
            if result.inserted_id:
                logger.info(f"Created new personality: {name}")
                return personality
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating personality {name}: {str(e)}")
            return None
    
    def update_personality(self, name: str, updates: dict) -> bool:
        """Update a personality (admin function)"""
        try:
            # Add updated_at timestamp
            updates['updated_at'] = datetime.utcnow()
            
            result = self.personalities_collection.update_one(
                {'name': name},
                {'$set': updates}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated personality {name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating personality {name}: {str(e)}")
            return False
    
    def delete_personality(self, name: str) -> bool:
        """Delete a personality (admin function)"""
        try:
            result = self.personalities_collection.delete_one({'name': name})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted personality {name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting personality {name}: {str(e)}")
            return False
    
    def reset_personality_stats(self, name: str = None) -> bool:
        """Reset personality statistics (admin function)"""
        try:
            query = {'name': name} if name else {}
            
            update_data = {
                '$set': {
                    'wins': 0,
                    'total_debates': 0,
                    'total_arguments': 0,
                    'average_votes': 0.0,
                    'updated_at': datetime.utcnow()
                }
            }
            
            result = self.personalities_collection.update_many(query, update_data)
            
            if result.modified_count > 0:
                logger.info(f"Reset stats for {result.modified_count} personalities")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error resetting personality stats: {str(e)}")
            return False
    
    def get_top_personalities(self, limit: int = 3, sort_by: str = 'wins') -> List[dict]:
        """Get top personalities by specified criteria"""
        try:
            sort_field = sort_by if sort_by in ['wins', 'total_debates', 'average_votes'] else 'wins'
            
            personalities = self.personalities_collection.find().sort(sort_field, -1).limit(limit)
            
            top_personalities = []
            for p_data in personalities:
                personality = AIPersonality.from_dict(p_data)
                
                top_personalities.append({
                    'name': personality.name,
                    'description': personality.description,
                    'wins': personality.wins,
                    'total_debates': personality.total_debates,
                    'win_rate': personality.get_win_rate(),
                    'average_votes': personality.average_votes
                })
            
            return top_personalities
            
        except Exception as e:
            logger.error(f"Error getting top personalities: {str(e)}")
            return []