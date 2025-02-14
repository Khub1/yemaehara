from flask import Blueprint, jsonify, request, render_template
from app.services import dp_algo


routes = Blueprint('routes', __name__)

@routes.route('/')
def home():
    return render_template('index.html')

@routes.route('/optimize', methods=['POST'])
def optimize():
    return dp_algo()


