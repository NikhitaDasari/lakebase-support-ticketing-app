# Lakebase Support Ticketing App

A Databricks App backed by **Databricks Lakebase/PostgreSQL** for managing internal support tickets and ticket conversations.

The application demonstrates a simple operational-data pattern on Databricks: authenticated users create and manage tickets through a Flask UI while application state is persisted in relational Lakebase tables.

**Tech:** Databricks Apps · Lakebase/PostgreSQL · Python · Flask · SQL · Databricks SDK

---

## What this project demonstrates

- Building and deploying a stateful application with Databricks Apps
- Persisting operational application data in Lakebase/PostgreSQL
- Modeling related ticket and message entities with relational keys
- Reading and writing database state from a Flask application
- Attributing user actions through Databricks forwarded identity
- Implementing ticket creation, messaging, status management, and deletion
- Keeping database credentials outside source code through Databricks secrets
- Providing health and database-connectivity endpoints for operational checks

---

## Architecture

```text
Authenticated User
       |
       v
+---------------------+
| Databricks App UI   |
| Flask + templates   |
+----------+----------+
           |
           v
+---------------------+
| Application routes  |
| tickets / messages  |
| status / health     |
+----------+----------+
           |
           v
+---------------------+
| Databricks Lakebase |
| PostgreSQL          |
|                     |
| support_app.tickets |
| ticket_messages     |
+---------------------+
```

---

## Core data model

### `support_app.tickets`

Stores the current ticket state.

```text
ticket_id
title
status
created_by
created_at
```

### `support_app.ticket_messages`

Stores the conversation history associated with each ticket.

```text
message_id
ticket_id
message_text
author
created_at
```

`ticket_messages.ticket_id` relates each message to its parent ticket.

---

## Application capabilities

### Ticket management

Users can:

- view all tickets,
- open a ticket and review its messages,
- create a new ticket,
- update ticket status,
- delete a ticket and its associated messages.

Supported ticket states include:

```text
open
in_progress
resolved
```

### Ticket conversations

Users can add messages to an existing ticket. Messages are stored separately from the ticket record so the application preserves a chronological conversation history.

### User attribution

When running as a Databricks App, the application reads the authenticated user's `X-Forwarded-Email` header and records that identity for ticket creation and messages. For local development, it falls back to the Databricks SDK current-user API.

### Operational checks

The project includes:

```http
GET /healthz
GET /db-test
```

`/healthz` verifies the Flask application is running, while `/db-test` verifies Lakebase connectivity and returns the current ticket count.

---

## Repository structure

```text
.
├── app.py                    # Flask application and ticket routes
├── lakebase.py               # Lakebase/PostgreSQL connection utilities
├── app.yaml                  # Databricks App configuration
├── setup_secrets.py          # Databricks secret setup
├── requirements.txt
├── .env.example
└── templates/
    ├── index.html            # Ticket list
    ├── create_ticket.html    # Create-ticket form
    └── ticket_details.html   # Ticket details and messages
```

---

## Running locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the Lakebase connection using the expected environment/secret settings, then run:

```bash
python app.py
```

---

## Databricks deployment

The application is designed to deploy through **Databricks Apps** using the included `app.yaml` configuration.

Database credentials are loaded through Databricks secrets rather than being committed to the repository.

---

## Why this project matters

This project focuses on the operational-data layer behind an application rather than an analytical pipeline: relational modeling, persistent state, authenticated user actions, application-to-database integration, and deployment on Databricks.

It serves as a foundational Lakebase application alongside the more advanced semantic-retrieval and agent projects in this portfolio.
