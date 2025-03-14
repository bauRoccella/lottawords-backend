import os
import sys
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, make_response
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
import pytz
import logging
import logging.handlers
import redis

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, log_level))

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Always add console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Add syslog handler in production
if os.getenv('FLASK_ENV') == 'production':
    # If PAPERTRAIL_HOST and PAPERTRAIL_PORT are set, use them
    papertrail_host = os.getenv('PAPERTRAIL_HOST')
    papertrail_port = os.getenv('PAPERTRAIL_PORT')
    
    if papertrail_host and papertrail_port:
        syslog_handler = logging.handlers.SysLogHandler(
            address=(papertrail_host, int(papertrail_port))
        )
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)

# Set up Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.lottawords.scraper import LetterBoxedScraper
from src.lottawords.solver import LetterBoxedSolver

app = Flask(__name__)

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": "*",  # Allow all origins initially, we'll filter in after_request
        "methods": ["GET", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Origin"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "send_wildcard": False  # Required when supports_credentials is True
    }
})

@app.after_request
def after_request(response):
    """Add CORS headers to every response"""
    origin = request.headers.get('Origin')
    
    # Log the origin for debugging
    logger.info(f"Processing response for origin: {origin}")
    
    # Check if origin is allowed
    if origin:
        if (origin.startswith('http://localhost:') or
            'vercel.app' in origin or
            'railway.app' in origin):
            
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'  # Cache preflight for 1 hour
            
            logger.info(f"CORS headers set for origin: {origin}")
        else:
            logger.warning(f"Rejected origin: {origin}")
    
    return response

@app.before_request
def log_request_info():
    """Log request information for debugging"""
    logger.info(f"Incoming request from origin: {request.headers.get('Origin')}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request path: {request.path}")
    logger.info(f"Request headers: {dict(request.headers)}")

# Add the memory cache dictionary
memory_cache = {
    'puzzle_data': None,
    'last_updated': None
}

# Replace the Redis setup section with this
try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url)
    USING_REDIS = True
except:
    logger.warning("Redis connection failed, falling back to memory cache")
    USING_REDIS = False

# Replace the cache functions with these versions
def is_cache_valid():
    """Check if cache is valid (from today and after the last puzzle update)"""
    try:
        if USING_REDIS:
            cached_data = redis_client.get(CACHE_KEY)
            if not cached_data:
                return False
            cache_dict = json.loads(cached_data)
        else:
            if not memory_cache['puzzle_data']:
                return False
            cache_dict = {
                'last_updated': memory_cache['last_updated'].isoformat() if memory_cache['last_updated'] else None
            }
        
        last_updated = datetime.fromisoformat(cache_dict['last_updated'])
        now = datetime.now(pytz.timezone('US/Eastern'))
        cutoff_time = now.replace(hour=3, minute=5, second=0, microsecond=0)
        
        if now.hour < 3 or (now.hour == 3 and now.minute < 5):
            cutoff_time = cutoff_time - timedelta(days=1)
        
        return last_updated.astimezone(pytz.timezone('US/Eastern')) >= cutoff_time
    except Exception as e:
        logger.error(f"Error checking cache validity: {e}")
        return False

def get_cached_data():
    """Get cached puzzle data"""
    try:
        if USING_REDIS:
            cached_data = redis_client.get(CACHE_KEY)
            if cached_data:
                return json.loads(cached_data)
        else:
            if memory_cache['puzzle_data']:
                return memory_cache['puzzle_data']
        return None
    except Exception as e:
        logger.error(f"Error getting cached data: {e}")
        return None

def save_cache_data(data):
    """Save puzzle data to cache"""
    try:
        cache_dict = {
            'puzzle_data': data,
            'last_updated': datetime.now().isoformat()
        }
        if USING_REDIS:
            redis_client.set(CACHE_KEY, json.dumps(cache_dict))
        else:
            memory_cache['puzzle_data'] = data
            memory_cache['last_updated'] = datetime.now()
        logger.info(f"Cache saved to {'Redis' if USING_REDIS else 'memory'}")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

def fetch_puzzle_data():
    """Fetch fresh puzzle data from NYT and solve it"""
    try:
        logger.info("Fetching new puzzle data...")
        scraper = LetterBoxedScraper()
        sides, nyt_solution, nyt_dictionary = scraper.get_puzzle_data()
        
        # Make sure we have valid sides data
        if not sides or len(sides) != 4:
            logger.error("Invalid or missing sides data from NYT")
            return {'error': 'Failed to retrieve puzzle data from NYT: Invalid sides data'}
        
        # Format sides into a square dictionary as expected by find_shortest_solution
        square = {
            "top": sides[0],
            "right": sides[1],
            "bottom": sides[2],
            "left": sides[3]
        }
        
        # Check if we have a valid dictionary from NYT
        if not nyt_dictionary or len(nyt_dictionary) == 0:
            logger.error("No dictionary received from NYT")
            return {'error': 'Failed to retrieve dictionary from NYT website. The page structure may have changed or the site may be temporarily unavailable.'}
        
        solver = LetterBoxedSolver()
        # Use the NYT dictionary
        lotta_solution = solver.find_shortest_solution(square, nyt_dictionary)
        
        # Ensure nyt_solution is a list of strings
        if not nyt_solution or not isinstance(nyt_solution, list):
            nyt_solution = []
        else:
            # Convert all items to strings if needed
            nyt_solution = [str(word) for word in nyt_solution]
        
        # Format for consistent response
        formatted_data = {
            'square': {
                'top': sides[0],
                'right': sides[1],
                'bottom': sides[2],
                'left': sides[3]
            },
            'nyt_solution': nyt_solution,
            'lotta_solution': lotta_solution,
            'error': None
        }
        
        # Save to Redis
        save_cache_data(formatted_data)
        
        logger.info("Puzzle data updated successfully")
        return formatted_data
    except Exception as e:
        logger.error(f"Error fetching puzzle data: {e}")
        return {'error': str(e)}

