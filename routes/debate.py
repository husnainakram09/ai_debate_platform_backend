from flask import Blueprint, jsonify, request
# from routes import debate_bp
from services.debate_service import DebateService
from utils.database import get_db
from utils.helpers import create_success_response, create_error_response, calculate_debate_engagement
import logging

debate_bp = Blueprint('debate', __name__)
logger = logging.getLogger(__name__)

@debate_bp.route('/<debate_id>/analytics')
def get_debate_analytics(debate_id):
    """Get detailed analytics for a specific debate"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        
        # Get debate
        debate = debate_service.get_debate(debate_id)
        if not debate:
            return jsonify(create_error_response('Debate not found')), 404
        
        # Get analytics
        analytics = debate_service.get_debate_analytics(debate_id)
        
        # Add engagement metrics
        engagement = calculate_debate_engagement(debate)
        analytics.update(engagement)
        
        return jsonify(create_success_response(analytics))
        
    except Exception as e:
        logger.error(f"Error getting debate analytics for {debate_id}: {str(e)}")
        return jsonify(create_error_response('Failed to retrieve debate analytics')), 500

@debate_bp.route('/<debate_id>/arguments')
def get_debate_arguments(debate_id):
    """Get all arguments for a specific debate"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        
        # Get debate
        debate = debate_service.get_debate(debate_id)
        if not debate:
            return jsonify(create_error_response('Debate not found')), 404
        
        # Optional filtering
        round_number = request.args.get('round', type=int)
        personality_id = request.args.get('personality')
        
        arguments = debate.arguments
        
        # Filter by round if specified
        if round_number:
            arguments = [arg for arg in arguments if arg.get('round_number') == round_number]
        
        # Filter by personality if specified
        if personality_id:
            arguments = [arg for arg in arguments if arg.get('personality_id') == personality_id]
        
        return jsonify(create_success_response({
            'debate_id': debate_id,
            'total_arguments': len(arguments),
            'arguments': arguments
        }))
        
    except Exception as e:
        logger.error(f"Error getting arguments for debate {debate_id}: {str(e)}")
        return jsonify(create_error_response('Failed to retrieve debate arguments')), 500

@debate_bp.route('/<debate_id>/rounds/<int:round_number>')
def get_debate_round(debate_id, round_number):
    """Get arguments for a specific round"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        
        # Get debate
        debate = debate_service.get_debate(debate_id)
        if not debate:
            return jsonify(create_error_response('Debate not found')), 404
        
        # Get arguments for the round
        round_arguments = debate.get_arguments_by_round(round_number)
        
        round_data = {
            'debate_id': debate_id,
            'round_number': round_number,
            'arguments_count': len(round_arguments),
            'arguments': round_arguments,
            'is_complete': len(round_arguments) >= len(debate.participants)
        }
        
        return jsonify(create_success_response(round_data))
        
    except Exception as e:
        logger.error(f"Error getting round {round_number} for debate {debate_id}: {str(e)}")
        return jsonify(create_error_response('Failed to retrieve debate round')), 500

@debate_bp.route('/<debate_id>/summary')
def get_debate_summary(debate_id):
    """Get a summary of the debate"""
    try:
        from utils.helpers import generate_debate_summary, calculate_debate_score
        
        db = get_db()
        debate_service = DebateService(db)
        
        # Get debate
        debate = debate_service.get_debate(debate_id)
        if not debate:
            return jsonify(create_error_response('Debate not found')), 404
        
        # Generate summary
        summary_text = generate_debate_summary(debate)
        scores = calculate_debate_score(debate)
        
        summary = {
            'debate_id': debate_id,
            'topic': debate.topic,
            'status': debate.status,
            'summary': summary_text,
            'statistics': {
                'total_rounds': debate.current_round,
                'total_arguments': len(debate.arguments),
                'total_votes': debate.total_votes,
                'participants': len(debate.participants)
            },
            'scores': scores,
            'winner': debate.winner,
            'judge_decision': debate.judge_decision
        }
        
        return jsonify(create_success_response(summary))
        
    except Exception as e:
        logger.error(f"Error generating summary for debate {debate_id}: {str(e)}")
        return jsonify(create_error_response('Failed to generate debate summary')), 500

@debate_bp.route('/<debate_id>/status')
def get_debate_status(debate_id):
    """Get current status of a debate"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        
        # Get debate
        debate = debate_service.get_debate(debate_id)
        if not debate:
            return jsonify(create_error_response('Debate not found')), 404
        
        status_info = {
            'debate_id': debate_id,
            'status': debate.status,
            'current_round': debate.current_round,
            'max_rounds': debate.max_rounds,
            'can_proceed': debate.can_proceed_to_next_round(),
            'is_complete': debate.is_complete(),
            'arguments_in_current_round': len(debate.get_arguments_by_round(debate.current_round)),
            'expected_arguments': len(debate.participants),
            'last_updated': debate.updated_at.isoformat()
        }
        
        return jsonify(create_success_response(status_info))
        
    except Exception as e:
        logger.error(f"Error getting status for debate {debate_id}: {str(e)}")
        return jsonify(create_error_response('Failed to retrieve debate status')), 500