from flask import Flask, render_template, jsonify, session, redirect, url_for, request
import os
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/label')
def label():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template('label.html', user_id=session.get('user_id'), stats={
        'user': {'total': 0, 'relevant': 0, 'irrelevant': 0},
        'overall': {'total': 0, 'labeled': 0, 'unlabeled': 0}
    })

@app.route('/set_user', methods=['POST'])
def set_user():
    user_id = request.form.get('user_id')
    if user_id:
        session['user_id'] = user_id
        return redirect(url_for('label'))
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True)