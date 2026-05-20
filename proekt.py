from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import re

app = Flask(__name__)
CORS(app)


CATEGORY_LABELS = {
    "likovi": "Ликови",
    "nastani": "Настани",
    "pricini_posledici": "Причини и последици",
    "zaklucoci": "Заклучоци"
}

CATEGORY_KEYWORDS = {
    "pricini_posledici": [
        "затоа што", "бидејќи", "поради", "причина", "последица",
        "затоа", "доведува", "резултат", "зошто"
    ],
    "zaklucoci": [
        "заклучок", "порака", "значи", "покажува", "учиме",
        "сфаќаме", "важно", "идеја", "тема", "поента"
    ],
    "nastani": [
        "се случува", "се случило", "оди", "заминува", "доаѓа",
        "пристигнува", "се враќа", "живее", "работи", "почнува",
        "тргнува", "останува", "сретнува"
    ],
    "likovi": [
        "лик", "ликови", "јунак", "јунаци", "мајка", "татко",
        "девојка", "девојче", "момче", "човек", "жена", "дете"
    ]
}

# Овие зборови се користат само за fallback flashcards.
# Целта е картичките да работат и кога текстот не е на македонски.
UNIVERSAL_STOPWORDS = {
    # Macedonian
    "кој", "која", "кое", "што", "дека", "како", "кога", "каде", "зошто",
    "бидејќи", "затоа", "ова", "тоа", "овој", "таа", "тие", "има", "нема",
    "еден", "една", "едно", "многу", "малку", "може", "треба", "беше", "биле",
    # English
    "the", "and", "that", "this", "with", "from", "there", "their", "which",
    "when", "where", "because", "about", "into", "after", "before", "also",
    "have", "has", "were", "been", "being", "what", "should", "would", "could",
    # Serbian/Croatian/Bosnian latin
    "koji", "koja", "koje", "kada", "gdje", "gde", "zbog", "zato", "ovaj",
    "ova", "ovo", "bilo", "bila", "bili", "treba", "može", "moze",
    # Albanian
    "dhe", "është", "eshte", "janë", "jane", "kjo", "këtë", "kete", "sepse",
    "për", "per", "nga", "kur", "ku", "çfarë", "cfare"
}

DEFINITION_PATTERNS = [
    # Macedonian / Serbian / Croatian / Bosnian
    r'\s+е\s+',
    r'\s+je\s+',
    r'\s+su\s+',
    r'\s+претставува\s+',
    r'\s+predstavlja\s+',
    r'\s+значи\s+',
    r'\s+znači\s+',
    r'\s+znaci\s+',

    # English
    r'\s+is\s+',
    r'\s+are\s+',
    r'\s+means\s+',
    r'\s+refers\s+to\s+',
    r'\s+is\s+defined\s+as\s+',

    # Albanian
    r'\s+është\s+',
    r'\s+eshte\s+',
    r'\s+janë\s+',
    r'\s+jane\s+',
    r'\s+do\s+të\s+thotë\s+',
    r'\s+do\s+te\s+thote\s+',

    # German / Spanish / French / Italian basic connectors
    r'\s+ist\s+',
    r'\s+sind\s+',
    r'\s+es\s+',
    r'\s+son\s+',
    r'\s+significa\s+',
    r'\s+est\s+',
    r'\s+sont\s+',
    r'\s+è\s+',
    r'\s+sono\s+'
]


def split_sentences(text):
    parts = re.split(r'(?<=[.!?])\s+|\n+', text)
    sentences = []

    for part in parts:
        clean = part.strip(" .!?")
        if len(clean) > 20:
            sentences.append(clean)

    return sentences


def extract_words(text):
    return list(set(re.findall(r'\w+', text.lower(), flags=re.UNICODE)))


def extract_keywords(text):
    words = re.findall(r'\w+', text.lower(), flags=re.UNICODE)
    return [w.strip(",.?!") for w in words if len(w.strip(",.?!")) > 4]


def safe_sample(candidates, count):
    if not candidates:
        return []
    return random.sample(candidates, min(len(candidates), count))


def detect_category(sentence):
    s = sentence.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in s:
                return category

    words = re.findall(r'\w+', sentence, flags=re.UNICODE)

    for word in words[1:]:
        if len(word) > 3 and word[0].isupper():
            return "likovi"

    return "nastani"


