import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import logging
import os

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_quiz')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=True)

# Global variables
eleves = {}
bonne_reponse = None
numero_question = 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/eleve')
def eleve():
    return render_template('eleve.html')

@app.route('/enseignant')
def enseignant():
    return render_template('enseignant.html')

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on_error_default
def default_error_handler(e):
    logger.error(f"Socket.IO error: {str(e)}")

@socketio.on('enregistrer_infos')
def enregistrer_infos(data):
    try:
        email = data.get('email')
        if not email:
            logger.warning("Attempted registration without email")
            return
            
        logger.info(f"Registering student: {email}")
        eleves[email] = {
            'prenom': data.get('prenom', ''),
            'nom': data.get('nom', ''),
            'reponses': {},
            'score': 0
        }
        emit('maj_eleves', eleves, broadcast=True)
    except Exception as e:
        logger.error(f"Error in enregistrer_infos: {str(e)}")

@socketio.on('poser_question')
def poser_question(data):
    try:
        global bonne_reponse, numero_question
        logger.info(f"New question: {data}")
        bonne_reponse = data.get('bonne_reponse')
        numero_question = int(data.get('numero_question', 0))
        emit('nouvelle_question', {'numero_question': numero_question}, broadcast=True)
    except Exception as e:
        logger.error(f"Error in poser_question: {str(e)}")

@socketio.on('envoyer_reponse')
def recevoir_reponse(data):
    try:
        email = data.get('email')
        reponse = data.get('reponse')
        
        if not email or not reponse or email not in eleves:
            logger.warning(f"Invalid response data: {data}")
            return
            
        logger.info(f"Response from {email}: {reponse}")
        
        correct = (reponse == bonne_reponse)
        eleves[email]['reponses'][numero_question] = {'reponse': reponse, 'correct': correct}
        
        if correct:
            eleves[email]['score'] += 1
            
        emit('maj_eleves', eleves, broadcast=True)
    except Exception as e:
        logger.error(f"Error in envoyer_reponse: {str(e)}")

@socketio.on('sauvegarder')
def sauvegarder():
    try:
        # Here you would implement saving to a file or database
        # For example:
        import json
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quiz_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(eleves, f)
            
        logger.info(f"Session saved to {filename}")
        emit('sauvegarde_complete', {'filename': filename}, broadcast=True)
    except Exception as e:
        logger.error(f"Error in sauvegarder: {str(e)}")

@socketio.on('reset')
def reset():
    try:
        global eleves, bonne_reponse, numero_question
        eleves = {}
        bonne_reponse = None
        numero_question = 0
        logger.info("Session reset")
        emit('maj_eleves', eleves, broadcast=True)
    except Exception as e:
        logger.error(f"Error in reset: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)