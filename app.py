from flask import Flask, render_template, request, make_response, g
from redis import Redis
import os
import socket
import random
import json
import logging

option_a = os.getenv('OPTION_A', "Cats")
option_b = os.getenv('OPTION_B', "Dogs")
option_c = os.getenv('OPTION_C', "Birds")
hostname = socket.gethostname()

app = Flask(__name__)

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host="redis", db=0, socket_timeout=5)
    return g.redis

@app.route("/", methods=['POST','GET'])
def hello():
    voter_id = request.cookies.get('voter_id')
    if not voter_id:
        voter_id = hex(random.getrandbits(64))[2:-1]

    votes_left = 3 - get_vote_count(voter_id)

    if request.method == 'POST':
        if votes_left > 0:
            redis = get_redis()
            vote = request.form['vote']
            app.logger.info('Received vote for %s', vote)
            data = json.dumps({'voter_id': voter_id, 'vote': vote})
            redis.rpush('votes', data)
            votes_left -= 1
        else:
            app.logger.info('User %s has already used all their votes', voter_id)

    resp = make_response(render_template(
        'index.html',
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
        hostname=hostname,
        votes_left=votes_left,
    ))
    resp.set_cookie('voter_id', voter_id)
    return resp

def get_vote_count(voter_id):
    redis = get_redis()
    votes = redis.lrange('votes', 0, -1)
    count = 0
    for vote in votes:
        data = json.loads(vote)
        if data['voter_id'] == voter_id:
            count += 1
    return count


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)

