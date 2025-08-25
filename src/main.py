import time
from gmail_client import get_service, poll_once, mark_as_spam, unmark_spam_to_inbox, add_label

POLL_SECONDS = 120  # we'll shorten during testing if you want

def ask_action(msg):
    """Simple CLI prompt for actions (will replace with notifications later)."""
    print("Choose action: [s] Mark as Spam, [k] Keep (Not Spam), [l] Add 'Suspicious' label, [n] None")
    while True:
        choice = input("> ").strip().lower()
        if choice in {"s","k","l","n"}:
            return choice
        print("Please enter s/k/l/n")

def main():
    svc = get_service()
    print("✅ Auth OK. Starting poll loop…")
    while True:
        try:
            new_msgs = poll_once(svc)
            if new_msgs:
                print(f"📥 New messages: {len(new_msgs)}")
                for m in new_msgs:
                    subj = (m["subject"] or "").strip()
                    print(f"\n— From: {m['from']}\n  Subject: {subj[:200]}\n  Snippet: {m['snippet'][:200]}")
                    action = ask_action(m)
                    if action == "s":
                        mark_as_spam(svc, m["id"])
                        print("→ Moved to Spam")
                    elif action == "k":
                        unmark_spam_to_inbox(svc, m["id"])  # safe even if not in Spam
                        print("→ Kept in Inbox")
                    elif action == "l":
                        add_label(svc, m["id"], "Suspicious")
                        print("→ Labeled 'Suspicious'")
                    else:
                        print("→ No action")
            # else: nothing new
        except KeyboardInterrupt:
            print("\nStopping.")
            break
        except Exception as e:
            print(f"[error] {e!r}")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
