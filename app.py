from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)


# SQlite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///questions.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_type = db.Column(db.String(50), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=True)  # For multiple-choice questions
    correct_answer = db.Column(db.String(255), nullable=False)
    feedback = db.Column(db.Text, nullable=True)

with app.app_context():
    db.create_all()

@app.route("/")
def dashboard():
    questions = Question.query.all()
    return render_template("dashboard.html", questions=questions)

@app.route("/add_question", methods=["GET", "POST"])
def add_question():
    if request.method == "POST":
        question_type = request.form.get("question_type")
        question_text = request.form.get("question_text")
        options = request.form.get("options")  # Optional (comma-separated for MCQs)
        correct_answer = request.form.get("correct_answer")
        feedback = request.form.get("feedback")

        question = Question(
            question_type=question_type,
            question_text=question_text,
            options=options,
            correct_answer=correct_answer,
            feedback=feedback,
        )
        db.session.add(question)
        db.session.commit()

        return redirect(url_for("dashboard"))
    return render_template("add_question.html")


@app.route("/api/questions", methods=["GET"])
def get_questions():
    questions = Question.query.all()
    questions_list = [
        {
            "id": question.id,
            "type": question.question_type,
            "text": question.question_text,
            "options": question.options.split(",") if question.options else None,
            "correct_answer": question.correct_answer,
            "feedback": question.feedback,
        }
        for question in questions
    ]
    return jsonify(questions_list)


@app.route("/delete_question/<int:question_id>")
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for("dashboard"))


user_states = {}

@app.route("/webhook", methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').lower()
    sender = request.values.get('From')
    
    resp = MessagingResponse()
    msg = resp.message()
    
    # Check if user is in middle of quiz
    if sender not in user_states:
        # Start new quiz
        questions = Question.query.all()
        if not questions:
            msg.body("No questions available")
            return str(resp)
        print(f"Questions retrieved: {questions}")  # Debug

        user_states[sender] = {
            'current_question': 0,
            'questions': questions,
            'score': 0
        }

        # Send first question
        current_q = questions[0]
        question_text = format_question(current_q)
        msg.body(question_text)
    else:
        current_state = user_states[sender]
        current_q = current_state['questions'][current_state['current_question']]
        
        if check_answer(current_q, incoming_msg):
            current_state['score'] += 1
            msg.body(f"Correct! {current_q.feedback}\n\nNext Question:\n\n")  # Added separator
        else:
            msg.body(f"Wrong. The correct answer was: {current_q.correct_answer}\n{current_q.feedback}\n\nNext Question:\n\n")  # Added separator
            
        # Move to next question
        current_state['current_question'] += 1
        print(f"Current question index: {current_state['current_question']}")  # Debug

        if current_state['current_question'] >= len(current_state['questions']):
            final_score = current_state['score']
            del user_states[sender]
            msg.body(f"Quiz completed! Your score: {final_score}/{len(current_state['questions'])}")
        else:
            next_q = current_state['questions'][current_state['current_question']]
            print(f"Next question: {format_question(next_q)}")  # Debug
            msg.body(format_question(next_q))

            
    return str(resp)

def format_question(question):
    if question.question_type == "multiple_choice":
        options = question.options.split(",")
        options_text = "\n".join([f"{i+1}. {opt.strip()}" for i, opt in enumerate(options)])
        return f"{question.question_text}\n\n{options_text}"
    else:
        return question.question_text

def check_answer(question, user_answer):
    if question.question_type == "multiple_choice":
        try:
            options = question.options.split(",")
            if user_answer.isdigit():
                selected_index = int(user_answer) - 1
                if 0 <= selected_index < len(options):
                    selected_answer = options[selected_index].strip()
                    return selected_answer.lower() == question.correct_answer.lower()
            return user_answer.lower() == question.correct_answer.lower()   
        except (ValueError, IndexError):
            return False
        
    elif question.question_type == "true_false":
        return user_answer.lower() == question.correct_answer.lower()
    
    else:  # fill_in_the_blank
        return user_answer.lower() == question.correct_answer.lower()

def send_whatsapp_message(to_number, message):
    try:
        client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            body=message,
            to=f'whatsapp:{to_number}'
        )
        return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

if __name__ == "__main__":
    app.run(debug=True)
