import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config
import time

logger = logging.getLogger(__name__)

# Global database connection
_db = None
_client = None

def init_db():
    """Initialize database connection with retry logic"""
    global _db, _client
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to MongoDB (attempt {attempt + 1}/{max_retries})")
            
            # Create MongoDB client with connection options
            _client = MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=Config.DB_CONNECTION_TIMEOUT,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
                maxPoolSize=50,
                minPoolSize=5
            )
            
            # Get database from URI or use default
            _db = _client.get_default_database()
            
            # Test connection
            _client.admin.command('ping')
            logger.info("Database connection established successfully")
            
            # Create indexes for better performance
            _create_indexes()
            
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("All database connection attempts failed")
                raise
        
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {str(e)}")
            raise

def get_db():
    """Get database instance, initializing if necessary"""
    global _db
    
    if _db is None:
        init_db()
    
    return _db

def get_client():
    """Get MongoDB client instance"""
    global _client
    
    if _client is None:
        init_db()
    
    return _client

def _create_indexes():
    """Create database indexes for better performance"""
    try:
        db = get_db()
        
        logger.info("Creating database indexes...")
        
        # Debates collection indexes
        debates_collection = db.debates
        
        # Primary indexes for debates
        debates_collection.create_index([('created_at', -1)])  # For sorting by creation date
        debates_collection.create_index([('status', 1)])       # For filtering by status
        debates_collection.create_index([('creator_id', 1)])   # For filtering by creator
        debates_collection.create_index([('updated_at', -1)])  # For sorting by update date
        
        # Compound indexes for debates
        debates_collection.create_index([('status', 1), ('created_at', -1)])  # Status + date
        debates_collection.create_index([('topic', 'text')])  # Text search on topic
        
        # Personalities collection indexes
        personalities_collection = db.personalities
        
        # Primary indexes for personalities
        personalities_collection.create_index([('name', 1)], unique=True)  # Unique name constraint
        personalities_collection.create_index([('wins', -1)])              # For leaderboard
        personalities_collection.create_index([('total_debates', -1)])     # For stats
        personalities_collection.create_index([('average_votes', -1)])     # For rankings
        
        # Compound indexes for personalities
        personalities_collection.create_index([('wins', -1), ('total_debates', -1)])  # Leaderboard sorting
        
        # Arguments indexes (if you decide to store arguments separately)
        # arguments_collection = db.arguments
        # arguments_collection.create_index([('debate_id', 1)])
        # arguments_collection.create_index([('personality_id', 1)])
        # arguments_collection.create_index([('round_number', 1)])
        # arguments_collection.create_index([('timestamp', -1)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        # Don't raise the error as indexes are performance optimization, not critical

def check_database_health():
    """Check database connection health"""
    try:
        client = get_client()
        
        # Ping the database
        client.admin.command('ping')
        
        # Get basic stats
        db = get_db()
        stats = db.command('dbstats')
        
        health_info = {
            'status': 'healthy',
            'database_name': db.name,
            'collections_count': stats.get('collections', 0),
            'data_size': stats.get('dataSize', 0),
            'storage_size': stats.get('storageSize', 0),
            'indexes_count': stats.get('indexes', 0)
        }
        
        logger.info("Database health check passed")
        return health_info
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

def get_collection_stats():
    """Get statistics for all collections"""
    try:
        db = get_db()
        
        collections_stats = {}
        
        # Get list of collections
        collection_names = db.list_collection_names()
        
        for collection_name in collection_names:
            try:
                collection = db[collection_name]
                stats = db.command('collstats', collection_name)
                
                collections_stats[collection_name] = {
                    'document_count': stats.get('count', 0),
                    'size': stats.get('size', 0),
                    'storage_size': stats.get('storageSize', 0),
                    'total_index_size': stats.get('totalIndexSize', 0),
                    'avg_obj_size': stats.get('avgObjSize', 0)
                }
                
            except Exception as e:
                logger.warning(f"Could not get stats for collection {collection_name}: {str(e)}")
                collections_stats[collection_name] = {'error': str(e)}
        
        return collections_stats
        
    except Exception as e:
        logger.error(f"Error getting collection stats: {str(e)}")
        return {}

def backup_database(backup_path: str = None):
    """Create a simple backup of the database (exports to JSON)"""
    try:
        import json
        from datetime import datetime
        import os
        
        if not backup_path:
            backup_path = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        db = get_db()
        backup_data = {}
        
        # Get all collections
        collection_names = db.list_collection_names()
        
        for collection_name in collection_names:
            collection = db[collection_name]
            documents = list(collection.find())
            
            # Convert ObjectId to string for JSON serialization
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            backup_data[collection_name] = documents
        
        # Write to file
        os.makedirs(os.path.dirname(backup_path) if os.path.dirname(backup_path) else '.', exist_ok=True)
        
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        logger.info(f"Database backup created: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"Error creating database backup: {str(e)}")
        return None

def close_db():
    """Close database connection"""
    global _client, _db
    
    try:
        if _client:
            _client.close()
            _client = None
            _db = None
            logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {str(e)}")

def reset_database():
    """Reset database (WARNING: Deletes all data - use only for development)"""
    try:
        db = get_db()
        
        # Get all collection names
        collection_names = db.list_collection_names()
        
        # Drop all collections
        for collection_name in collection_names:
            db.drop_collection(collection_name)
            logger.info(f"Dropped collection: {collection_name}")
        
        # Recreate indexes
        _create_indexes()
        
        logger.warning("Database has been reset - all data deleted")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

# Database utility functions for common operations
def insert_document(collection_name: str, document: dict):
    """Insert a document into a collection"""
    try:
        db = get_db()
        collection = db[collection_name]
        result = collection.insert_one(document)
        return result.inserted_id
    except Exception as e:
        logger.error(f"Error inserting document into {collection_name}: {str(e)}")
        return None

def find_documents(collection_name: str, query: dict = None, limit: int = None):
    """Find documents in a collection"""
    try:
        db = get_db()
        collection = db[collection_name]
        
        cursor = collection.find(query or {})
        
        if limit:
            cursor = cursor.limit(limit)
        
        return list(cursor)
        
    except Exception as e:
        logger.error(f"Error finding documents in {collection_name}: {str(e)}")
        return []

def update_document(collection_name: str, query: dict, update: dict):
    """Update a document in a collection"""
    try:
        db = get_db()
        collection = db[collection_name]
        result = collection.update_one(query, update)
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating document in {collection_name}: {str(e)}")
        return False

def delete_document(collection_name: str, query: dict):
    """Delete a document from a collection"""
    try:
        db = get_db()
        collection = db[collection_name]
        result = collection.delete_one(query)
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting document from {collection_name}: {str(e)}")
        return False