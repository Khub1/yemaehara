from flask import Blueprint, jsonify
from app.services import create_lote, simulate_lote, get_aviaries, get_lotes, assign_and_print_aviaries_lotes


routes = Blueprint('routes', __name__)

@routes.route('/')
def home():
    return jsonify({"message": "Flask Backend is running!"})

@routes.route('/lote_create')
def lote_creation():
    lote = create_lote(plote_raza_id=1, pad_id=66, id_escenario=10)  
    result = simulate_lote(lote, t=18)

    return result

@routes.route('/get_aviaries')
def aviaries():
    return get_aviaries()

@routes.route('/get_lotes', methods=['GET'])
def lotes():
    return get_lotes()

@routes.route('/assign_and_print_aviaries_lotes', methods=['GET'])
def assing_and_print_aviaries_lotes_route():
    return assign_and_print_aviaries_lotes()

