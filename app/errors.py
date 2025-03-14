import traceback
from flask import current_app as app, redirect
from flask import render_template, request, jsonify
from werkzeug.http import HTTP_STATUS_CODES
import re

from sqlalchemy.exc import OperationalError

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
    # Check if the requested URL matches a specific resource pattern,
    # e.g. URLs that look like '/items/<id>' or '/users/<id>'.
    missing_resource = False
    resource_message = None

    # Example: if your item URLs are like /items/<id>
    match = re.match(r'^/(?:customers|instruments|rentals)(?:/.*)?$', request.path)
    if match:
        missing_resource = True
        resource_message = "The requested item could not be found."

    # You can add more patterns for other resources if needed.

    # If JSON is accepted, return JSON response
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        payload = {'error': 'Not Found'}
        if missing_resource:
            payload['message'] = resource_message
        else:
            payload['message'] = 'The requested route was not found.'
        response = jsonify(payload)
        response.status_code = 404
        return response

    # If it's an API request with a specific pattern
    if request.path.startswith('/api'):
        return jsonify({
            'error': 'Not Found',
            'message': resource_message or 'The requested resource was not found on the server.'
        }), 404

    # For normal HTML response, pass additional context to your template
    return render_template('errorpages/404.html',
                           missing_resource=missing_resource,
                           message=resource_message), 404


# errorhandler for db connection gone away
@app.errorhandler(OperationalError)
def db_connection_error(error):
    # Check if the error is due to a lost database connection
    connection_lost = False
    # Some drivers provide an error code in error.orig.args
    try:
        error_code = error.orig.args[0]
        # MySQL server has gone away error code is 2006
        if error_code == 2006:
            connection_lost = True
    except (AttributeError, IndexError, TypeError):
        pass

    if connection_lost:
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            response = jsonify({
                'error': 'Database Connection Error',
                'message': 'MySQL server has gone away. The database connection was lost. Please retry the operation.'
            })
            response.status_code = 500
            return response
        else:
            return redirect(request.url)

    # Fallback for other OperationalErrors
    return render_template('errorpages/500.html'), 500


# errorhandler for 500 internal server error
@app.errorhandler(500)
def internal_server_error(error):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'Internal Server Error'})
        response.status_code = 500
        return response
    else:
        return render_template('errorpages/500.html'), 500


@app.errorhandler(Exception)
def handle_all_exceptions(error):
    # Log details about the error
    app.logger.error(f"Unhandled Exception: {error}")
    app.logger.error(traceback.format_exc())

    # For API endpoints or JSON requests, return a JSON response
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."})
        response.status_code = 500
        return response

    # For regular browser requests, render a friendly error page
    return render_template("errorpages/500.html"), 500
