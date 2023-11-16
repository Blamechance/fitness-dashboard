from flask import Blueprint

# Defining a blueprint
admin_bp = Blueprint(
    'user_data_processing_bp', __name__,
    template_folder='templates',
    static_folder='static'
)