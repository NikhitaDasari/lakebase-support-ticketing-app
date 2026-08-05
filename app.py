"""
Databricks Ticketing System App:
- Serves a Flask-based support ticket management system
- Reads/writes to Lakebase (Databricks-managed Postgres) via lakebase.py

Run locally:
    python app.py
Deploy as a Databricks App using app.yaml.
"""

import logging
import os

from databricks.sdk import WorkspaceClient
from flask import Flask, jsonify, redirect, render_template, request, url_for

import lakebase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticketing-app")

app = Flask(__name__)
_w = WorkspaceClient()


def _current_user_email() -> str:
    """
    Resolve the current user's email for ticket attribution.

    Databricks Apps inject the logged-in user's identity via the
    X-Forwarded-Email header on every request. Fall back to the Databricks
    SDK's current_user API for local development where that header isn't set.
    """
    header_email = request.headers.get("X-Forwarded-Email")
    if header_email:
        return header_email
    return _w.current_user.me().user_name


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})

@app.route("/db-test")
def db_test():
    rows = lakebase.run_query(
        """
        SELECT
            COUNT(*) AS ticket_count
        FROM support_app.tickets
        """
    )

    return jsonify(
        {
            "status": "connected",
            "ticket_count": rows[0]["ticket_count"],
        }
    )

@app.errorhandler(Exception)
def handle_exception(err):
    """Ensure all unhandled errors return JSON (not an HTML error page),
    so the frontend's resp.json() call never chokes on HTML."""
    logger.exception("Unhandled exception while processing request")
    status_code = getattr(err, "code", 500)
    if not isinstance(status_code, int):
        status_code = 500
    return jsonify({"error": str(err)}), status_code


@app.route("/")
def index():
    tickets = lakebase.run_query(
        """
        SELECT
            ticket_id,
            title,
            status,
            created_by,
            created_at
        FROM support_app.tickets
        ORDER BY ticket_id ASC
        """
    )

    return render_template(
        "index.html",
        tickets=tickets
    )

@app.route("/tickets/<int:ticket_id>")
def ticket_details(ticket_id):
    ticket_rows = lakebase.run_query(
        """
        SELECT
            ticket_id,
            title,
            status,
            created_by,
            created_at
        FROM support_app.tickets
        WHERE ticket_id = %s
        """,
        (ticket_id,),
    )

    if not ticket_rows:
        return jsonify({"error": "Ticket not found"}), 404

    messages = lakebase.run_query(
        """
        SELECT
            message_id,
            message_text,
            author,
            created_at
        FROM support_app.ticket_messages
        WHERE ticket_id = %s
        ORDER BY created_at ASC
        """,
        (ticket_id,),
    )

    return render_template(
        "ticket_details.html",
        ticket=ticket_rows[0],
        messages=messages,
    )

@app.route("/tickets/create", methods=["GET", "POST"])
def create_ticket():
    """Display the create ticket form (GET) or process the submission (POST)."""
    if request.method == "GET":
        return render_template("create_ticket.html")
    
    # POST: Handle form submission
    title = request.form.get("title", "").strip()
    status = request.form.get("status", "open").strip()
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
    
    # Get the current user's email
    created_by = _current_user_email()
    
    # Insert the new ticket into the database
    lakebase.run_write(
        """
        INSERT INTO support_app.tickets (title, status, created_by, created_at)
        VALUES (%s, %s, %s, now())
        """,
        (title, status, created_by),
    )
    
    # Redirect back to the main ticket list
    return redirect(url_for("index"))

@app.route("/tickets/<int:ticket_id>/messages", methods=["POST"])
def add_message(ticket_id):
    """Add a new message to a ticket."""
    message_text = request.form.get("message_text", "").strip()
    
    if not message_text:
        return jsonify({"error": "Message text is required"}), 400
    
    # Get the current user's email
    author = _current_user_email()
    
    # Insert the new message into the database
    lakebase.run_write(
        """
        INSERT INTO support_app.ticket_messages (ticket_id, message_text, author, created_at)
        VALUES (%s, %s, %s, now())
        """,
        (ticket_id, message_text, author),
    )
    
    # Redirect back to the ticket details page
    return redirect(url_for("ticket_details", ticket_id=ticket_id))

@app.route("/tickets/<int:ticket_id>/status", methods=["POST"])
def update_status(ticket_id):
    """Update the status of a ticket."""
    new_status = request.form.get("status", "").strip()
    
    if not new_status:
        return jsonify({"error": "Status is required"}), 400
    
    # Valid status values
    valid_statuses = ["open", "in_progress", "resolved"]
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
    
    # Update the ticket status in the database
    lakebase.run_write(
        """
        UPDATE support_app.tickets
        SET status = %s
        WHERE ticket_id = %s
        """,
        (new_status, ticket_id),
    )
    
    # Redirect back to the ticket details page
    return redirect(url_for("ticket_details", ticket_id=ticket_id))

@app.route("/tickets/<int:ticket_id>/delete", methods=["POST"])
def delete_ticket(ticket_id):
    """Delete a ticket and all its associated messages."""
    # First, delete all messages associated with this ticket
    lakebase.run_write(
        """
        DELETE FROM support_app.ticket_messages
        WHERE ticket_id = %s
        """,
        (ticket_id,),
    )
    
    # Then, delete the ticket itself
    lakebase.run_write(
        """
        DELETE FROM support_app.tickets
        WHERE ticket_id = %s
        """,
        (ticket_id,),
    )
    
    # Redirect back to the main ticket list
    return redirect(url_for("index"))


if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', 8000))
    app.run(debug=True, host=host, port=port)
    print(f"Flask app running on http://{host}:{port}")