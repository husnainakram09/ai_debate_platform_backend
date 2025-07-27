from flask import Blueprint, jsonify, request
# from routes import main_bp
from services.debate_service import DebateService
from services.personality_service import PersonalityService
from utils.database import get_db, check_database_health
from utils.helpers import create_success_response, create_error_response
import logging

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        db_health = check_database_health()
        
        health_status = {
            'status': 'healthy',
            'service': 'AI Debate Platform',
            'database': db_health,
            'timestamp': '2024-01-01T00:00:00Z'  # You can use datetime.utcnow().isoformat()
        }
        
        if db_health.get('status') != 'healthy':
            return jsonify(health_status), 503
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

@main_bp.route('/info')
def get_info():
    """Get platform information"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        personality_service = PersonalityService()
        
        info = {
            'platform_name': 'AI Debate Platform',
            'version': '1.0.0',
            'description': 'A platform where AI personalities engage in structured debates',
            'features': [
                'Multi-round debates',
                '6 unique AI personalities',
                'Real-time argument generation',
                'Community voting',
                'Personality leaderboards'
            ],
            'statistics': {
                'total_debates': debate_service.get_debates_count(),
                'active_debates': debate_service.get_debates_count('in_progress'),
                'completed_debates': debate_service.get_debates_count('completed'),
                'total_personalities': len(personality_service.get_all_personalities())
            }
        }
        
        return jsonify(create_success_response(info))
        
    except Exception as e:
        logger.error(f"Error getting platform info: {str(e)}")
        return jsonify(create_error_response('Failed to retrieve platform information')), 500

@main_bp.route('/status')
def get_status():
    """Get detailed platform status"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        
        # Get recent activity
        recent_debates = debate_service.get_recent_debates(5)
        
        status = {
            'service_status': 'running',
            'uptime': '24h 30m',  # You can calculate actual uptime
            'recent_activity': {
                'recent_debates': len(recent_debates),
                'last_debate_created': recent_debates[0].created_at.isoformat() if recent_debates else None
            },
            'system_info': {
                'python_version': '3.9+',
                'flask_version': '2.3.3',
                'mongodb_status': 'connected'
            }
        }
        
        return jsonify(create_success_response(status))
        
    except Exception as e:
        logger.error(f"Error getting platform status: {str(e)}")
        return jsonify(create_error_response('Failed to retrieve platform status')), 500