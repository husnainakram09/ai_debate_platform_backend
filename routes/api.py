from flask import request, jsonify, Blueprint
from services.debate_service import DebateService
from services.ai_service import AIService
from services.personality_service import PersonalityService
from utils.database import get_db
from utils.helpers import validate_debate_data, sanitize_input
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from pprint import pprint


api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# Thread pool for AI processing
executor = ThreadPoolExecutor(max_workers=4)

@api_bp.route('/debates', methods=['GET'])
def get_debates():
    """Get all debates with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status')
        
        db = get_db()
        debate_service = DebateService(db)
        
        debates = debate_service.get_debates_paginated(page, limit, status)
        total = debate_service.get_debates_count(status)
        
        return jsonify({
            'success': True,
            'debates': [debate.to_dict() for debate in debates],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting debates: {str(e)}")
        return jsonify({'error': 'Failed to retrieve debates'}), 500

@api_bp.route('/debates', methods=['POST'])
def create_debate():
    """Create a new debate"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate input
        is_valid, error_message = validate_debate_data(data)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        topic = sanitize_input(data.get('topic'))
        creator_id = data.get('creator_id')
        
        db = get_db()
        debate_service = DebateService(db)
        
        debate = debate_service.create_debate(topic, creator_id)
        
        return jsonify({
            'success': True,
            'debate_id': str(debate._id),
            'debate': debate.to_dict(),
            'message': 'Debate created successfully'
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating debate: {str(e)}")
        return jsonify({'error': 'Failed to create debate'}), 500

@api_bp.route('/debates/<debate_id>', methods=['GET'])
def get_debate(debate_id):
    """Get a specific debate by ID"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        
        debate = debate_service.get_debate(debate_id)
        
        if not debate:
            return jsonify({'error': 'Debate not found'}), 404
        
        return jsonify({
            'success': True,
            'debate': debate.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error getting debate {debate_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve debate'}), 500

@api_bp.route('/debates/<debate_id>/start', methods=['POST'])
def start_debate(debate_id):
    """Start a debate and generate first round arguments"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        ai_service = AIService()
        
        # Check if debate exists and is in correct state
        debate = debate_service.get_debate(debate_id)
        
        if not debate:
            return jsonify({'error': 'Debate not found'}), 404
        
        if debate.status != 'created':
            return jsonify({'error': 'Debate has already been started or completed'}), 400
        
        # Start the debate
        debate = debate_service.start_debate(debate_id)
        
        if not debate:
            return jsonify({'error': 'Failed to start debate'}), 500
        
        # Generate first round of arguments asynchronously
        def generate_arguments():
            try:
                arguments = ai_service.generate_debate_round(debate, 1)
                for arg in arguments:
                    debate_service.add_argument(debate_id, arg)
                return arguments
            except Exception as e:
                logger.error(f"Error generating arguments: {str(e)}")
                return []
        
        # Run in thread pool to avoid blocking
        future = executor.submit(generate_arguments)
        arguments = future.result(timeout=60)  # 60 second timeout
        
        return jsonify({
            'success': True,
            'debate': debate.to_dict(),
            'arguments': [arg.to_dict() for arg in arguments],
            'message': 'Debate started successfully'
        })
    
    except Exception as e:
        logger.error(f"Error starting debate: {str(e)}")
        return jsonify({'error': 'Failed to start debate'}), 500

@api_bp.route('/debates/<debate_id>/next-round', methods=['POST'])
def next_round(debate_id):
    """Progress to the next round of debate"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        ai_service = AIService()
        
        debate = debate_service.get_debate(debate_id)
        
        if not debate:
            return jsonify({'error': 'Debate not found'}), 404
        
        if debate.status != 'in_progress':
            return jsonify({'error': 'Debate is not in progress'}), 400
        
        next_round_num = debate.current_round + 1
        
        if next_round_num > debate.max_rounds:
            # End debate
            debate_service.end_debate(debate_id)
            updated_debate = debate_service.get_debate(debate_id)
            return jsonify({
                'success': True,
                'debate_ended': True,
                'debate': updated_debate.to_dict(),
                'message': 'Debate completed - all rounds finished'
            })
        
        # Generate next round arguments
        def generate_arguments():
            try:
                arguments = ai_service.generate_debate_round(debate, next_round_num)
                for arg in arguments:
                    debate_service.add_argument(debate_id, arg)
                debate_service.update_round(debate_id, next_round_num)
                return arguments
            except Exception as e:
                logger.error(f"Error generating round {next_round_num} arguments: {str(e)}")
                return []
        
        future = executor.submit(generate_arguments)
        arguments = future.result(timeout=60)
        
        updated_debate = debate_service.get_debate(debate_id)
        
        return jsonify({
            'success': True,
            'round': next_round_num,
            'debate': updated_debate.to_dict(),
            'arguments': [arg.to_dict() for arg in arguments],
            'message': f'Round {next_round_num} completed'
        })
    
    except Exception as e:
        logger.error(f"Error proceeding to next round: {str(e)}")
        return jsonify({'error': 'Failed to proceed to next round'}), 500

@api_bp.route('/debates/<debate_id>/judge', methods=['POST'])
def judge_debate(debate_id):
    """Judge a debate and declare winner"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        winner_personality = data.get('winner')
        reasoning = sanitize_input(data.get('reasoning', ''))
        judge_id = data.get('judge_id')
        
        if not winner_personality:
            return jsonify({'error': 'Winner personality is required'}), 400
        
        db = get_db()
        debate_service = DebateService(db)
        
        # Verify debate exists and is completed
        debate = debate_service.get_debate(debate_id)
        if not debate:
            return jsonify({'error': 'Debate not found'}), 404
        
        if debate.status in ['judged']:
            return jsonify({'error': 'Debate already jugded.'}), 400

        if debate.status not in ['completed', 'in_progress']:
            return jsonify({'error': 'Debate must be completed before judging'}), 400
        
        # Verify winner is a valid participant
        if winner_personality not in debate.participants:
            return jsonify({'error': 'Winner must be a debate participant'}), 400
        result = debate_service.judge_debate(debate_id, winner_personality, reasoning, judge_id)
        
        if result:
            updated_debate = debate_service.get_debate(debate_id)
            # pprint(updated_debate.to_dict())
            return jsonify({
                'success': True,
                'debate': updated_debate.to_dict(),
                'winner': winner_personality,
                'message': 'Debate judged successfully'
            })
        else:
            return jsonify({'error': 'Failed to judge debate'}), 500
    
    except Exception as e:
        logger.error(f"Error judging debate: {str(e)}")
        return jsonify({'error': 'Failed to judge debate'}), 500

@api_bp.route('/debates/<debate_id>/vote', methods=['POST'])
def vote_on_debate(debate_id):
    """Vote for the best argument in a debate"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        personality_id = data.get('personality_id')
        voter_id = data.get('voter_id', 'anonymous')
        
        if not personality_id:
            return jsonify({'error': 'Personality ID is required'}), 400
        
        db = get_db()
        debate_service = DebateService(db)
        
        result = debate_service.add_vote(debate_id, personality_id, voter_id)
        
        if result:
            updated_debate = debate_service.get_debate(debate_id)
            return jsonify({
                'success': True,
                'debate': updated_debate.to_dict(),
                'message': 'Vote recorded successfully'
            })
        else:
            return jsonify({'error': 'Failed to record vote'}), 500
    
    except Exception as e:
        logger.error(f"Error voting on debate: {str(e)}")
        return jsonify({'error': 'Failed to record vote'}), 500

@api_bp.route('/personalities', methods=['GET'])
def get_personalities():
    """Get all AI personalities"""
    try:
        personality_service = PersonalityService()
        personalities = personality_service.get_all_personalities()
        
        return jsonify({
            'success': True,
            'personalities': [p.to_dict() for p in personalities]
        })
    
    except Exception as e:
        logger.error(f"Error getting personalities: {str(e)}")
        return jsonify({'error': 'Failed to get personalities'}), 500

@api_bp.route('/personalities/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get personality leaderboard"""
    try:
        personality_service = PersonalityService()
        leaderboard = personality_service.get_leaderboard()
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        })
    
    except Exception as e:
        logger.error(f"Error getting leaderboard: {str(e)}")
        return jsonify({'error': 'Failed to get leaderboard'}), 500

@api_bp.route('/stats', methods=['GET'])
def get_platform_stats():
    """Get platform statistics"""
    try:
        db = get_db()
        debate_service = DebateService(db)
        personality_service = PersonalityService()
        
        stats = {
            'total_debates': debate_service.get_debates_count(),
            'active_debates': debate_service.get_debates_count('in_progress'),
            'completed_debates': debate_service.get_debates_count('completed'),
            'total_personalities': len(personality_service.get_all_personalities()),
            'total_arguments': debate_service.get_total_arguments_count()
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"Error getting platform stats: {str(e)}")
        return jsonify({'error': 'Failed to get platform statistics'}), 500

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@api_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

