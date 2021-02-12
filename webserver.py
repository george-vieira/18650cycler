import json
import logging
import queue
import time
import uuid

from flask import Flask, send_from_directory
from flask import Response, request

# from waitress import serve

cRed = "\033[31m"
cGreen = "\033[32m"
cYellow = "\033[33m"
cBlue = "\033[34m"
cMag = "\033[35m"
cCyan = "\033[36m"
cNorm = "\033[0m"

cyclerqueue = queue.Queue()
webqueue = {}

app = Flask(__name__)


def get_request():
    rid = str(uuid.uuid4())
    webqueue[rid] = queue.Queue()
    return rid


def is_comms_busy():
    """

    :return:
    """
    if not cyclerqueue.empty() and len(cyclerqueue.queue) > 20:
        logging.debug("Cycler queue too busy: Empty? '{}'".format(cyclerqueue.empty()))
        logging.debug("Queue content: {}".format(list(cyclerqueue.queue)))
        return True


def wait_and_get_response(rid):
    """

    :return:
    """
    while webqueue[rid].empty():
        time.sleep(0.5)
    response = webqueue[rid].get()
    webqueue[rid].task_done()
    del webqueue[rid]
    logging.debug("SendingResponse: {}".format(response))
    return Response(response['message'], status=response['code'], mimetype=response['mimetype'])


@app.route('/js/<path:path>')
def send_js(path):
    """

    :param path:
    :return:
    """
    return send_from_directory('web/js', path)


@app.route('/img/<path:path>')
def send_img(path):
    """

    :param path:
    :return:
    """
    return send_from_directory('web/img', path)


@app.route('/css/<path:path>')
def send_css(path):
    """

    :param path:
    :return:
    """
    return send_from_directory('web/css', path)


@app.route('/', methods=['GET'])
@app.route('/<path:path>', methods=['GET'])
def root(path='index.html'):
    """

    :return:
    """
    return send_from_directory('web', path)


@app.route('/api/status/<int:slot_id>', methods=['POST'])
def api_status(slot_id):
    """

    :return:
    """
    payload = json.loads(request.stream.read().decode('utf-8'))
    logging.info("{}Requested: {} {}{}".format(cMag, request.path, payload, cNorm))
    if is_comms_busy():
        return Response("Comms service too busy", status=429)

    rid = get_request()
    cyclerqueue.put({'slot_id': slot_id, 'action': 'status', 'payload': payload, 'request_id': rid})
    return wait_and_get_response(rid)


@app.route('/api/stop/<int:slot_id>', methods=['POST'])
def api_stop(slot_id):
    """

    :return:
    """
    payload = json.loads(request.stream.read().decode('utf-8'))
    logging.info("{}Requested: {} {}{}".format(cMag, request.path, payload, cNorm))
    if is_comms_busy():
        return Response("Comms service too busy", status=429)

    rid = get_request()
    cyclerqueue.put({'slot_id': slot_id, 'action': 'stop', 'payload': payload, 'request_id': rid})
    return wait_and_get_response(rid)


@app.route('/api/charge/<int:slot_id>', methods=['POST'])
def api_charge(slot_id):
    """

    :return:
    """
    payload = json.loads(request.stream.read().decode('utf-8'))

    logging.info("{}Requested: {}{}".format(cMag, request.path, cNorm))
    if is_comms_busy():
        return Response("Comms service too busy", status=429)

    rid = get_request()
    cyclerqueue.put(
            {'slot_id': slot_id, 'action': 'charge', 'payload': format_request(payload), 'request_id': rid})
    return wait_and_get_response(rid)


@app.route('/api/cycle/<int:slot_id>', methods=['POST'])
def api_cycle(slot_id):
    """

    :return:
    """
    payload = json.loads(request.stream.read().decode('utf-8'))

    logging.info("{}Requested: {}{}".format(cMag, request.path, cNorm))
    if is_comms_busy():
        return Response("Comms service too busy", status=429)

    rid = get_request()
    cyclerqueue.put(
            {'slot_id': slot_id, 'action': 'cycle', 'payload': format_request(payload), 'request_id': rid})
    return wait_and_get_response(rid)


@app.route('/api/discharge/<int:slot_id>', methods=['POST'])
def api_discharge(slot_id):
    """

    :return:
    """
    payload = json.loads(request.stream.read().decode('utf-8'))

    logging.info("{}Requested: {}{}".format(cMag, request.path, cNorm))
    if is_comms_busy():
        return Response("Comms service too busy", status=429)

    rid = get_request()
    cyclerqueue.put(
            {'slot_id': slot_id, 'action': 'discharge', 'payload': format_request(payload), 'request_id': rid})
    return wait_and_get_response(rid)


@app.route('/api/history/<int:slot_id>', methods=['GET'])
def history(slot_id):
    """

    :param slot_id:
    :return:
    """
    logging.info("{}Requested: {}{}".format(cMag, request.path, cNorm))
    if is_comms_busy():
        return Response("Comms service too busy", status=429)

    rid = get_request()
    cyclerqueue.put({'slot_id': slot_id, 'action': 'history', 'payload': '{}', 'request_id': rid})
    return wait_and_get_response(rid)


def format_request(payload: dict):
    return {item['name']: item['value'] for item in payload}


def run_server():
    """

    :return:
    """
    logging.info("Webserver starting")
    app.run(host="0.0.0.0", port=8080)
