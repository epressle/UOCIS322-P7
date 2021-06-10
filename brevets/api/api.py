import os
import sys
from pymongo import MongoClient
from flask import Flask, request, jsonify, abort, Response
from flask_restful import Resource, Api
from passlib.hash import sha256_crypt as pwd_context
import json
from itsdangerous import (TimedJSONWebSignatureSerializer \
                                  as Serializer, BadSignature, \
                                  SignatureExpired)

app = Flask(__name__)
api = Api(app)

SALT = '4CzsbzrtlOFzWOpr'
SECRET_KEY = "x6sgBrQRWx2bUoL48xo7Jxt5eH41XN0rkuPneC4lcK42Z4fJoSeGrzwVObg5W2ko"

client = MongoClient('mongodb://' + os.environ['MONGODB_HOSTNAME'], 27017)
db = client.brevetdb

def verify_token(token):
    s = Serializer(SECRET_KEY, expires_in=10)
    try:
        data = s.loads(token)
    except SignatureExpired:
        app.logger.debug("Token expired!")
        return False
    except BadSignature:
        app.logger.debug("Invalid token!")
        return False
    app.logger.debug("Token is still valid!")
    return True


def csv_convert(data, out):
    str = ""
    data = data[1:]
    data = data[:-1]
    app.logger.debug("data str = " + data)

    data = data.replace('"', "")
    data = data.replace("'", "")
    data = data.replace(" ", "")
    data = data.replace("{", "")
    data = data.replace("}", "")

    if out == 'open':
        str += "open_times\n"
        while data:
            start_val = data.find("[")
            end_val = data.find("]")
            snippet = data[start_val + 1:end_val]
            o_times = snippet.split(",")
            for x in o_times:
                str += x + "\n"
            remove_str = 'open_times:[' + snippet + ']'
            data = data.replace(remove_str + ",", "")
            data = data.replace(remove_str, "")
    elif out == 'close':
        str += "close_times\n"
        while data:
            start_val = data.find("[")
            end_val = data.find("]")
            snippet = data[start_val + 1:end_val]
            c_times = snippet.split(",")
            for x in c_times:
                str += x + "\n"
            remove_str = 'close_times:[' + snippet + ']'
            app.logger.debug('remove_str = ' + remove_str)
            data = data.replace(remove_str + ",", "")
            data = data.replace(remove_str, "")
    else:
        remove_str = ""
        str += "open_times,close_times\n"
        count = 0
        while data:
            app.logger.debug(data)
            start_val = data.find("[")
            end_val = data.find("]")
            snippet = data[start_val + 1:end_val]
            a_times = snippet.split(",")
            for x in a_times:
                str += x
                if count % 2 == 0:
                    str += " "
                else:
                    str += "\n"
            if count % 2 == 0:
                remove_str = 'open_times:[' + snippet + ']'
            else:
                remove_str = 'close_times:[' + snippet + ']'
            app.logger.debug('remove_str = ' + remove_str)
            data = data.replace(remove_str + ",", "")
            data = data.replace(remove_str, "")
            count += 1
    return str


def get_data(type_arg='all'):
    num = request.args.get('top', type=int)
    if num is None or num <= 0:
        num = sys.maxsize
    if type_arg == 'close':
        entries = db.brevetdb.find({}, {'_id': 0, 'brev_distance': 0, 'open_times': 0, 'kms': 0}).limit(num)
    elif type_arg == 'open':
        entries = db.brevetdb.find({}, {'_id': 0, 'brev_distance': 0, 'close_times': 0, 'kms': 0}).limit(num)
    else:
        entries = db.brevetdb.find({}, {'_id': 0, 'brev_distance': 0, 'kms': 0}).limit(num)
    entries = str(list(entries))
    app.logger.debug("entries in get_data = " + entries)
    return entries


class ListAll(Resource):
    def get(self, ext='json'):
        token = request.args.get('token', type=str)
        if not verify_token(token):
            app.logger.debug("Token is invalid!")
            abort(401)
        entries = get_data('all')
        if ext == 'csv':
            return csv_convert(entries, 'all')
        else:
            return entries

class ListOpenOnly(Resource):
    def get(self, ext='json'):
        token = request.args.get('token', type=str)
        if not verify_token(token):
            app.logger.debug("Token is invalid!")
            abort(401)
        entries = get_data('open')
        if ext == 'csv':
            return csv_convert(entries, 'open')
        else:
            return entries

class ListCloseOnly(Resource):
    def get(self, ext='json'):
        token = request.args.get('token', type=str)
        if not verify_token(token):
            app.logger.debug("Token is invalid!")
            abort(401)
        entries = get_data('close')
        if ext == 'csv':
            return csv_convert(entries, 'close')
        else:
            return entries

class Register(Resource):
    def post(self):
        uname = request.args.get('uname', type=str)
        app.logger.debug("username = " + uname)
        if db.accounts.find_one({'username': uname}) is not None:
            # account already exists
            app.logger.debug("The user exists already! ABORT 400")
            abort(400)
        password = request.args.get('pass', type=str)
        entry = {
            'username': uname,
            'password': password
        }
        app.logger.debug("entry = " + str(entry))
        jsonified = jsonify(entry)
        jsonified.status_code = 201
        app.logger.debug("JSONified entry = " + str(jsonified))
        db.accounts.insert_one(entry)
        return jsonified

class Token(Resource):
    def get(self, expiration=600):
        uname = request.args.get('uname', type=str)
        acc = db.accounts.find_one({'username': uname})
        if not acc:
            # return 401, username does not exist
            app.logger.debug("Username does not exist!")
            abort(401)
        password = request.args.get('pass', type=str)
        if acc['password'] != password:
            app.logger.debug("Password does not match!")
            abort(401)
        app.logger.debug("Username, password match!")
        s = Serializer(SECRET_KEY, expires_in=expiration)
        app.logger.debug("s generated!")
        app.logger.debug("id = " + str(acc['_id']))
        token = s.dumps({'id': str(acc['_id'])})
        app.logger.debug("Token generated!")
        if not verify_token(token):
            app.logger.debug("Token is invalid!")
            abort(401)
        # token has some oddities at the start and the last character, get rid of those
        token = str(token)[2:]
        token = token[:-1]
        entry = {
            'id': str(acc['_id']),
            'username': uname,
            'token': token,
            'duration': expiration
        }
        app.logger.debug("entry = " + str(entry))
        jsonified = jsonify(entry)
        app.logger.debug("JSONified entry = " + str(jsonified))
        jsonified.status_code = 200
        return jsonified


# Create routes
# Another way, without decorators
api.add_resource(ListAll, '/listAll', '/listAll/<string:ext>')
api.add_resource(ListOpenOnly, '/listOpenOnly', '/listOpenOnly/<string:ext>')
api.add_resource(ListCloseOnly, '/listCloseOnly', '/listCloseOnly/<string:ext>')
api.add_resource(Register, '/register')
api.add_resource(Token, '/token')

# Run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
