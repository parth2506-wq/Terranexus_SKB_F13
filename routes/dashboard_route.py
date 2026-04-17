# routes/dashboard.py
# Drop this file into your Terranexus_SKB_F13/routes/ folder.
# Then register the blueprint in app.py (see INTEGRATION_GUIDE.md).

from flask import Blueprint, render_template, send_from_directory, jsonify
import os

dashboard_bp = Blueprint('dashboard', __name__)

# ── Serve the dashboard HTML ──────────────────────────────────
@dashboard_bp.route('/dashboard')
def dashboard():
    """
    Serves the CarbonKarma dMRV dashboard.
    Place dashboard.html in your templates/ folder.
    """
    return render_template('dashboard.html')


# ── Health check (dashboard pings this on load) ───────────────
@dashboard_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'TerraNexus CarbonKarma dMRV'})
