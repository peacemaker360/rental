from flask import current_app as app
from flask import render_template, request, jsonify
from werkzeug.http import HTTP_STATUS_CODES

from app import db

#################################
# Error handling routes
# Quelle: Übernommen aus den Beispielen
#################################


def error_response(status_code, message=None):
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload)
    response.status_code = status_code
    return response


def bad_request(message):
    return error_response(400, message)


@app.errorhandler(403)
def unauthorized(error):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'Forbidden'})
        response.status_code = 403
        return response
    else:
        return render_template('errorpages/403.html'), 403


@app.errorhandler(404)
def not_found_error(error):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'Not Found'})
        response.status_code = 404
        return response
    # Customise all 404 route errors on the api
    if request.path.startswith('/api'):
        return jsonify({'error': 'Not Found', 'message': 'The requested resource was not found on the server.'}), 404
    else:
        return render_template('errorpages/404.html'), 404


@app.errorhandler(500)
def not_found_error(error):
    db.session.rollback()
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'Internal Server Error'})
        response.status_code = 500
        return response
    else:
        return render_template('errorpages/500.html'), 500
