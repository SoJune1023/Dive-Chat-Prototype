# <---------- Route ---------->
from flask import Blueprint, jsonify, request

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/register', methods = ['POST'])
def register():
    pass

@user_bp.route('/signin', methods = ['POST'])
def signin():
    pass