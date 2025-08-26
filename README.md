# Spam Mail Alert

This is an individual project which is a background email notifier that checks incoming emails and classifies them as spam or not. This notification tool is mainly connected to Gmail using Model Context Protocol (MCP) to make AI models (or assistant) can have access to the email service.

## Features

- Connects securely to Gmail via OAuth2
- Polls for new messages (no cost, free Gmail API usage)
- Classifies spam using a baseline ML model (TF-IDF + LogisticRegression)
- Sends desktop notifications with spam status
<!-- - (Planned) Automatically applies Gmail labels (Spam / Safe)
- (Planned) Exposes MCP tools:
  - list_unread_emails
  - classify_email(message_id)
  - mark_as_spam(message_id)
  - explain_classification(message_id) -->


## Project Status

- [x] Gmail API authentication
- [x] Basic unread email listing
- [x] Polling loop with history tracking
- [x] Spam classification (baseline)
- [ ] Desktop notifications
- [ ] Gmail label actions
- [ ] MCP server integration


# How to get started

## Set up
Once the repo is cloned, install all the required libraries.
```
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
```
python src/main.py
```
- Once running the script, a browser will open for Google login. 
- On success, you should see “✅ Auth succeeded” and a short list of unread subjects/snippets (or “No unread messages found.”). 
- A **token.json** will appear (keep it private); and **state.json** will hold your baseline last_history_id.

#### ** MAKE SURE TO KEEP **credentials.json**, **token.json**, and **state.json** CREDENTIAL. **

### Case: Authentication Fail (ERROR 403: access_denied)
This happens when the user you are trying to log in has not been added to the list of approved testers.
- If the Authentication fails due to the `Access Blocked` error, make sure to complete the Google Verification Process (follow the instruction below).  
    - Go to the Google CLoud Console
    - Go to **APIs & Services** -> **OAuth consent screen**.
    - Look for the **Test users** section
    - Click the **+ ADD USERS** button
    - TYPE your email address and SAVE