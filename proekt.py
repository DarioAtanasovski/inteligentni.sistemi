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
        "затоа", "доведува", "доведе", "резултат", "како резултат", "зошто"
    ],
    "zaklucoci": [
        "заклучок", "порака", "значи", "покажува", "учиме",
        "сфаќаме", "важно", "идеја", "тема", "поента", "може да се заклучи"
    ],
    "nastani": [
        "се случува", "се случило", "оди", "заминува", "доаѓа",
        "пристигнува", "се враќа", "живее", "работи", "почнува",
        "тргнува", "останува", "сретнува", "настан", "потоа", "на крај"
    ],
    "likovi": [
        "лик", "ликови", "јунак", "јунаци", "мајка", "татко",
        "девојка", "девојче", "момче", "човек", "жена", "дете", "карактер"
    ]
}

# Зборови што не треба да се избираат како точен одговор.
# Ова е главната разлика од претходната верзија: веќе не се бираат случајни небитни зборови.
STOPWORDS = {
    "и", "во", "на", "со", "за", "од", "до", "кон", "над", "под", "пред", "зад", "при", "без",
    "се", "си", "сум", "сме", "сте", "бев", "беше", "беа", "биле", "бил", "била", "има", "имаат",
    "нема", "не", "да", "ќе", "ги", "го", "ја", "му", "им", "ми", "ни", "ви", "ме", "те",
    "кој", "која", "кое", "кои", "што", "дека", "како", "кога", "каде", "зошто", "колку",
    "ова", "тоа", "овој", "овие", "таа", "тие", "тој", "така", "тука", "таму", "потоа",
    "еден", "една", "едно", "многу", "малку", "повеќе", "помалку", "може", "треба", "мора",
    "затоа", "бидејќи", "поради", "преку", "меѓу", "сите", "секој", "некој", "нешто",
    "the", "and", "that", "this", "with", "from", "there", "their", "which", "when", "where",
    "because", "about", "into", "after", "before", "also", "have", "has", "were", "been", "being",
    "what", "should", "would", "could", "are", "was", "is", "of", "to", "in", "a", "an",
    "koji", "koja", "koje", "kada", "gdje", "gde", "zbog", "zato", "ovaj", "ova", "ovo", "bilo",
    "bila", "bili", "treba", "može", "moze", "je", "su", "sam", "smo", "ste",
    "dhe", "është", "eshte", "janë", "jane", "kjo", "këtë", "kete", "sepse", "për", "per", "nga", "kur", "ku"
}

# Дополнителни зборови што се граматички корисни, но не се добри како точен одговор во квиз.
STOPWORDS.update({
    "претставува", "нарекува", "дефинира", "значи", "создава", "помага", "јавува",
    "реагира", "реагираат", "доведува", "доведе", "контролира", "следи", "опишува",
    "покажува", "можеме", "треба", "важно", "главни", "главен", "главна"
})

DEFINITION_PATTERNS = [
    r"\s+се\s+нарекува\s+",
    r"\s+се\s+дефинира\s+како\s+",
    r"\s+претставува\s+",
    r"\s+значи\s+",
    r"\s+е\s+",
    r"\s+is\s+defined\s+as\s+",
    r"\s+refers\s+to\s+",
    r"\s+means\s+",
    r"\s+is\s+",
    r"\s+are\s+",
    r"\s+je\s+",
    r"\s+su\s+",
    r"\s+predstavlja\s+",
    r"\s+znači\s+",
    r"\s+znaci\s+",
    r"\s+është\s+",
    r"\s+eshte\s+",
    r"\s+janë\s+",
    r"\s+jane\s+"
]

REASON_MARKERS = [
    "затоа што", "бидејќи", "поради", "како резултат на", "од причина што", "because", "due to"
]

TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЃѓЌќЅѕЉљЊњЏџШшЖжЧчЋћČčĆćŽžŠšĐđ0-9%]+", re.UNICODE)


