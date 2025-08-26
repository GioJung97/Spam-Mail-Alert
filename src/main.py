import time, json
from gmail_client import get_service, poll_once, mark_as_spam, unmark_spam_to_inbox, add_label
from classify.baseline import load_or_init, predict, _heuristics, combine_scores, explain
from storage import log_decision

POLL_SECONDS = 30

def ask_action(msg, suggested: str, score: float, reasons: str):
    print(f"Suggested: {suggested.upper()} (score={score:.2f})")
    print("Choose action: [s] Spam, [k] Keep, [l] Label 'Suspicious', [n] None (enter to accept suggestion)")
    while True:
        choice = input("> ").strip().lower()
        if choice == "":
            return suggested[0]  # first letter of suggested
        if choice in {"s","k","l","n"}:
            return choice
        print("Please enter s/k/l/n or press Enter")

def main():
    svc = get_service()
    print("✅ Auth OK. Loading model…")
    model = load_or_init()

    print("Starting poll loop…")
    while True:
        try:
            new_msgs = poll_once(svc)
            if new_msgs:
                print(f"📥 New messages: {len(new_msgs)}")
                texts = []
                for m in new_msgs:
                    subj = (m["subject"] or "").strip()
                    text = f"{subj}\n{m['snippet']}"
                    texts.append(text)

                # Model probabilities (cold start returns 0.5)
                model_scores = predict(model, texts)

                for m, mscore in zip(new_msgs, model_scores):
                    subject = (m["subject"] or "").strip()
                    heur, reasons_list = _heuristics(subject, m["snippet"], m["from"])
                    score = combine_scores(heur, float(mscore))
                    reasons = explain(reasons_list, float(mscore))

                    # Simple rule for suggestion
                    suggested = "spam" if score >= 0.65 else ("suspicious" if score >= 0.50 else "keep")

                    print(f"\n— From: {m['from']}\n  Subject: {subject[:200]}\n  Score: {score:.2f}\n  Reasons: {reasons}")

                    action_key = ask_action(m, suggested, score, reasons)

                    # Map action to Gmail + label for logging
                    if action_key == "s":
                        mark_as_spam(svc, m["id"])
                        chosen = "spam"
                        print("→ Moved to Spam")
                    elif action_key == "k":
                        unmark_spam_to_inbox(svc, m["id"])
                        chosen = "ham"
                        print("→ Kept in Inbox")
                    elif action_key == "l":
                        add_label(svc, m["id"], "Suspicious")
                        chosen = "suspicious"
                        print("→ Labeled 'Suspicious'")
                    else:
                        chosen = "none"
                        print("→ No action")

                    log_decision(m["id"], score, chosen, reasons)

        except KeyboardInterrupt:
            print("\nStopping.")
            break
        except Exception as e:
            print(f"[error] {e!r}")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
