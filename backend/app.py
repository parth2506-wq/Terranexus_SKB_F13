import os
from flask import Flask, jsonify
from config.settings import Config

# Import all route blueprints
from routes.fusion import fusion_bp
from routes.verification import verification_bp
from routes.credits import credits_bp
from routes.report import report_bp

# Note: The original architecture plan included separate routes for satellite, awd, and methane. 
# Because we built the powerful FusionEngine to handle multi-modal processing simultaneously, 
# those outputs are now natively handled by the `/fusion-data` endpoint to ensure the JSON 
# schema is perfectly synchronized.

def create_app():
    # Initialize the Flask application
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register Blueprints (primary API versioned prefix)
    app.register_blueprint(fusion_bp, url_prefix='/api/v1')
    app.register_blueprint(verification_bp, url_prefix='/api/v1')
    app.register_blueprint(credits_bp, url_prefix='/api/v1')
    app.register_blueprint(report_bp, url_prefix='/api/v1')

    # Backward-compatible aliases for clients calling legacy unprefixed routes.
    app.register_blueprint(fusion_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(credits_bp)
    app.register_blueprint(report_bp)

    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            "service": "dMRV Carbon Intelligence Engine",
            "status": "running",
            "api_prefix": "/api/v1",
            "available_endpoints": [
                "/health",
                "/api/v1/fusion-data",
                "/api/v1/verification",
                "/api/v1/credits",
                "/api/v1/report",
                "/fusion-data",
                "/verification",
                "/credits",
                "/report"
            ]
        }), 200

    # Base Health Check Endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "healthy", 
            "service": "dMRV Carbon Intelligence Engine",
            "mesh_bridge": "active"
        }), 200

    # Global Error Handler: 404 Not Found
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Endpoint not found. Ensure you are using the /api/v1/ prefix."
        }), 404

    # Global Error Handler: 500 Internal Server Error
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "Internal Server Error", 
            "details": str(error)
        }), 500

    return app

if __name__ == '__main__':
    # Instantiate the app
    app = create_app()
    
    print("\n[INIT] Starting dMRV Carbon Intelligence Engine...")
    print(f"[INIT] Loaded OpenRouter Config: {'YES' if Config.OPENROUTER_API_KEY else 'NO'}")
    print(f"[INIT] LoRa Mesh Bridge targeting ESP32 at: {Config.ESP32_IP}:{Config.ESP32_PORT}\n")
    
    # Run the server on 0.0.0.0 to allow local network connections (crucial for ESP32/Mesh tests)
    app.run(host='0.0.0.0', port=5000, debug=True)