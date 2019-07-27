import json

from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password

from .models import Plant, User
from .utils import formulate_response, session_validation
from bson.objectid import ObjectId

"""
Add a new plant to the database
Only listen to POST requests.
"""
@csrf_exempt
def create_plant(request):
    if request.method != "POST" or request.body == None:
        response_success = False
        response_message = "Only POST requests are allowed on this route"
        response_code = 300
        return formulate_response(response_message, response_success, response_code)

    body = json.loads(request.body)
    Plant.objects.mongo_insert(body)
    response_success = True
    response_message = "Plant inserted succesfully"
    response_code = 200
    return formulate_response(response_message, response_success, response_code)


@csrf_exempt
def retrieve_plant(request, id):
    # Only listen to GET requests
    if request.method != "GET":
        response_success = False
        response_message = "Only GET requests are allowed on this route"
        response_code = 300
        return formulate_response(response_message, response_success, response_code)

    plant = Plant.objects.mongo_find_one({'_id': ObjectId(id)})
    # Plant not found
    if plant == None:
        response_success = False
        response_message = "No such plant exists"
        response_code = 400
        return formulate_response(response_message, response_success, response_code)

    plant = dict(plant)
    plant['_id'] = id
    response_message = "account created succesfully"
    response_success = True
    response_code = 200
    response_data = plant
    return formulate_response(response_message, response_success, response_code, response_data)


@csrf_exempt
def sign_up(request):
   # response attributes
    response_message = "account created succesfully"
    response_success = True
    response_code = 200

    # Only listen to POST requests
    if request.method != "POST" or request.body == None:
        response_success = False
        response_message = "Only POST requests are allowed on this route"
        response_code = 300
        return formulate_response(response_message, response_success, response_code)

    body = json.loads(request.body)
    # fail if no sign up information
    if not body["password"] or not body["email"]:
        response_success = False
        response_message = "incomplete data"
        response_code = 300
        return formulate_response(response_message, response_success, response_code)

    body["password"] = make_password(body["password"])
    tmp_user = {
        'email': body['email'],
        'password': body['password'],
        'premium': False,
        'grid': []
    }
    User.objects.mongo_insert(tmp_user)

    return formulate_response(response_message, response_success, response_code)


@csrf_exempt
def log_in(request):
    # response attributes
    response_message = "login successful"
    response_success = True
    response_code = 200
    print(request.session.session_key)
    # Only listen to POST requests
    if request.method != "POST" or request.body == None:
        response_success = False
        response_message = "Only POST requests are allowed on this route"
        response_code = 300
        return formulate_response(response_message, response_success, response_code)

    if request.session.exists(request.session.session_key):
        # validate and obtain user info from session
        user_email = session_validation(request.session.session_key)
        print("user: ", user_email)
        response_message = "already logged in user"
        response_success = False
        response_code = 300
        candidate_user = User.objects.mongo_find_one({"email": user_email})
        candidate_user = dict(candidate_user)
        del candidate_user['_id']
        del candidate_user['password']
        return formulate_response(response_message, response_success, response_code, candidate_user)

    # load body
    body = json.loads(request.body)

    # fail if no sign up information
    if not body["password"] or not body["email"]:
        response_success = False
        response_message = "missing login information"
        response_code = 300
        return formulate_response(response_message, response_success, response_code)

    # get user from DB
    candidate_user = User.objects.mongo_find_one({"email": body["email"]})

    if candidate_user is None:
        response_success = False
        response_message = "Incorrect email"
        response_code = 300
    elif not check_password(body["password"], candidate_user["password"]):
        response_success = False
        response_message = "Incorrect password"
        response_code = 300
    else:  # login granted
        print("creating new session")
        candidate_user = dict(candidate_user)
        request.session.create()
        request.session["user_email"] = body["email"]

    return formulate_response(response_message, response_success, response_code, candidate_user)

@csrf_exempt
def add_plant_to_grid(request):
    # Only listen to PUT requests
    if request.method != "PUT" or request.body == None:
        response_success = False
        response_message = "Only PUT requests are allowed on this route"
        response_code = 300
        return formulate_response(response_message, response_success, response_code)

    user_email = session_validation(request.session.session_key)
    if user_email is None:
        response_success = False
        response_message = "Internal server error. Session was not found."
        response_code = 500
        return formulate_response(response_message, response_success, response_code)

    user = User.objects.mongo_find_one({'email': user_email})
    user = dict(user)

    body = json.loads(request.body)

    plant = Plant.objects.mongo_find_one({'name': body['plant_name']})
    # Plant not found
    if plant is None:
        response_success = False
        response_message = "No such plant exists"
        response_code = 300
        return formulate_response(response_message, response_success, response_code)
    
    plant = dict(plant)
    del plant['_id']
    tmp_cell = {
        'positionX': body['positionX'],
        'positionY': body['positionY'],
        'crop': plant,
        'current_moisture': plant['moisture_threshold']
    }
    user['grid'].append(tmp_cell)
    User.objects.mongo_update_one({'_id': user['_id']}, {'$set': user}, upsert=False)
    del user['_id']
    del user['password']
    response_success = True
    response_message = "User updated successfully"
    response_code = 200
    return formulate_response(response_message, response_success, response_code, user)
