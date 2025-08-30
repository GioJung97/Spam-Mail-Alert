# 📧 Spam Notifier MCP

This project provides hands-on experience with the Model Context Protocol (MCP) and a simple machine learning workflow using a Logistic Regression model for spam detection.  

Spam Notifier MCP is a background email agent that monitors your Gmail inbox, detects new messages, classifies them as spam or not-spam, and notifies you instantly on your desktop. It also exposes its core functions as **MCP tools**, allowing AI clients (e.g., Claude Desktop) to interact with your inbox in real-time.

---

## ✨ Features

- **Real-time Gmail monitoring**  
  Polls your Gmail inbox using the Gmail API and detects new incoming emails.

- **Desktop notifications**  
  Instant macOS notifications with sender, subject, and spam score.

- **Spam classification**  
  Combines heuristic rules (keywords, links, suspicious domains) with a machine learning baseline (TF-IDF + Logistic Regression). Improves over time as you label emails.

- **One-click actions**  
  Mark messages as Spam, keep them in Inbox, or label them as Suspicious.

- **Persistent logging & retraining**  
  Logs every decision to SQLite, enabling incremental training and better spam detection.

- **MCP integration**  
  Exposes tools (`list_unread_emails`, `classify_message`, `mark_as_spam`, `explain_decision`) so any MCP-aware client (like Claude Desktop) can interact with your mailbox programmatically.

---

# 🚀 Getting Started

## Clone and install dependencies
```bash
git clone https://github.com/your-username/spam-notifier-mcp.git
cd spam-notifier-mcp
pip install -r requirements.txt
```

## Enable Gmail API
To connect with Gmail, the API needs to be enabled.  

1. Go to Google Cloud Console → create a project (any name).  
2. APIs & Services → “Enable APIs and Services” → enable Gmail API.  
3. APIs & Services → Credentials → Create Credentials → OAuth client ID.  
   - Application type: Desktop app.
4. Download `credentials.json` into the project root.

## Run First Test
```bash
python src/main.py
```
- Once running the script, a browser will open for Google login. 
- On success, you should see “✅ Auth succeeded” and a short list of unread subjects/snippets (or “No unread messages found.”). 
- A **token.json** will appear (keep it private); and **state.json** will hold your baseline last_history_id.
- Try testing emails and see if you get any messages (with notification) from the shell.

⚠️ **Important:** Keep `credentials.json`, `token.json`, and `state.json` private.  
Never commit them to GitHub. They are already included in `.gitignore`.


### Case: Authentication Fail (ERROR 403: access_denied)
This happens when the user you are trying to log in has not been added to the list of approved testers.
- If the Authentication fails due to the `Access Blocked` error, make sure to complete the Google Verification Process (follow the instruction below).  
    - Go to the Google Cloud Console
    - Go to **APIs & Services** -> **OAuth consent screen**.
    - Look for the **Test users** section
    - Click the **+ ADD USERS** button
    - TYPE your email address and SAVE

## MCP Server Connection

1. Download [Claude Desktop](https://claude.ai/download), if you haven't yet
2. Go to Setting → Developer → Click `edit config`
3. Open `claude_desktop_config.json` file
4. Change the configuration as follows:
```json
{
    "mcpServers": {
        "spam_notifier": {
            "command": "python",
            "args": [
                "Absolute/path/to/spam_notifier_mcp/src/mcp_server.py"
            ],
            "cwd": "Absolute/path/to/spam_notifier_mcp"
        }
    }
}
```
5. Reboot Claude Desktop and check if the server is connected. 
    - Further details can be found in the website: https://modelcontextprotocol.io/quickstart/server
6. Test out the features (or tools) with Claude AI