@app.route('/api/puzzle')
def get_puzzle_data():
    """API endpoint to get puzzle data (from cache if available)"""
    global scraping_in_progress
    
    # Initialize the flag if it doesn't exist
    if 'scraping_in_progress' not in globals():
        scraping_in_progress = False
    
    # Check for valid cache
    if is_cache_valid():
        logger.info("Using valid cache data")
        return jsonify(get_cached_data())
    
    # Check if scraping is already in progress
    if scraping_in_progress:
        logger.info("Scraping already in progress, returning status")
        return jsonify({
            'status': 'loading',
            'message': 'Data is being prepared, please try again in a moment'
        })
    
    # If we're here, we need fresh data and no scraping is happening
    scraping_in_progress = True
    try:
        logger.info("Starting fresh data fetch")
        result = fetch_puzzle_data()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error during fetch: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })
    finally:
        scraping_in_progress = False

@app.route('/api/status')
def get_status():
    """Health check endpoint"""
    try:
        # Basic application status
        status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'redis_connected': False,
            'cache_valid': False
        }
        
        # Check Redis connection
        try:
            redis_client.ping()
            status['redis_connected'] = True
        except:
            logger.warning("Redis connection failed")
        
        # Check cache if Redis is connected
        if status['redis_connected']:
            try:
                status['cache_valid'] = is_cache_valid()
            except:
                logger.warning("Cache validation failed")
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal status check failed',
            'timestamp': datetime.now().isoformat()
        }), 200  # Return 200 even on error for health check

@app.route('/api/healthz')
def healthz():
    """Minimal health check endpoint for Railway"""
    logger.info("Health check endpoint called")
    return 'OK', 200

@app.errorhandler(500)
def handle_500_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.route('/api/debug')
def debug_puzzle_data():
    """Debug endpoint to check puzzle data and response format"""
    try:
        # Scrape fresh data
        logger.info("DEBUG: Fetching fresh data for debugging")
        scraper = LetterBoxedScraper()
        sides, nyt_solution, nyt_dictionary = scraper.get_puzzle_data()
        
        # Check formats
        response = {
            "sides_type": str(type(sides)),
            "sides_value": sides,
            "nyt_solution_type": str(type(nyt_solution)),
            "nyt_solution_value": nyt_solution,
            "dictionary_type": str(type(nyt_dictionary)),
            "dictionary_length": len(nyt_dictionary) if nyt_dictionary else 0,
            "sample_words": nyt_dictionary[:5] if nyt_dictionary and len(nyt_dictionary) >= 5 else []
        }
        
        # Check cache
        if is_cache_valid():
            response["cache_status"] = "valid"
            response["cached_data"] = {
                "lotta_solution": get_cached_data()['lotta_solution'] if 'lotta_solution' in get_cached_data() else None,
                "lotta_solution_type": str(type(get_cached_data().get('lotta_solution', None))),
                "lotta_solution_length": len(get_cached_data()['lotta_solution']) if 'lotta_solution' in get_cached_data() and get_cached_data()['lotta_solution'] else 0
            }
        else:
            response["cache_status"] = "invalid or missing"
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        return jsonify({"error": str(e)})

def init_scheduler():
    """Initialize the scheduler to update puzzle data at 3:05 AM EST (when NYT updates)"""
    scheduler = BackgroundScheduler()
    
    # Schedule job to run at 3:05 AM EST every day
    scheduler.add_job(
        fetch_puzzle_data,
        CronTrigger(
            hour=3, 
            minute=5, 
            timezone=pytz.timezone('US/Eastern')
        ),
        id='fetch_daily_puzzle'
    )
    
    scheduler.start()
    logger.info("Scheduler started - puzzle will update daily at 3:05 AM EST")
    
    # Shutdown scheduler when app exits
    atexit.register(lambda: scheduler.shutdown())

# On startup: initialize scheduler
init_scheduler()

# Fetch puzzle data on startup if needed
if not is_cache_valid():
    fetch_puzzle_data()

# Add startup logging
logger.info("Flask application starting")
logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
logger.info(f"Redis URL configured: {'REDIS_URL' in os.environ}")
logger.info(f"Debug mode: {app.debug}")

@app.route('/')
def index():
    """Fallback route for the old template"""
    square, nyt_solution, lotta_solution = get_puzzle_data()
    return render_template('index.html', 
                         square=square,
                         nyt_solution=nyt_solution,
                         lotta_solution=lotta_solution)

if __name__ == '__main__':
    logger.info("Starting Flask development server")
    app.run(debug=True) 