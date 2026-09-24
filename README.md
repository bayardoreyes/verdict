# Verdict

An AI-assisted expense reimbursement decision system with a human-in-the-loop review workflow — designed and built end-to-end, from the data model to the cloud deployment.

## Live Demo

**App:** https://verdict-em5w.onrender.com/login

| Role | Email | Password |
|---|---|---|
| Reviewer | `reviewer@antonios.com` | `testpass123` |
| Employee | `employee@antonios.com` | `testpass123` |

Log in as **Employee** to submit an expense and get an instant AI-assisted decision. Log in as **Reviewer** to see the review queue, approve/reject/revert decisions, manage policy rules, and check the AI-vs-human agreement rate on the reports page.

> The database is shared across everyone who visits this demo — feel free to poke around, nothing here is production data.

## What It Does

Verdict automates first-pass approval of employee expense requests against a company's reimbursement policy, then routes anything uncertain to a human reviewer. Every decision — AI or human — is fully auditable.

- **Hybrid decision engine:** an LLM-based engine (via OpenRouter) evaluates each request against the active policy; if it fails or returns an invalid response, the system automatically falls back to a deterministic rule-based engine. Both implement the same `DecisionEngine` interface (Strategy pattern).
- **Human-in-the-loop review:** AI decisions of `ESCALATE` go to a reviewer queue. A reviewer can approve, reject, or revert *any* past decision at any time — the AI never has the final word on its own.
- **Full audit trail:** every decision and every manual override is logged with before/after values, so the reasoning behind any expense's status is always traceable.
- **Role-based access:** Employees can submit and track their own requests; Reviewers get the full queue, policy rule management, and reporting.

## Tech Stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.x
- **Database:** PostgreSQL
- **Frontend:** Server-rendered Jinja2 templates, cookie-based JWT auth
- **AI:** OpenRouter (LLM-based decisioning with rule-based fallback)
- **Deployment:** Docker container on Render, with a managed Render PostgreSQL instance
- **Testing:** pytest

## Running Locally

```bash
git clone https://github.com/bayardoreyes/verdict.git
cd verdict
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://user:pass@localhost:5432/verdict_db
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
JWT_SECRET_KEY=any_random_string
JWT_EXPIRATION_MINUTES=60
```

Then initialize the database and start the server:

```bash
python init_db.py
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/login`.

### Running with Docker

```bash
docker build -t verdict-app .
docker run --env-file .env -p 8000:8000 verdict-app
```

## Author

Built by [Bayardo Reyes](https://github.com/bayardoreyes).