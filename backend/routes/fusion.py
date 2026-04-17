import torch
from flask import Blueprint, request, jsonify
from services.fusion_engine import FusionEngine
from services.lora_bridge import MeshMessengerBridge

fusion_bp = Blueprint('fusion', __name__)

# Initialize singletons
fusion_engine = FusionEngine()
mesh_bridge = MeshMessengerBridge()

@fusion_bp.route('/fusion-data', methods=['POST'])
def get_fusion_data():
    """
    Expects JSON payload with location and weather data.
    In a real scenario, this triggers the GEE API to fetch SAR/Opt data.
    """
    try:
        data = request.json
        
        # 1. MOCK TENSORS (For hackathon testing if GEE API isn't ready)
        # Create dummy tensors to simulate satellite data ingestion
        dummy_sar = torch.randn(1, 2, 256, 256) # Batch=1, Channels=2 (VV, VH), 256x256
        dummy_opt = torch.randn(1, 2, 256, 256) # Batch=1, Channels=2 (NDWI, CloudMask)
        dummy_time_series = torch.randn(1, 30, 3) # Batch=1, 30 days, 3 features
        
        # 2. PROCESS FUSION
        result = fusion_engine.process_fusion(
            sar_tensor=dummy_sar,
            opt_tensor=dummy_opt,
            weather_data={
                "location": data.get("location", {"lat": 20.9320, "lon": 77.7523}),
                "temp": data.get("temperature", 32.5),
                "rain": data.get("rainfall", 5.0),
                "ndvi": data.get("ndvi", 0.6),
                "timestamp": data.get("timestamp", "2026-04-17T12:00:00Z")
            },
            time_series_data=dummy_time_series
        )
        
        # 3. TRIGGER LORA MESH ALERT (If AWD is violated and methane is high)
        if result['awd_status'] is False and result['methane_value'] > 50.0:
            mesh_bridge.broadcast_alert(
                location=result['location'],
                alert_type="HIGH_METHANE_AWD_VIOLATION",
                severity="CRITICAL"
            )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400