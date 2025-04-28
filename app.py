import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

eleves = {}
bonne_reponse = None
numero_question = 0

@app.route('/eleve')
def eleve():
    return render_template('eleve.html')

@app.route('/enseignant')
def enseignant():
    return render_template('enseignant.html')

@socketio.on('enregistrer_infos')
def enregistrer_infos(data):
    eleves[data['email']] = {'prenom': data['prenom'], 'nom': data['nom'], 'reponses': {}}
    emit('maj_eleves', eleves, broadcast=True)

@socketio.on('poser_question')
def poser_question(data):
    global bonne_reponse, numero_question
    bonne_reponse = data['bonne_reponse']
    numero_question = data['numero_question']
    emit('nouvelle_question', {'numero_question': numero_question}, broadcast=True)

@socketio.on('envoyer_reponse')
def recevoir_reponse(data):
    email = data['email']
    reponse = data['reponse']
    correct = (reponse == bonne_reponse)
    if email in eleves:
        eleves[email]['reponses'][numero_question] = {'reponse': reponse, 'correct': correct}
        # Incrémenter le score
        if 'score' not in eleves[email]:
            eleves[email]['score'] = 0
        if correct:
            eleves[email]['score'] += 1
    emit('maj_eleves', eleves, broadcast=True)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)