def build_question(sentence, all_words, category):
    words = sentence.split()

    if len(words) < 5:
        return None

    lower_sentence = sentence.lower()

    if category == "pricini_posledici":
        reason_markers = ["затоа што", "бидејќи", "поради"]

        for marker in reason_markers:
            if marker in lower_sentence:
                parts = re.split(marker, sentence, maxsplit=1, flags=re.IGNORECASE)

                if len(parts) == 2:
                    first_part = parts[0].strip()
                    reason_part = parts[1].strip()
                    keywords = extract_keywords(reason_part)

                    if keywords:
                        return {
                            "question": f"Објасни зошто: {first_part}?",
                            "correct_answer": reason_part,
                            "keywords": keywords,
                            "type": "essay",
                            "category": category,
                            "source_sentence": sentence,
                            "explanation": f"Важни поими: {', '.join(keywords)}"
                        }

    if (" е " in sentence or " претставува " in sentence) and random.random() > 0.5:
        parts = re.split(r'\s+е\s+|\s+претставува\s+', sentence, maxsplit=1, flags=re.IGNORECASE)

        if len(parts) == 2:
            subject = parts[0].strip()
            definition = parts[1].strip()
            keywords = extract_keywords(definition)

            if keywords:
                return {
                    "question": f"Раскажи поопширно: Што знаеш за {subject}?",
                    "correct_answer": definition,
                    "keywords": keywords,
                    "type": "essay",
                    "category": category,
                    "source_sentence": sentence,
                    "explanation": f"Важни поими: {', '.join(keywords)}"
                }

    valid_indices = [
        i for i, w in enumerate(words)
        if len(w.strip(",.?!")) > 3
    ]

    if not valid_indices:
        return None

    if len(valid_indices) >= 4 and random.random() > 0.7:
        target_indices = random.sample(valid_indices, 2)
        correct_list = [words[i].strip(",.?!") for i in sorted(target_indices)]

        display_words = list(words)

        for idx in target_indices:
            display_words[idx] = "_______"

        wrong_candidates = [
            w for w in all_words
            if w not in [a.lower() for a in correct_list]
        ]

        wrong = safe_sample(wrong_candidates, 2)
        options = correct_list + wrong
        random.shuffle(options)

        return {
            "question": " ".join(display_words) + " (Избери ги двата збора)",
            "correct_answer": correct_list,
            "options": options,
            "type": "multiple_choice",
            "category": category,
            "source_sentence": sentence
        }

    target_index = random.choice(valid_indices)
    correct_answer = words[target_index].strip(",.?!")

    display_words = list(words)
    display_words[target_index] = "_______"

    q_type = random.choice(["choice", "input"])
    options = []

    if q_type == "choice":
        wrong_candidates = [
            w for w in all_words
            if w != correct_answer.lower()
        ]

        wrong = safe_sample(wrong_candidates, 3)
        options = wrong + [correct_answer]
        random.shuffle(options)

    return {
        "question": " ".join(display_words) + ".",
        "correct_answer": correct_answer,
        "options": options,
        "type": q_type,
        "category": category,
        "source_sentence": sentence
    }


def logic_for_quiz(text, focus_categories=None):
    sentences = split_sentences(text)
    all_words = extract_words(text)
    quiz = []

    for sentence in sentences:
        category = detect_category(sentence)

        if focus_categories and category not in focus_categories:
            continue

        question = build_question(sentence, all_words, category)

        if question:
            quiz.append(question)

    random.shuffle(quiz)

    if focus_categories:
        return quiz[:6]

    return quiz[:12]


def split_by_definition_connector(sentence):
    for pattern in DEFINITION_PATTERNS:
        parts = re.split(pattern, sentence, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            subject = parts[0].strip(" ,.!?:;\"'()[]{}")
            definition = parts[1].strip(" ,.!?:;\"'()[]{}")

            if 1 < len(subject) <= 70 and len(definition) > 8:
                return subject, definition

    return None, None


def pick_key_word(sentence):
    words = re.findall(r'\w+', sentence, flags=re.UNICODE)

    candidates = []
    for index, word in enumerate(words):
        clean = word.strip(" ,.!?:;\"'()[]{}").lower()

        if len(clean) < 5:
            continue

        if clean in UNIVERSAL_STOPWORDS:
            continue

        score = len(clean)

        if index > 0 and word[0].isupper():
            score += 8

        if len(clean) >= 8:
            score += 3

        candidates.append((score, word))

    if not candidates:
        return None

    candidates.sort(reverse=True, key=lambda item: item[0])
    return candidates[0][1]


def make_cloze_flashcard(sentence):
    key_word = pick_key_word(sentence)

    if not key_word:
        return {
            "front": "Што треба да запомниш од оваа реченица?",
            "back": sentence,
            "source_sentence": sentence
        }

    front = re.sub(re.escape(key_word), "_______", sentence, count=1)

    return {
        "front": front,
        "back": f"Одговор: {key_word}\n\nЦела реченица: {sentence}",
        "source_sentence": sentence
    }


def logic_for_flashcards(text):
    sentences = split_sentences(text)
    flashcards = []

    for sentence in sentences:
        subject, definition = split_by_definition_connector(sentence)

        if subject and definition:
            flashcards.append({
                "front": f"Што знаеш за {subject}?",
                "back": definition,
                "source_sentence": sentence
            })
        else:
            flashcards.append(make_cloze_flashcard(sentence))

    random.shuffle(flashcards)
    return flashcards[:12]


@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '').strip()
        weak_categories = data.get('weak_categories', None)

        if not text:
            return jsonify({"error": "Внеси текст"}), 400

        questions = logic_for_quiz(text, weak_categories)

        if weak_categories and len(questions) == 0:
            questions = logic_for_quiz(text, None)

        return jsonify({
            "quiz": questions,
            "categories": CATEGORY_LABELS
        })

    except Exception as e:
        print(f"Грешка: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/generate-flashcards', methods=['POST'])
def generate_flashcards():
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '').strip()

        if not text:
            return jsonify({"error": "Внеси текст"}), 400

        flashcards = logic_for_flashcards(text)

        return jsonify({
            "flashcards": flashcards
        })

    except Exception as e:
        print(f"Грешка: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "SmartQuiz Pro API работи успешно."
    })


if __name__ == '__main__':
    app.run(debug=True)
