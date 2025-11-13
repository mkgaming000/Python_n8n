# ai_predictor.py
from flask import Flask, request, jsonify
from collections import Counter, defaultdict
import json, os

app = Flask(__name__)
DATA_FILE = "history.json"
VALID = {"stone","scissor","paper"}

def load_history():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,"r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(h):
    with open(DATA_FILE,"w") as f:
        json.dump(h, f, indent=2)

history = load_history()

@app.route("/update", methods=["POST"])
def update_choice():
    data = request.get_json(force=True)
    opened = data.get("opened")
    if not opened or opened not in VALID:
        return jsonify({"error": "invalid choice, must be one of stone|scissor|paper"}), 400
    history.append(opened)
    save_history(history)
    return jsonify({"status":"ok", "total": len(history)})

@app.route("/predict", methods=["POST"])
def predict_next():
    # Return JSON with prediction, confidence, metadata
    if len(history) < 5:
        return jsonify({
            "prediction": "stone",
            "confidence": 0.33,
            "reason": "not enough data",
            "total": len(history)
        })

    # Frequency
    freq = Counter(history)
    total = sum(freq.values())
    freq_score = {k: v/total for k,v in freq.items()}

    # 2-step Markov
    chain2 = defaultdict(list)
    for i in range(len(history)-2):
        key = (history[i], history[i+1])
        chain2[key].append(history[i+2])

    last2 = tuple(history[-2:])
    if last2 in chain2:
        nexts = Counter(chain2[last2])
        pred_item, count = nexts.most_common(1)[0]
        markov_conf = count / sum(nexts.values())
        method = "markov2"
    else:
        pred_item, markov_conf = None, 0
        method = "fallback_freq"

    # Trend / recent
    recent = history[-10:]
    recent_most = Counter(recent).most_common(1)[0][0]

    # Combine: score candidates
    choices = list(VALID)
    scores = {}
    for c in choices:
        s = freq_score.get(c, 0) * 0.4
        if c == pred_item: s += markov_conf * 0.5
        if c == recent_most: s += 0.1
        scores[c] = s

    # Normalize
    total_s = sum(scores.values()) or 1
    for k in scores: scores[k] = round(scores[k]/total_s, 3)

    prediction = max(scores, key=lambda k: scores[k])
    confidence = scores[prediction]

    return jsonify({
        "prediction": prediction,
        "confidence": confidence,
        "method": method,
        "total": len(history),
        "recent": recent,
        "freq": freq,
        "scores": scores
    })

@app.route("/clear", methods=["POST"])
def clear_history():
    history.clear()
    save_history(history)
    return jsonify({"status":"cleared"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)