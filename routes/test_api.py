from flask import Flask, jsonify, Blueprint

# Create a minimal API blueprint
test_api_bp = Blueprint('test_api', __name__)

@test_api_bp.route('/personalities')
def get_personalities():
    return jsonify({
        'success': True,
        'personalities': ['test_personality_1', 'test_personality_2']
    })

@test_api_bp.route('/test')
def test_route():
    return {'message': 'Test API working!'}

if __name__ == '__main__':
    app = Flask(__name__)
    app.register_blueprint(test_api_bp, url_prefix='/api')
    
    print("Test routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.endpoint}: {rule.rule}")
    
    app.run(debug=True, port=5001)