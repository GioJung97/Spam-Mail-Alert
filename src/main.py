import time, json
from gmail_client import get_service, poll_once, mark_as_spam, unmark_spam_to_inbox, add_label
from classify.baseline import load_or_init, predict, _heuristics, combine_scores, explain
from storage import log_decision
from notify import notify
import math

POLL_SECONDS = 30

def ask_action(msg, suggested: str, score: float, reasons: str):
    print(f"Suggested: {suggested.upper()} (score={score:.2f})")
    print("Choose action: [s] Spam, [k] Keep, [l] Label 'Suspicious', [n] None (enter to accept suggestion)")
    while True:
        choice = input("> ").strip().lower()
        if choice == "":
            return suggested[0]
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

                model_scores = predict(model, texts)

                for m, mscore in zip(new_msgs, model_scores):
                    subject = (m["subject"] or "").strip()
                    heur, reasons_list = _heuristics(subject, m["snippet"], m["from"])
                    score = math.ceil(combine_scores(heur, float(mscore)))
                    reasons = explain(reasons_list, float(mscore))
                    suggested = "spam" if score >= 0.65 else ("suspicious" if score >= 0.50 else "keep")

                    # clickable URL to open the thread in Gmail (works for primary account index 0)
                    url = None
                    if m.get("threadId"):
                        url = f"https://mail.google.com/mail/u/0/#inbox/{m['threadId']}"

                    subtitle = f"{m['from']}"
                    notif_msg = f"Spam Possibility: {score * 100}% · {subject[:90]}"
                    notify(title="New Email", subtitle=subtitle, message=notif_msg, url=url)


                    # Keep the CLI as the action surface
                    print(f"\n— From: {m['from']}\n  Subject: {subject[:200]}\n  Spam Possibility: {score * 100}%\n  Reasons: {reasons}")
                    action_key = ask_action(m, suggested, score, reasons)

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
