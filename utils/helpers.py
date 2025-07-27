import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import html

logger = logging.getLogger(__name__)

def format_datetime(dt: datetime, format_type: str = 'relative') -> str:
    """Format datetime for display"""
    if not dt:
        return "Unknown"
    
    if format_type == 'relative':
        return _format_relative_datetime(dt)
    elif format_type == 'absolute':
        return dt.strftime("%B %d, %Y at %I:%M %p")
    elif format_type == 'short':
        return dt.strftime("%m/%d/%Y %H:%M")
    else:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

def _format_relative_datetime(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2 hours ago')"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    elif diff.days > 7:
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    # Try to break at word boundary
    truncated = text[:max_length - len(suffix)]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # If we can break at a word boundary without losing too much
        truncated = truncated[:last_space]
    
    return truncated + suffix

def validate_debate_data(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate debate creation data"""
    if not data:
        return False, "Request data is required"
    
    if not data.get('topic'):
        return False, "Topic is required"
    
    topic = data['topic'].strip()
    
    if len(topic) < 10:
        return False, "Topic must be at least 10 characters long"
    
    if len(topic) > 500:
        return False, "Topic must be less than 500 characters"
    
    # Check for inappropriate content (basic check)
    if _contains_inappropriate_content(topic):
        return False, "Topic contains inappropriate content"
    
    return True, ""

def validate_judge_data(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate debate judging data"""
    if not data:
        return False, "Request data is required"
    
    if not data.get('winner'):
        return False, "Winner selection is required"
    
    winner = data['winner'].strip()
    if not winner:
        return False, "Winner cannot be empty"
    
    reasoning = data.get('reasoning', '').strip()
    if reasoning and len(reasoning) > 1000:
        return False, "Reasoning must be less than 1000 characters"
    
    return True, ""

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS and other attacks"""
    if not text:
        return ""
    
    # HTML escape
    text = html.escape(text)
    
    # Remove potential script tags and other dangerous HTML
    text = re.sub(r'<script[^>]>.?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)  # Remove any remaining HTML tags
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove null bytes and other control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text.strip()

def _contains_inappropriate_content(text: str) -> bool:
    """Basic check for inappropriate content (expand as needed)"""
    inappropriate_patterns = [
        r'\b(spam|scam|fraud)\b',
        r'<script',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers like onclick=
    ]
    
    text_lower = text.lower()
    for pattern in inappropriate_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    
    return False

def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Extract keywords from text for tagging/categorization"""
    if not text:
        return []
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'may', 'might', 'must', 'can', 'shall', 'should', 'it', 'its', 'he', 'she', 'they',
        'we', 'you', 'i', 'me', 'him', 'her', 'them', 'us'
    }
    
    # Extract words (alphanumeric sequences)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter out stop words and count occurrences
    word_count = {}
    for word in words:
        if word not in stop_words and len(word) > 2:
            word_count[word] = word_count.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    
    return [word for word, count in sorted_words[:max_keywords]]

def calculate_debate_score(debate) -> Dict[str, float]:
    """Calculate scoring metrics for a debate"""
    try:
        scores = {}
        
        if not debate.arguments:
            return scores
        
        # Count arguments by personality
        personality_args = {}
        personality_votes = {}
        
        for arg in debate.arguments:
            personality_id = arg.get('personality_id', 'Unknown')
            personality_args[personality_id] = personality_args.get(personality_id, 0) + 1
            personality_votes[personality_id] = personality_votes.get(personality_id, 0) + arg.get('votes', 0)
        
        # Calculate scores for each personality
        for personality_id in personality_args:
            arg_count = personality_args[personality_id]
            vote_count = personality_votes[personality_id]
            
            # Base score from participation
            participation_score = arg_count * 10
            
            # Bonus from votes
            vote_score = vote_count * 5
            
            # Quality bonus (votes per argument)
            quality_score = (vote_count / arg_count) * 20 if arg_count > 0 else 0
            
            total_score = participation_score + vote_score + quality_score
            scores[personality_id] = round(total_score, 2)
        
        return scores
        
    except Exception as e:
        logger.error(f"Error calculating debate scores: {str(e)}")
        return {}

def generate_debate_summary(debate) -> str:
    """Generate a summary of the debate"""
    try:
        if not debate.arguments:
            return "No arguments have been made in this debate yet."
        
        total_args = len(debate.arguments)
        participants = len(debate.participants)
        
        summary_parts = [
            f"This debate on '{debate.topic}' featured {participants} AI personalities",
            f"exchanging {total_args} arguments across {debate.current_round} rounds."
        ]
        
        if debate.winner:
            summary_parts.append(f"The debate was won by {debate.winner}.")
        
        if debate.total_votes > 0:
            summary_parts.append(f"The community cast {debate.total_votes} votes.")
        
        return " ".join(summary_parts)
        
    except Exception as e:
        logger.error(f"Error generating debate summary: {str(e)}")
        return "Unable to generate debate summary."

def validate_personality_data(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate personality creation/update data"""
    if not data:
        return False, "Request data is required"
    
    required_fields = ['name', 'description', 'personality_traits', 'debate_style', 'system_prompt']
    
    for field in required_fields:
        if not data.get(field):
            return False, f"{field.replace('_', ' ').title()} is required"
    
    name = data['name'].strip()
    if len(name) < 3 or len(name) > 50:
        return False, "Name must be between 3 and 50 characters"
    
    description = data['description'].strip()
    if len(description) < 20 or len(description) > 500:
        return False, "Description must be between 20 and 500 characters"
    
    system_prompt = data['system_prompt'].strip()
    if len(system_prompt) < 50 or len(system_prompt) > 2000:
        return False, "System prompt must be between 50 and 2000 characters"
    
    personality_traits = data.get('personality_traits', [])
    if not isinstance(personality_traits, list) or len(personality_traits) < 2:
        return False, "At least 2 personality traits are required"
    
    return True, ""

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"

def paginate_results(items: List[Any], page: int, per_page: int) -> Dict[str, Any]:
    """Paginate a list of items"""
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        'items': items[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': end < total,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if end < total else None
    }

def calculate_win_rate(wins: int, total: int) -> float:
    """Calculate win rate percentage"""
    if total == 0:
        return 0.0
    return round((wins / total) * 100, 2)

def generate_debate_id() -> str:
    """Generate a unique debate ID"""
    import uuid
    return str(uuid.uuid4())

def is_valid_object_id(obj_id: str) -> bool:
    """Check if string is a valid MongoDB ObjectId"""
    try:
        from bson import ObjectId
        ObjectId(obj_id)
        return True
    except:
        return False

def clean_mongodb_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Clean MongoDB result for JSON serialization"""
    if isinstance(result, dict):
        cleaned = {}
        for key, value in result.items():
            if key == '_id':
                cleaned[key] = str(value)
            elif isinstance(value, datetime):
                cleaned[key] = value.isoformat()
            elif isinstance(value, dict):
                cleaned[key] = clean_mongodb_result(value)
            elif isinstance(value, list):
                cleaned[key] = [clean_mongodb_result(item) if isinstance(item, dict) else item for item in value]
            else:
                cleaned[key] = value
        return cleaned
    return result

def rate_limit_key(user_id: str = None, ip_address: str = None) -> str:
    """Generate rate limiting key"""
    if user_id:
        return f"user:{user_id}"
    elif ip_address:
        return f"ip:{ip_address}"
    else:
        return "anonymous"

def validate_api_key(api_key: str) -> bool:
    """Validate API key format (basic validation)"""
    if not api_key or len(api_key) < 20:
        return False
    
    # Check if it contains only allowed characters
    import string
    allowed_chars = string.ascii_letters + string.digits + '-_'
    return all(c in allowed_chars for c in api_key)

def get_client_ip(request) -> str:
    """Get client IP address from request"""
    # Check for forwarded headers first (for reverse proxies)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    return request.remote_addr or 'unknown'

def create_error_response(message: str, code: int = 400, details: Dict = None) -> Dict[str, Any]:
    """Create standardized error response"""
    response = {
        'success': False,
        'error': message,
        'code': code
    }
    
    if details:
        response['details'] = details
    
    return response

def create_success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
    """Create standardized success response"""
    response = {
        'success': True
    }
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    return response

def log_api_request(endpoint: str, method: str, user_id: str = None, ip_address: str = None):
    """Log API request for monitoring"""
    logger.info(f"API Request: {method} {endpoint} - User: {user_id or 'anonymous'} - IP: {ip_address or 'unknown'}")

def calculate_debate_engagement(debate) -> Dict[str, float]:
    """Calculate engagement metrics for a debate"""
    try:
        if not debate.arguments:
            return {'engagement_score': 0.0, 'avg_argument_length': 0.0, 'participation_rate': 0.0}
        
        total_chars = sum(len(arg.get('content', '')) for arg in debate.arguments)
        avg_argument_length = total_chars / len(debate.arguments)
        
        # Calculate participation rate (how evenly distributed are the arguments)
        personality_counts = {}
        for arg in debate.arguments:
            personality_id = arg.get('personality_id', 'Unknown')
            personality_counts[personality_id] = personality_counts.get(personality_id, 0) + 1
        
        if personality_counts:
            max_args = max(personality_counts.values())
            min_args = min(personality_counts.values())
            participation_rate = (min_args / max_args) * 100 if max_args > 0 else 0
        else:
            participation_rate = 0
        
        # Calculate overall engagement score
        vote_factor = min(debate.total_votes / 10, 10)  # Cap at 10
        length_factor = min(avg_argument_length / 100, 10)  # Cap at 10
        participation_factor = participation_rate / 10
        
        engagement_score = (vote_factor + length_factor + participation_factor) / 3
        
        return {
            'engagement_score': round(engagement_score, 2),
            'avg_argument_length': round(avg_argument_length, 2),
            'participation_rate': round(participation_rate, 2)
        }
        
    except Exception as e:
        logger.error(f"Error calculating debate engagement: {str(e)}")
        return {'engagement_score': 0.0, 'avg_argument_length': 0.0, 'participation_rate': 0.0}