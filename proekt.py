from flask import Flask, request, jsonify
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)


def logic_for_quiz(text):
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 15]
    quiz = []
    all_words = list(set(text.replace(',', '').replace('.', '').split()))

    for sentence in sentences:
        words = sentence.split()
        if len(words) < 5: continue

        valid_indices = [i for i, w in enumerate(words) if len(w.strip(",.?!")) > 3]
        if not valid_indices: continue

        target_index = random.choice(valid_indices)
        correct_answer = words[target_index].strip(",.?!")

        display_words = list(words)
        display_words[target_index] = "_______"
        question_text = " ".join(display_words) + "."

        # ОДЛУКА: Дали прашањето ќе биде со пишување или заокружување?
        # 50% шанса за секое
        q_type = random.choice(['choice', 'input'])

        options = []
        if q_type == 'choice':
            possible_wrong = [w for w in all_words if w.lower() != correct_answer.lower() and len(w) > 3]
            wrong_options = random.sample(possible_wrong, min(len(possible_wrong), 3))
            options = wrong_options + [correct_answer]
            random.shuffle(options)

        quiz.append({
            "question": question_text,
            "options": options,
            "correct_answer": correct_answer,
            "type": q_type,  # Го додаваме типот тука
            "explanation": f"Точниот збор е '{correct_answer}'."
        })

    return quiz

@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.json
        user_text = data.get('text', '')

        if not user_text:
            return jsonify({"error": "Внесете текст"}), 400

        # Ја повикуваме логиката
        questions = logic_for_quiz(user_text)

        if not questions:
            return jsonify({"error": "Текстот е прекраток за квиз"}), 400

        return jsonify({"quiz": questions})

    except Exception as e:
        print(f"ГРЕШКА: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Ова го стартува серверот на порта 5000
    app.run(debug=True, port=5000)