def split_sentences(text):
    text = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    sentences = []

    for part in parts:
        clean = part.strip(" .!?;:•-–—\t")
        word_count = len(TOKEN_RE.findall(clean))
        if len(clean) >= 30 and word_count >= 5:
            sentences.append(clean)

    return sentences


def normalize_word(word):
    return word.strip(" ,.!?:;\"'“”„()[]{}\n\t").lower()


def tokenize(text):
    return TOKEN_RE.findall(text)


def is_good_keyword(word):
    clean = normalize_word(word)

    if not clean:
        return False

    if clean in STOPWORDS:
        return False

    if len(clean) < 4:
        return False

    # Не избирај чисти броеви како одговор, освен ако се дел од важен процент/ознака.
    if clean.isdigit():
        return False

    # Не избирај зборови што се само граматички додатоци.
    weak_suffixes = ("њето", "њето", "ата", "ите", "иот")
    if len(clean) <= 5 and clean.endswith(weak_suffixes):
        return False

    return True


def word_frequencies(text):
    freq = {}
    for word in tokenize(text):
        clean = normalize_word(word)
        if is_good_keyword(clean):
            freq[clean] = freq.get(clean, 0) + 1
    return freq


def extract_keywords(text, max_count=6):
    scored = rank_keywords(text, {})
    result = []
    seen = set()

    for item in scored:
        clean = normalize_word(item["word"])
        if clean not in seen:
            seen.add(clean)
            result.append(clean)
        if len(result) >= max_count:
            break

    return result


def rank_keywords(sentence, global_freq=None):
    global_freq = global_freq or {}
    words = tokenize(sentence)
    candidates = []
    seen = set()

    for index, word in enumerate(words):
        clean = normalize_word(word)

        if not is_good_keyword(clean):
            continue

        if clean in seen:
            continue

        seen.add(clean)
        score = 0

        # Подолги зборови почесто се носители на значење.
        score += min(len(clean), 12)

        # Збор што се повторува низ текстот е веројатно важен поим.
        score += min(global_freq.get(clean, 0), 4) * 2

        # Имиња / називи често почнуваат со голема буква, но не го форсираме првиот збор во реченица.
        if index > 0 and word[:1].isupper():
            score += 8

        # Научни / апстрактни поими често имаат вакви наставки.
        important_endings = (
            "ција", "ство", "изам", "ност", "терапија", "логика", "систем", "процес",
            "болест", "симптом", "причина", "последица", "заклучок", "карактер"
        )
        if clean.endswith(important_endings):
            score += 5

        # Не го бирај првиот збор само затоа што е прв.
        if index == 0:
            score -= 2

        candidates.append({
            "word": word.strip(" ,.!?:;\"'“”„()[]{}"),
            "clean": clean,
            "score": score
        })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates


def safe_sample(candidates, count):
    unique = []
    seen = set()
    for candidate in candidates:
        clean = normalize_word(candidate)
        if clean and clean not in seen:
            seen.add(clean)
            unique.append(candidate)

    if not unique:
        return []

    return random.sample(unique, min(len(unique), count))



def sentence_contains_keyword(sentence_lower, keyword):
    keyword = keyword.lower().strip()
    if " " in keyword:
        return keyword in sentence_lower
    pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
    return re.search(pattern, sentence_lower, flags=re.UNICODE) is not None

def detect_category(sentence):
    s = sentence.lower()

    if "затоа што" in s or "бидејќи" in s or "поради" in s:
        return "pricini_posledici"

    if "затоа е важно" in s or "може да се заклучи" in s or "заклучок" in s or "порака" in s:
        return "zaklucoci"

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(sentence_contains_keyword(s, keyword) for keyword in keywords):
            return category

    # Ако има име во средина на реченица, често станува збор за лик.
    words = tokenize(sentence)
    for index, word in enumerate(words):
        if index > 0 and word[:1].isupper() and len(word) > 2:
            return "likovi"

    return "nastani"


