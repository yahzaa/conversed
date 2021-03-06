from ast import literal_eval
import json

from flask import render_template, request
import requests
import redis

from main import application, POOL
from utils import cleanup, validate
from config import API, API_KEY, LOCAL_DEV, API_STAT


@application.route('/')
def home():
    return render_template("home.html")


@application.route('/', methods=['POST'])
def profile():
    emailid = request.form['emailid'].strip()
    validated = validate(emailid)
    if not validated:
        return render_template("sorry.html")
    else:
        try:
            redis_server = redis.Redis(connection_pool=POOL)
            if not redis_server.exists(emailid):
                payload = {
                    'key': API_KEY,
                    'person_email': emailid,
                }
                response = requests.get(API, params=payload, verify=False)
                if response.status_code == 200:
                    data = json.loads(response.text)
                    if data.get('profile').get('status').get('has_person_data'):
                        cleaned_data = cleanup(data)
                        redis_server.set(emailid, json.dumps(cleaned_data))
                        redis_server.bgsave()
                else:
                    return render_template("sorry.html")
            try:
                data = json.loads(redis_server.get(emailid))
            except ValueError:
                data = literal_eval(redis_server.get(emailid))
            if data.get('profile').get('status').get('has_person_data', False):
                return render_template("data.html",
                                       user=data['profile']['person_data'])
            else:
                return render_template("sorry.html")
        except (requests.exceptions.ConnectionError, TypeError):
            return render_template("sorry.html")


@application.route('/status/')
def api_status():
    payload = {
        'key': API_KEY,
    }
    response = requests.get(API_STAT, params=payload, verify=False)
    if response.status_code == 200:
        data = json.loads(response.text)
        return render_template("status.html", data=data)
    else:
        return render_template("home.html")


@application.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404
