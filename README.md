# GH Notifier

A lightweight tool to notify you via Slack whenever you're mentioned or replied to in GitHub issues, pull requests or discussions across your organization.

## Features

- Sends a Slack DM when:
  - You're mentioned (e.g., @yourhandle) in a comment
  - You're the author of the issue/PR/discussion and someone replies
  - You've commented before, and someone else replies
- Runs every 30 minutes (by default)
- Persists last_checked timestamp to avoid duplicate alerts
- Supports issues, PRs, and GitHub Discussions

## Requirements

- A GitHub Personal Access Token with `repo` and `read:org` scopes (classic token)
- A Slack bot token (`xoxb-...`) with permission to send DMs
- Your Slack User ID (`U12345678`) (see debug commands below)
- Docker Desktop

## Running with Docker Compose

Run it

```
docker compose up --build -d
```
The tool will run every 30 minutes and send a Slack message when a new relevant comment is found.

To stop

```
docker compose down
```

---

## Debug Commands

### GitHub

- **Test Personal Access Token**
  
  ```sh
  curl -H "Authorization: token <GITHUB_PAT>" https://api.github.com/orgs/skyscrapers/repos
  ```

- **Get Your User Info**
  
  ```sh
  curl -H "Authorization: token <GITHUB_PAT>" https://api.github.com/user
  ```

- **Search for Your GitHub Handle in Comments**
  
  ```sh
  curl -H "Authorization: token <GITHUB_PAT>" \
  "https://api.github.com/search/issues?q=%22<YOUR-GH-HANDLE>%22+in%3Acomments+org%3Askyscrapers+is%3Aissue+updated%3A%3E2025-05-14T17%3A50%3A00Z&sort=updated&order=desc"
  ```

### Slack

- **Get Your Slack User ID by Email**
  
  ```sh
  curl -s -H "Authorization: Bearer <SLACK_BOT_TOKEN>" \
  "https://slack.com/api/users.lookupByEmail?email=<EMAIL_ADDRESS>"
  ```

- **Send a Message to Yourself or a Channel**
  
  ```sh
  curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer <SLACK_BOT_TOKEN>" \
  -H "Content-type: application/json" \
  -d '{"channel":"<USER_ID_OR_CHANNEL>","text":"Hello from test"}'
  ```


### Possible future updates
- Introduce proper env variables to configure the tool
- ... ?
