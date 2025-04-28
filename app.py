import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import logging
import os
import json
import datetime

# Configuration des logs
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_quiz')

# Configuration de Socket.IO optimisée pour Render
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

# Variables globales
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
    logger.info(f"Client connecté: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client déconnecté: {request.sid}")

@socketio.on_error_default
def default_error_handler(e):
    logger.error(f"Erreur Socket.IO: {str(e)}")

@socketio.on('enregistrer_infos')
def enregistrer_infos(data):
    try:
        email = data.get('email')
        if not email:
            logger.warning("Tentative d'inscription sans email")
            return
            
        logger.info(f"Inscription de l'élève: {email}")
        eleves[email] = {
            'prenom': data.get('prenom', ''),
            'nom': data.get('nom', ''),
            'reponses': {},
            'score': 0
        }
        emit('maj_eleves', eleves, broadcast=True)
    except Exception as e:
        logger.error(f"Erreur dans enregistrer_infos: {str(e)}")

@socketio.on('poser_question')
def poser_question(data):
    try:
        global bonne_reponse, numero_question
        logger.info(f"Nouvelle question: {data}")
        bonne_reponse = data.get('bonne_reponse')
        numero_question = int(data.get('numero_question', 0))
        emit('nouvelle_question', {'numero_question': numero_question}, broadcast=True)
    except Exception as e:
        logger.error(f"Erreur dans poser_question: {str(e)}")

@socketio.on('envoyer_reponse')
def recevoir_reponse(data):
    try:
        email = data.get('email')
        reponse = data.get('reponse')
        
        if not email or not reponse:
            logger.warning(f"Données de réponse invalides: {data}")
            return
            
        if email not in eleves:
            logger.warning(f"Email non enregistré: {email}")
            return
            
        logger.info(f"Réponse de {email}: {reponse}")
        
        correct = (reponse == bonne_reponse)
        eleves[email]['reponses'][numero_question] = {'reponse': reponse, 'correct': correct}
        
        if correct:
            eleves[email]['score'] += 1
            
        emit('maj_eleves', eleves, broadcast=True)
    except Exception as e:
        logger.error(f"Erreur dans envoyer_reponse: {str(e)}")

@socketio.on('sauvegarder')
def sauvegarder():
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quiz_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(eleves, f)
            
        logger.info(f"Session sauvegardée dans {filename}")
        emit('sauvegarde_complete', {'filename': filename}, broadcast=True)
    except Exception as e:
        logger.error(f"Erreur dans sauvegarder: {str(e)}")

@socketio.on('reset')
def reset():
    try:
        global eleves, bonne_reponse, numero_question
        eleves = {}
        bonne_reponse = None
        numero_question = 0
        logger.info("Session réinitialisée")
        emit('maj_eleves', eleves, broadcast=True)
    except Exception as e:
        logger.error(f"Erreur dans reset: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)