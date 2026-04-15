import os
import sys

# Change perfectly to Backend dir context if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nlp_engine import parse_voice_command
import time

test_cases = [
    {
        "text": "I have a meeting tomorrow at 3 PM",
        "expected_intent": "add_task",
        "expected_task": "Meeting",
        "expected_priority": "Medium"
    },
    {
        "text": "Delete the gym task",
        "expected_intent": "delete_task",
        "expected_task": "Gym task",
        "expected_priority": "Medium"
    },
    {
        "text": "Mark read book as complete",
        "expected_intent": "complete_task",
        "expected_task": "Read book",
        "expected_priority": "Low"
    },
    {
        "text": "Schedule an urgent doctor appointment for next Monday",
        "expected_intent": "add_task",
        "expected_task": "Urgent doctor appointment",
        "expected_priority": "High"
    },
    {
        "text": "Remind me to call John in the evening",
        "expected_intent": "add_task",
        "expected_task": "Call john",
        "expected_priority": "Medium"
    },
    {
        "text": "Cancel my flight booking",
        "expected_intent": "delete_task",
        "expected_task": "Flight booking",
        "expected_priority": "Medium"
    },
    {
        "text": "I need to buy groceries today",
        "expected_intent": "add_task",
        "expected_task": "Buy groceries",
        "expected_priority": "Low"  # Buy is considered low priority in current heuristic
    },
    {
        "text": "Finished the math exam",
        "expected_intent": "complete_task",
        "expected_task": "Math exam",
        "expected_priority": "High"
    },
    {
        "text": "Add finish presentation to my list",
        "expected_intent": "add_task",
        "expected_task": "Finish presentation to my list",
        "expected_priority": "Medium"
    },
    {
        "text": "Drop the database table",
        "expected_intent": "delete_task",
        "expected_task": "Database table",
        "expected_priority": "Medium"
    }
]

def evaluate():
    print("Starting NLP Evaluation...")
    passed = 0
    total = len(test_cases)
    failures = []

    for i, tc in enumerate(test_cases):
        text = tc["text"]
        print(f"[{i+1}/{total}] Testing: '{text}'")
        try:
            res = parse_voice_command(text)
            
            # Validation
            intent_match = res["intent"] == tc["expected_intent"]
            task_match = res["task_name"].lower() == tc["expected_task"].lower()
            priority_match = res["priority"] == tc["expected_priority"]
            
            if intent_match and task_match and priority_match:
                passed += 1
            else:
                failures.append({
                    "text": text,
                    "expected": tc,
                    "actual": res
                })
        except Exception as e:
            failures.append({
                "text": text,
                "expected": tc,
                "error": str(e)
            })

    accuracy = (passed / total) * 100
    
    print("\n" + "="*40)
    print("EVALUATION REPORT")
    print("="*40)
    print(f"Total Cases: {total}")
    print(f"Passed:      {passed}")
    print(f"Failed:      {total - passed}")
    print(f"Accuracy:    {accuracy:.2f}%")
    
    if failures:
        print("\nFAILURE DETAILS:")
        for idx, f in enumerate(failures):
            print("-" * 20)
            print(f"Failure #{idx+1}: '{f['text']}'")
            if "error" in f:
                print(f"  Error: {f['error']}")
            else:
                expected = f["expected"]
                actual = f["actual"]
                if actual['intent'] != expected['expected_intent']:
                    print(f"  Intent:   Expected '{expected['expected_intent']}', Got '{actual['intent']}'")
                if actual['task_name'].lower() != expected['expected_task'].lower():
                    print(f"  Task:     Expected '{expected['expected_task']}', Got '{actual['task_name']}'")
                if actual['priority'] != expected['expected_priority']:
                    print(f"  Priority: Expected '{expected['expected_priority']}', Got '{actual['priority']}'")
    print("="*40)

if __name__ == '__main__':
    evaluate()
