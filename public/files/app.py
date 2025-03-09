# CertifyEasy - Qbank Web App (Flask)
import csv
import random
import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import bcrypt
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certifyeasy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam = db.Column(db.String(50), nullable=False)
    part = db.Column(db.String(50), nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    completed_questions = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)

class WrongAnswers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam = db.Column(db.String(50), nullable=False)
    part = db.Column(db.String(50), nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(100), nullable=False)
    options = db.Column(db.String(500), nullable=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

EXAMS = {
    "CIA": {
        "1": "Part 1: Essentials of Internal Auditing",
        "2": "Part 2: Practice of Internal Auditing",
        "3": "Part 3: Business Knowledge for Internal Auditing"
    },
    "CISA": {"": "Certified Information Systems Auditor"},
    "CFA": {"": "Chartered Financial Analyst Level 1"}
}

def load_qbank(exam, part):
    filename = f"QBANK_{exam}{part}.csv"
    file_path = os.path.join(os.path.dirname(__file__), filename)
    qbank_by_subject = {}
    encodings = ['utf-8', 'latin1', 'windows-1252']
    for encoding in encodings:
        try:
            with open(file_path, newline='', encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    subject = row["subject"]
                    qbank_by_subject.setdefault(subject, []).append({
                        "question": row["question"],
                        "options": [row["option1"], row["option2"], row["option3"], row["option4"]],
                        "answer": row["answer"],
                        "explanation": row["explanation"]
                    })
            print(f"Loaded Qbank: {filename} with subjects: {list(qbank_by_subject.keys())}")
            return qbank_by_subject
        except FileNotFoundError:
            return {}
        except Exception as e:
            print(f"Error loading {filename} with {encoding}: {e}")
    return {}

qbanks = {}
for exam in EXAMS:
    qbanks[exam] = {}
    for part in EXAMS[exam]:
        qbanks[exam][part] = load_qbank(exam, part)

sessions = {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def root():
    if current_user.is_authenticated:
        progress_by_exam = {}
        for exam in EXAMS:
            total_completed = sum(p.completed_questions for p in Progress.query.filter_by(user_id=current_user.id, exam=exam).all())
            total_questions = sum(p.total_questions for p in Progress.query.filter_by(user_id=current_user.id, exam=exam).all())
            progress_by_exam[exam] = (total_completed / total_questions * 100) if total_questions > 0 else 0
        return render_template('index.html', exams=EXAMS, progress=progress_by_exam, username=current_user.username)
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if len(password) < 6:
            flash('Password must be at least 6 characters.')
            return redirect(url_for('signup'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('signup'))
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(username=username, password_hash=hashed)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('root'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash):
            login_user(user)
            return redirect(url_for('root'))
        flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/subjects', methods=['POST'])
@login_required
def get_subjects():
    exam = request.form['exam'].strip()
    part = request.form['part'].strip() if request.form['part'].strip() else ""
    print(f"Fetching subjects for {exam} {part}")
    subjects = list(qbanks.get(exam, {}).get(part, {}).keys())
    print(f"Subjects found: {subjects}")
    progress_by_subject = {}
    for subject in subjects:
        prog = Progress.query.filter_by(user_id=current_user.id, exam=exam, part=part, subject=subject).first()
        progress_by_subject[subject] = (prog.completed_questions / prog.total_questions * 100) if prog and prog.total_questions > 0 else 0
    return jsonify({"subjects": subjects, "progress": progress_by_subject})

@app.route('/start', methods=['POST'])
@login_required
def start():
    exam = request.form['exam'].strip()
    part = request.form['part'].strip() if request.form['part'].strip() else ""
    subject = request.form['subject'].strip()
    print(f"Starting practice for {exam} {part} {subject}")
    qbank = qbanks.get(exam, {}).get(part, {}).get(subject, [])
    if not qbank:
        return jsonify({"error": f"No questions available for {exam} {part} {subject}."}), 400
    
    prog = Progress.query.filter_by(user_id=current_user.id, exam=exam, part=part, subject=subject).first()
    if not prog:
        prog = Progress(user_id=current_user.id, exam=exam, part=part, subject=subject, total_questions=len(qbank))
        db.session.add(prog)
        db.session.commit()
    
    session_data = {
        "exam": exam,
        "part": part,
        "subject": subject,
        "qbank": qbank.copy(),
        "current_qbank_index": 0,
        "wrong_answers": [],
        "next_question": None,
        "original_total": len(qbank),
        "correct_streak": 0,
        "mastery_correct": prog.completed_questions,
        "mastery_total": prog.total_questions,
        "longest_streak": 0,
        "explanations": []
    }
    random.shuffle(session_data["qbank"])
    session_data["next_question"] = session_data["qbank"][0]
    sessions[current_user.id] = session_data
    progress = (session_data["current_qbank_index"] / session_data["original_total"] * 100) if session_data["original_total"] > 0 else 0
    mastery_percentage = (session_data["mastery_correct"] / session_data["mastery_total"] * 100) if session_data["mastery_total"] > 0 else 0
    return jsonify({
        "exam": exam,
        "part": part,
        "subject": subject,
        "question": session_data["next_question"],
        "index": 0,
        "progress": progress,
        "retry_queue": len(session_data["wrong_answers"]),
        "mastery_percentage": mastery_percentage,
        "correct_streak": 0,
        "message": ""
    })

@app.route('/answer', methods=['POST'])
@login_required
def answer():
    try:
        exam = request.form.get('exam')
        part = request.form.get('part', "")
        subject = request.form.get('subject')
        user_answer = request.form.get('answer')
        index = int(request.form.get('index', 0))
        question_json = request.form.get('question', '{}')
        
        if not exam or not subject:
            return jsonify({"error": "Invalid or missing exam/subject"}), 400
        if not user_answer:
            return jsonify({"error": "No answer provided"}), 400
        
        try:
            question = json.loads(question_json) if question_json else {}
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return jsonify({"error": "Invalid question data"}), 400
        
        if not question or "question" not in question:
            return jsonify({"error": "Missing question data"}), 400
        
        session = sessions.get(current_user.id)
        user_answer_idx = int(user_answer) - 1
        correct_answer = question["answer"]
        user_answer_text = question["options"][user_answer_idx]

        feedback = {
            "correct": user_answer_text == correct_answer,
            "user_answer": f"{chr(65 + user_answer_idx)}) {user_answer_text}",
            "correct_answer": f"{chr(65 + question['options'].index(correct_answer))} {correct_answer}",
            "explanation": question["explanation"]
        }
        
        if "retry_count" not in question:
            question["retry_count"] = 0
        
        if feedback["correct"]:
            session["mastery_correct"] += 1
            session["correct_streak"] += 1
            session["longest_streak"] = max(session["longest_streak"], session["correct_streak"])
            prog = Progress.query.filter_by(user_id=current_user.id, exam=exam, part=part, subject=subject).first()
            prog.completed_questions += 1
            db.session.commit()
            if question["retry_count"] > 0:
                wrong_entry = WrongAnswers.query.filter_by(
                    user_id=current_user.id, exam=exam, part=part, subject=subject, question_text=question["question"]
                ).first()
                if wrong_entry:
                    db.session.delete(wrong_entry)
                    db.session.commit()
        else:
            session["correct_streak"] = 0
            question["retry_count"] += 1
            if question["retry_count"] <= 2:
                wrong_question = {
                    "question": question["question"],
                    "options": question["options"].copy(),
                    "answer": correct_answer,
                    "explanation": f"Retry #{question['retry_count']}: {question['explanation']}",
                    "retry_count": question["retry_count"]
                }
                session["wrong_answers"].append(wrong_question)
                print(f"Queued wrong answer (retry {question['retry_count']}): {question['question']}")
            if question["retry_count"] == 1:
                existing_wrong = WrongAnswers.query.filter_by(
                    user_id=current_user.id, exam=exam, part=part, subject=subject, question_text=question["question"]
                ).first()
                if not existing_wrong:
                    wrong = WrongAnswers(
                        user_id=current_user.id, exam=exam, part=part, subject=subject,
                        question_text=question["question"], correct_answer=correct_answer,
                        options=json.dumps(question["options"]), answered_at=datetime.utcnow()
                    )
                    db.session.add(wrong)
                    db.session.commit()
        
        session["current_qbank_index"] += 1
        
        next_q = None
        if session["current_qbank_index"] < len(session["qbank"]):
            next_q = session["qbank"][session["current_qbank_index"]]
        elif session["wrong_answers"]:
            next_q = session["wrong_answers"].pop(0)
            print(f"Qbank exhausted, serving wrong answer: {next_q['question']}")
        else:
            mastery_percentage = (session["mastery_correct"] / session["mastery_total"] * 100) if session["mastery_total"] > 0 else 0
            return jsonify({
                "exam": exam,
                "part": part,
                "subject": subject,
                "feedback": feedback,
                "finished": True,
                "wrong_count": WrongAnswers.query.filter_by(user_id=current_user.id, exam=exam, part=part, subject=subject).count(),
                "correct_count": session["mastery_correct"],
                "original_total": session["original_total"],
                "mastery_percentage": mastery_percentage,
                "longest_streak": session["longest_streak"]
            })

        options = next_q["options"].copy()
        random.shuffle(options)
        next_q["options"] = options
        session["next_question"] = next_q

        progress = (session["current_qbank_index"] / session["original_total"] * 100) if session["original_total"] > 0 else 100
        mastery_percentage = (session["mastery_correct"] / session["mastery_total"] * 100) if session["mastery_total"] > 0 else 0
        return jsonify({
            "exam": exam,
            "part": part,
            "subject": subject,
            "feedback": feedback,
            "next_question": session["next_question"],
            "index": session["current_qbank_index"],
            "progress": min(progress, 100),
            "retry_queue": len(session["wrong_answers"]),
            "mastery_percentage": mastery_percentage,
            "correct_streak": session["correct_streak"]
        })
    except Exception as e:
        print(f"Error in /answer: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)