def split_by_definition_connector(sentence):
    for pattern in DEFINITION_PATTERNS:
        parts = re.split(pattern, sentence, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            subject = parts[0].strip(" ,.!?:;\"'“”„()[]{}")
            definition = parts[1].strip(" ,.!?:;\"'“”„()[]{}")

            # Ако предметот е предолг, прашањето звучи лошо.
            subject_words = [normalize_word(w) for w in tokenize(subject)]

            if 2 <= len(subject) <= 80 and len(definition) >= 12:
                # Избегнувај лажни дефиниции од типот „Затоа е важно...“.
                if not subject_words or subject_words[0] in STOPWORDS:
                    continue

                # Избегнувај дефиниции каде предметот е цела сложена реченица.
                if len(subject_words) <= 8:
                    return subject, definition

    return None, None


def split_by_reason_marker(sentence):
    lower = sentence.lower()

    for marker in REASON_MARKERS:
        if marker in lower:
            parts = re.split(re.escape(marker), sentence, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                first_part = parts[0].strip(" ,.!?:;\"'“”„()[]{}")
                reason_part = parts[1].strip(" ,.!?:;\"'“”„()[]{}")
                if len(first_part) > 8 and len(reason_part) > 8:
                    return first_part, reason_part

    return None, None


def make_blank_sentence(sentence, target):
    pattern = r"(?<!\w)" + re.escape(target) + r"(?!\w)"
    blanked = re.sub(pattern, "_______", sentence, count=1, flags=re.IGNORECASE)

    if blanked == sentence:
        blanked = sentence.replace(target, "_______", 1)

    return blanked


def get_wrong_options(all_terms, correct_terms, count=3):
    correct_clean = {normalize_word(term) for term in correct_terms}
    candidates = [
        term for term in all_terms
        if normalize_word(term) not in correct_clean and is_good_keyword(term)
    ]
    return safe_sample(candidates, count)


def build_essay_question(sentence, category):
    first_part, reason_part = split_by_reason_marker(sentence)
    if first_part and reason_part:
        keywords = extract_keywords(reason_part, max_count=5)
        if keywords:
            return {
                "question": f"Објасни зошто се случува ова: {first_part}.",
                "correct_answer": reason_part,
                "keywords": keywords,
                "type": "essay",
                "category": "pricini_posledici",
                "source_sentence": sentence,
                "explanation": f"Во одговорот треба да се спомнат: {', '.join(keywords)}"
            }

    subject, definition = split_by_definition_connector(sentence)
    if subject and definition:
        keywords = extract_keywords(definition, max_count=5)
        if keywords:
            return {
                "question": f"Објасни со свои зборови: што претставува {subject}?",
                "correct_answer": definition,
                "keywords": keywords,
                "type": "essay",
                "category": category,
                "source_sentence": sentence,
                "explanation": f"Во одговорот треба да се спомнат: {', '.join(keywords)}"
            }

    if category == "zaklucoci":
        keywords = extract_keywords(sentence, max_count=5)
        if keywords:
            return {
                "question": "Која е главната порака или заклучок од оваа реченица?",
                "correct_answer": sentence,
                "keywords": keywords,
                "type": "essay",
                "category": category,
                "source_sentence": sentence,
                "explanation": f"Клучни поими: {', '.join(keywords)}"
            }

    return None


def build_choice_question(sentence, all_terms, category, global_freq):
    ranked = rank_keywords(sentence, global_freq)
    if not ranked:
        return None

    target = ranked[0]["word"]
    wrong = get_wrong_options(all_terms, [target], 3)

    if len(wrong) < 2:
        return None

    options = wrong + [target]
    random.shuffle(options)

    return {
        "question": f"Кој поим недостига во реченицата: „{make_blank_sentence(sentence, target)}“?",
        "correct_answer": target,
        "options": options,
        "type": "choice",
        "category": category,
        "source_sentence": sentence
    }


def build_input_question(sentence, category, global_freq):
    ranked = rank_keywords(sentence, global_freq)
    if not ranked:
        return None

    # За input земаме важен поим, но ако може различен од најпрвиот, за да не се повторува со choice.
    target_item = ranked[1] if len(ranked) > 1 else ranked[0]
    target = target_item["word"]

    return {
        "question": f"Пополни го поимот што недостига: „{make_blank_sentence(sentence, target)}“.",
        "correct_answer": target,
        "options": [],
        "type": "input",
        "category": category,
        "source_sentence": sentence
    }


def build_multiple_choice_question(sentence, all_terms, category, global_freq):
    ranked = rank_keywords(sentence, global_freq)

    if len(ranked) < 2:
        return None

    targets = [ranked[0]["word"], ranked[1]["word"]]
    wrong = get_wrong_options(all_terms, targets, 3)

    if len(wrong) < 2:
        return None

    blanked = sentence
    for target in targets:
        blanked = make_blank_sentence(blanked, target)

    options = targets + wrong[:3]
    random.shuffle(options)

    return {
        "question": f"Во реченицата недостигаат два важни поими: „{blanked}“ (избери ги двата точни).",
        "correct_answer": targets,
        "options": options,
        "type": "multiple_choice",
        "category": category,
        "source_sentence": sentence
    }


def build_questions_for_sentence(sentence, all_terms, global_freq):
    category = detect_category(sentence)
    questions = []

    essay = build_essay_question(sentence, category)
    if essay:
        questions.append(essay)

    choice = build_choice_question(sentence, all_terms, category, global_freq)
    if choice:
        questions.append(choice)

    input_q = build_input_question(sentence, category, global_freq)
    if input_q:
        questions.append(input_q)

    multiple = build_multiple_choice_question(sentence, all_terms, category, global_freq)
    if multiple:
        questions.append(multiple)

    return questions


def select_balanced_questions(candidates, limit):
    random.shuffle(candidates)

    # Прво пробуваме да има разновидност, наместо сите да бидат ист тип.
    desired_order = ["essay", "choice", "input", "multiple_choice"]
    selected = []
    used_keys = set()
    per_sentence_count = {}

    def add_question(q, relaxed=False):
        sentence_key = q.get("source_sentence", "")[:90]
        unique_key = (sentence_key, q.get("type"), q.get("question"))

        if unique_key in used_keys:
            return False

        if not relaxed and per_sentence_count.get(sentence_key, 0) >= 1:
            return False

        selected.append(q)
        used_keys.add(unique_key)
        per_sentence_count[sentence_key] = per_sentence_count.get(sentence_key, 0) + 1
        return True

    while len(selected) < limit:
        before = len(selected)

        for q_type in desired_order:
            for q in candidates:
                if q.get("type") == q_type and add_question(q):
                    break

            if len(selected) >= limit:
                break

        if len(selected) == before:
            break

    # Ако текстот е краток, дозволуваме второ прашање од иста реченица.
    if len(selected) < limit:
        for q in candidates:
            add_question(q, relaxed=True)
            if len(selected) >= limit:
                break

    random.shuffle(selected)
    return selected[:limit]


def logic_for_quiz(text, focus_categories=None):
    sentences = split_sentences(text)
    global_freq = word_frequencies(text)

    all_terms_ranked = rank_keywords(text, global_freq)
    all_terms = [item["word"] for item in all_terms_ranked]

    candidates = []
    for sentence in sentences:
        sentence_questions = build_questions_for_sentence(sentence, all_terms, global_freq)

        for question in sentence_questions:
            if focus_categories and question.get("category") not in focus_categories:
                continue
            candidates.append(question)

    limit = 6 if focus_categories else 12
    return select_balanced_questions(candidates, limit)


def pick_key_word(sentence):
    ranked = rank_keywords(sentence, {})
    if not ranked:
        return None
    return ranked[0]["word"]


def make_cloze_flashcard(sentence):
    key_word = pick_key_word(sentence)

    if not key_word:
        return {
            "front": "Што треба да запомниш од оваа реченица?",
            "back": sentence,
            "source_sentence": sentence
        }

    front = make_blank_sentence(sentence, key_word)

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
