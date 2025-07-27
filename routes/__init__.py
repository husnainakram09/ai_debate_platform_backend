# from flask import Blueprint

# # Create blueprints
# # main_bp = Blueprint('main', __name__)
# # debate_bp = Blueprint('debate', __name__)
# # api_bp = Blueprint('api', __name__)

# # Import route modules to register routes with blueprints
# # Import these AFTER creating blueprints to avoid circular imports
# from routes import main, debate, api

# # Make blueprints available when importing from routes
# __all__ = ['main_bp', 'debate_bp', 'api_bp']

# Import blueprints from route files
from routes.main import main_bp
from routes.debate import debate_bp
from routes.api import api_bp

# Make blueprints available when importing from routes
__all__ = ['main_bp', 'debate_bp', 'api_bp']
