from flask import Flask
from flask_cors import CORS
from config import Config
from utils.database import init_db
from routes import main_bp, debate_bp, api_bp
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for all routes
    # CORS(app, origins=['*'])
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    
    # Initialize database
    init_db()
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(debate_bp, url_prefix='/debate')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': 'AI Debate Platform is running'}, 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)