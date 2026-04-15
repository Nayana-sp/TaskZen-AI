import re
import os
from transformers import pipeline
from huggingface_hub import login

try:
    import spacy
except ImportError:
    spacy = None

try:
    from transformers import pipeline
except ImportError:
    pipeline = None

try:
    import dateparser
    from dateparser.search import search_dates
except ImportError:
    dateparser = None
    search_dates = None


nlp = None
intent_classifier = None


def get_nlp_models():
    global nlp, intent_classifier

    # Load SpaCy
    if not nlp:
        try:
            print("Loading SpaCy NLP Engine...")
            nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print("Error loading SpaCy:", e)
            nlp = None

    # Load HuggingFace model
    if not intent_classifier:
        try:
            if pipeline is None:
                print("Transformers not installed")
                intent_classifier = None
            else:
                print("Loading HuggingFace Intent Pipeline...")


                token = os.getenv("HF_TOKEN")

                if token:
                    login(token=token)

                intent_classifier = pipeline(
                    "zero-shot-classification",
                    model="valhalla/distilbart-mnli-12-3",
                    device=-1
            )

                print("AI Models Loaded Successfully.")

        except Exception as e:
            print("Error loading model:", e)
            intent_classifier = None

    return nlp, intent_classifier

def extract_datetime(text: str):
    try:
        if search_dates is None:
            res = None
        else:
            res = search_dates(
                text,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'STRICT_PARSING': False
                }
            )
    except Exception:
        res = None

    # Filter noise
    if res:
        res = [
            match for match in res
            if len(match[0].strip()) > 2 and
            match[0].lower().strip() not in ['for', 'the', 'and', 'any', 'day', 'now', 'this']
        ]
        if not res:
            res = None

    date_str, time_str, reminder_time = None, None, None

    if res:
        parsed_dt = res[0][1]
        date_str = parsed_dt.strftime("%Y-%m-%d")

    # ✅ Extract time FIRST
    time_match = re.search(
        r'\b((1[0-2]|0?[1-9])(:[0-5][0-9])?\s*([AaPp]\.?[Mm]\.?))',
        text,
        re.IGNORECASE
    )

    if time_match and dateparser is not None:
        t_parsed = dateparser.parse(time_match.group(1))
        if t_parsed:
            time_str = t_parsed.strftime("%I:%M %p")

    # ✅ THEN assign reminder_time correctly
    if res:
        parsed_dt = res[0][1]

        if time_str:
            reminder_time = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            reminder_time = parsed_dt.strftime("%Y-%m-%d 00:00:00")

    return date_str, time_str, reminder_time

def detect_priority(text: str):
    text = text.lower()
    if any(word in text for word in ["exam", "urgent", "asap", "deadline", "important", "must"]):
        return "High"
    if any(word in text for word in ["read", "buy", "watch", "maybe"]):
        return "Low"
    return "Medium"

def detect_intent(text: str, date_str: str, time_str: str, local_classifier=None, local_nlp=None):
    text_l = text.lower()
    
    # 1. Explicit explicit exact word matching
    if re.search(r'\b(delete|remove|cancel|drop)\b', text_l):
        return "delete_task", 0.95
    if re.search(r'\b(complete|completed|done|finished|mark)\b', text_l):
        return "complete_task", 0.95
    if re.search(r'\b(schedule|remind|add|create|have|new)\b', text_l):
        return "add_task", 0.95

    # 2. Temporal Heuristics: If there's a scheduled time/date, it's almost always a Create!
    if date_str or time_str:
        return "add_task", 0.90
        
    # 3. SpaCy Linguistic Tense Analysis
    if local_nlp and local_nlp != "Failed":
        doc = local_nlp(text)
        has_past_tense = any(token.tag_ in ['VBD', 'VBN'] for token in doc)
        has_future_tense = any(token.tag_ == 'MD' and token.text.lower() in ['will', 'shall'] for token in doc)
        
        if has_past_tense and not has_future_tense:
            return "complete_task", 0.85
        if has_future_tense:
            return "add_task", 0.85

    # 4. Neural Intent Matcher bounds
    if local_classifier is None:
        return "add_task", 0.0
        
    labels = ["add a new task or remind me", "delete or remove a task", "mark task as complete or done"]
    res = local_classifier(text, labels)
    top_label = res['labels'][0]
    score = res['scores'][0]
    
    if top_label == "delete or remove a task": return "delete_task", score
    if top_label == "mark task as complete or done": return "complete_task", score
    return "add_task", score

def parse_voice_command(text: str):
    if not text or not text.strip():
        return {"error": "Empty input"}

    local_nlp, local_intent = get_nlp_models()
    
    date_str, time_str, reminder_time = extract_datetime(text)
    intent, score = detect_intent(text, date_str, time_str, local_intent, local_nlp)
    priority = detect_priority(text)
    
    # ----------------------------------
    # Advanced NLP Entity extraction
    # ----------------------------------
    task_name = text.strip()
    
    # 1. Clean prefixes representing intent
    intent_prefixes = [
        "schedule a meeting", "schedule meeting", "schedule an", "schedule a", "schedule",
        "remind me to", "remind me", "set a reminder for", "set a reminder", "set reminder",
        "i have an", "i have a", "i have", "i need to", "i need",
        "add", "create", "delete", "remove", "cancel", "drop",
        "mark", "complete", "completed", "finish", "finished"
    ]
    intent_prefixes.sort(key=len, reverse=True)

    for prefix in intent_prefixes:
        if task_name.lower().startswith(prefix):
            task_name = task_name[len(prefix):].strip()
            break
            
    # 2. Remove detected date phrases
    try:
        res = search_dates(text, settings={'PREFER_DATES_FROM': 'future', 'STRICT_PARSING': False})
    except Exception:
        res = None

    if res:
        for match in res:
            date_str_exact = match[0]
            if len(date_str_exact) > 2:
                pattern = re.compile(r'\b' + re.escape(date_str_exact) + r'\b', re.IGNORECASE)
                task_name = pattern.sub('', task_name).strip()

    # 3. Clean stop words iteratively
    prev_task = ""
    while prev_task != task_name:
        prev_task = task_name

        task_name = re.sub(
            r'^(a |an |the |to |for |about |my |some )',
            '',
            task_name,
            flags=re.IGNORECASE
        ).strip()

        task_name = re.sub(
            r'\s+(at|on|for|in|to|as complete|as done|to my list|tomorrow|today|tonight|in the evening|in the morning|in the afternoon)$',
            '',
            task_name,
            flags=re.IGNORECASE
        ).strip()

    # 4. Remove punctuation issues
    task_name = task_name.strip(" .,!?:;")

    if not task_name:
        task_name = "Task"
    else:
        task_name = task_name.capitalize()

    # ----------------------------------
    # Conversational Formatting
    # ----------------------------------
    if intent == "add_task":
        if date_str and time_str:
            sentence = f"{task_name} scheduled for {date_str} at {time_str}."
        elif date_str:
            sentence = f"{task_name} scheduled for {date_str}."
        else:
            sentence = f"{task_name} properly scheduled without a set time."
    elif intent == "delete_task":
        sentence = f"Deleted task: {task_name}."
    else:
        sentence = f"Marked task {task_name} as complete."
        
    needs_confirmation = score < 0.65
    
    return {
        "intent": intent,
        "task_name": task_name,
        "date": date_str,
        "time": time_str,
        "reminder_time": reminder_time,
        "priority": priority,
        "confidence": score,
        "needs_confirmation": needs_confirmation,
        "sentence": sentence,
        "original_text": text
    }