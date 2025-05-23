import os
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

# Configuration
GITHUB_TOKEN = "ghp_" # Replace with your GitHub token
ORG_NAME = "" # Replace with your GitHub organization name
HANDLE = "" # Replace with your GitHub handle
INTERVAL_MINUTES = 30 # Check every 30 minutes, do not set to a lower value to avoid rate limits
SLACK_BOT_TOKEN = "xoxb-"
SLACK_USER_ID = "" # Replace with your Slack user ID
STATE_FILE = "/app/last_checked.txt"

# Headers for GitHub and Slack API requests
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}
GRAPHQL_URL = "https://api.github.com/graphql"
GRAPHQL_HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}"
}
SLACK_HEADERS = {
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json"
}

def load_last_checked():
    """Load the last-checked timestamp from file (= last_checked.txt) or default to now - INTERVAL."""
    try:
        with open(STATE_FILE, "r") as f:
            return datetime.fromisoformat(f.read().strip())
    except Exception:
        return datetime.now(timezone.utc) - timedelta(minutes=INTERVAL_MINUTES)

def save_last_checked(timestamp):
    """Save the current timestamp to the last_checked.txt file."""
    with open(STATE_FILE, "w") as f:
        f.write(timestamp.isoformat())

def check_issues_and_prs(item_type, since_time, handle):
    """
    Check issues or PRs updated since the last run.
    Only notify if:
    - You're mentioned in a comment
    - You're the author and someone replies
    - You've previously commented and someone else replies
    """
    results = []
    page = 1
    mentions = []

    while True:
        query = f"org:{ORG_NAME} is:{item_type} updated:>{since_time.isoformat()}"
        url = f"https://api.github.com/search/issues?q={quote(query)}&per_page=50&page={page}"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        results.extend(items)
        if len(items) < 50:
            break
        page += 1

    for item in results:
        issue_url = item["url"]
        item_author = item["user"]["login"]
        resp = requests.get(f"{issue_url}/comments", headers=HEADERS)
        resp.raise_for_status()
        comments = resp.json()

        has_user_commented = any(c["user"]["login"] == handle for c in comments)

        for comment in comments:
            created = datetime.strptime(comment["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if created <= since_time:
                continue
            author = comment["user"]["login"]
            body = comment.get("body", "").lower()
            if (
                handle in body
                or item_author == handle
                or (has_user_commented and author != handle)
            ):
                mentions.append({
                    "user": {"login": author},
                    "html_url": comment["html_url"]
                })

    return mentions

def check_discussion_mentions_smart(since_time):
    """
    Use GitHub GraphQL API to check all discussions in repos where:
    - You're mentioned
    - You're the discussion author
    - You've commented and someone else adds a new comment
    """
    query = """
    query($org: String!, $after: String) {
      organization(login: $org) {
        repositories(first: 50, after: $after) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            name
            discussions(first: 20, orderBy: {field: UPDATED_AT, direction: DESC}) {
              nodes {
                title
                url
                author { login }
                comments(first: 50) {
                  nodes {
                    body
                    createdAt
                    author {
                      login
                    }
                    url
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    mentions = []
    cursor = None

    while True:
        variables = {"org": ORG_NAME, "after": cursor}
        resp = requests.post(GRAPHQL_URL, headers=GRAPHQL_HEADERS, json={"query": query, "variables": variables})
        resp.raise_for_status()
        data = resp.json()

        repos = data.get("data", {}).get("organization", {}).get("repositories", {}).get("nodes", [])
        for repo in repos:
            for discussion in repo.get("discussions", {}).get("nodes", []):
                author = discussion.get("author", {}).get("login", "")
                comments = discussion.get("comments", {}).get("nodes", [])
                has_user_commented = any(c["author"]["login"] == HANDLE for c in comments)

                for comment in comments:
                    created = datetime.fromisoformat(comment["createdAt"].replace("Z", "+00:00"))
                    author_login = comment["author"]["login"]
                    body = comment.get("body", "").lower()
                    if created <= since_time:
                        continue
                    if (
                        HANDLE in body
                        or author == HANDLE
                        or (has_user_commented and author_login != HANDLE)
                    ):
                        mentions.append({
                            "user": {"login": author_login},
                            "html_url": comment["url"]
                        })

        page_info = data.get("data", {}).get("organization", {}).get("repositories", {}).get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    return mentions

def send_dm(message):
    """Send the notification message to Slack via DM."""
    payload = {"channel": SLACK_USER_ID, "text": message}
    resp = requests.post("https://slack.com/api/chat.postMessage", headers=SLACK_HEADERS, json=payload)
    if not resp.ok or not resp.json().get("ok"):
        print("❌ Slack send failed:", resp.text)

def notify(mentions):
    """Format and send the message if there are any new mentions."""
    if not mentions:
        print("✅ No new mentions.")
        return
    message = f"🚨 *New mention(s) for @{HANDLE}:*\n"
    for m in mentions:
        message += f"- [{m['user']['login']}]({m['html_url']})\n"
    print("🔔 Sending Slack DM...")
    send_dm(message)

def main():
    """Main loop: load last checked, run checks, notify, and save new state."""
    since_time = load_last_checked()
    print(f"🔎 Checking for mentions since {since_time.isoformat()}")

    mentions = []
    mentions += check_issues_and_prs("issue", since_time, HANDLE)
    mentions += check_issues_and_prs("pr", since_time, HANDLE)
    mentions += check_discussion_mentions_smart(since_time)

    notify(mentions)
    save_last_checked(datetime.now(timezone.utc))

if __name__ == "__main__":
    main()
