from flask import Flask, request, jsonify
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)


def generate_local_quiz(text):
    # Го делиме текстот на реченици
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
    quiz = []

    # Земаме најмногу 3 реченици за да направиме прашања
    selected_sentences = random.sample(sentences, min(len(sentences), 3))

    for sentence in selected_sentences:
        words = sentence.split()
        if len(words) < 4: continue

        # Избираме случаен збор што ќе биде „скриен“ (точен одговор)
        target_index = random.randint(0, len(words) - 1)
        correct_answer = words[target_index].strip(",.?!")

        # Го заменуваме зборот со празни места во прашањето
        words[target_index] = "_______"
        question_text = " ".join(words) + "?"

        # Правиме лажни одговори (случајни зборови од истиот текст)
        all_words = list(set(text.split()))
        wrong_options = random.sample([w for w in all_words if w != correct_answer], 3)

        options = wrong_options + [correct_answer]
        random.shuffle(options)  # Ги мешаме опциите

        quiz.append({
            "question": question_text,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": f"Точниот збор во оваа реченица е '{correct_answer}'."
        })

    return {"quiz": quiz}


@app.route('/generate-quiz', methods=['POST'])
def generate_local_quiz(text):
    # Го делиме текстот на реченици
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 15]
    quiz = []

    all_words = list(set(text.lower().split()))  # Листа на сите зборови за лажни одговори

    # Сега одиме низ СИТЕ реченици (без лимит од 3)
    for sentence in sentences:
        words = sentence.split()
        if len(words) < 5: continue  # Прескокни многу кратки реченици

        # Избираме случаен збор што е подолг од 3 букви (за поинтересни прашања)
        valid_indices = [i for i, w in enumerate(words) if len(w.strip(",.?!")) > 3]
        if not valid_indices: continue

        target_index = random.choice(valid_indices)
        correct_answer = words[target_index].strip(",.?!")

        # Го заменуваме зборот со празни места
        temp_words = list(words)
        temp_words[target_index] = "_______"
        question_text = " ".join(temp_words) + "."

        # Генерираме лажни одговори
        wrong_options = random.sample([w for w in all_words if w != correct_answer.lower()], min(len(all_words) - 1, 3))

        options = wrong_options + [correct_answer]
        random.shuffle(options)

        quiz.append({
            "question": question_text,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": f"Зборот што недостига е '{correct_answer}'."
        })

    return {"quiz": quiz}


if __name__ == '__main__':
    app.run(debug=True)