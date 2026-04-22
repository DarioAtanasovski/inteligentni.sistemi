from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import re

app = Flask(__name__)
CORS(app)


def logic_for_quiz(text):
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 30]
    quiz = []
    # Ги вадиме сите зборови од целиот текст за да генерираме погрешни опции
    all_words = list(set(re.findall(r'\w+', text.lower())))

    for sentence in sentences:
        words = sentence.split()
        if len(words) < 5:
            continue

        # ПРВО: Проверка за тип "Раскажување" (Essay)
        if (" е " in sentence or " претставува " in sentence) and random.random() > 0.6:
            parts = re.split(r' е | претставува ', sentence, maxsplit=1, flags=re.IGNORECASE)
            subjekt = parts[0].strip()
            definicija = parts[1].strip()
            keywords = [w.lower().strip(",.?!") for w in definicija.split() if len(w) > 4]

            if keywords:
                quiz.append({
                    "question": f"Раскажи поопширно: Што знаеш за {subjekt}?",
                    "correct_answer": definicija,
                    "keywords": keywords,
                    "type": "essay",
                    "explanation": f"Важни концепти: {', '.join(keywords)}"
                })
                continue

        # ВТОРО: Прашања со пополнување и избор (сега променливите се достапни)
        valid_indices = [i for i, w in enumerate(words) if len(w.strip(",.?!")) > 3]
        if not valid_indices:
            continue

        # Шанса за Multiple Choice (Checkbox)
        if len(valid_indices) >= 4 and random.random() > 0.7:
            target_indices = random.sample(valid_indices, 2)
            correct_list = [words[i].strip(",.?!") for i in sorted(target_indices)]

            display_words = list(words)
            for idx in target_indices:
                display_words[idx] = "_______"

            wrong = random.sample([w for w in all_words if w not in [a.lower() for a in correct_list]],
                                  min(len(all_words) - 2, 2))
            options = correct_list + wrong
            random.shuffle(options)

            quiz.append({
                "question": " ".join(display_words) + " (Избери ги двата збора)",
                "correct_answer": correct_list,
                "options": options,
                "type": "multiple_choice"
            })
            continue

        # Стандардно: Еден збор фали (Choice или Input)
        target_index = random.choice(valid_indices)
        correct_answer = words[target_index].strip(",.?!")

        display_words = list(words)
        display_words[target_index] = "_______"

        q_type = random.choice(['choice', 'input'])
        options = []
        if q_type == 'choice':
            wrong = random.sample([w for w in all_words if w != correct_answer.lower()], min(len(all_words) - 1, 3))
            options = wrong + [correct_answer]
            random.shuffle(options)

        quiz.append({
            "question": " ".join(display_words) + ".",
            "correct_answer": correct_answer,
            "options": options,
            "type": q_type
        })

    return quiz


@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.json
        text = data.get('text', '')
        if not text: return jsonify({"error": "Внеси текст"}), 400
        questions = logic_for_quiz(text)
        return jsonify({"quiz": questions})
    except Exception as e:
        print(f"Грешка: {e}")  # Ова ќе ти покаже во PyCharm што точно не чини
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)