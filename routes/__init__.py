# Part 1 routes
from .satellite import satellite_bp
from .fusion import fusion_bp
from .awd import awd_bp
from .methane import methane_bp

# Part 2 routes
from .part2.verification import verification_bp
from .part2.credits import credits_bp
from .part2.analytics import analytics_bp
from .part2.report import report_bp
from .part2.llm_insights import llm_bp

# Internal admin routes
from .internal import internal_bp
