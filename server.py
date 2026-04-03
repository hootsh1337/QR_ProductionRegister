#!/usr/bin/env python3
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, make_response
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "throughput.db")
TABLE_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc TEXT NOT NULL,
    work_order_id TEXT NOT NULL,
    planned_qty INTEGER,
    operation TEXT,
    actual_qty INTEGER NOT NULL,
    operator_name TEXT,
    station_id TEXT,
    extra_json TEXT
);
"""

app = Flask(__name__, static_folder=APP_DIR, static_url_path="")
init_db()
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(TABLE_SQL)
    con.commit()
    con.close()

@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

@app.route("/")
def root():
    return send_from_directory(APP_DIR, "index.html")

@app.route("/simple")
def simple():
    return send_from_directory(APP_DIR, "wo_form_simple.html")

@app.route("/submit", methods=["POST", "OPTIONS"])
def submit():
    if request.method == "OPTIONS":
        return make_response(("", 200))

    try:
        data = request.get_json(force=True, silent=True) or {}
        work_order_id = (data.get("work_order_id") or "").strip()
        if not work_order_id:
            return jsonify({"ok": False, "error": "Missing work_order_id"}), 400

        planned_qty = data.get("planned_qty")
        try:
            planned_qty = int(planned_qty) if planned_qty is not None and str(planned_qty).strip() != "" else None
        except Exception:
            planned_qty = None

        operation = (data.get("operation") or "").strip() or None

        actual_qty = data.get("actual_qty")
        try:
            actual_qty = int(actual_qty)
        except Exception:
            return jsonify({"ok": False, "error": "actual_qty must be an integer"}), 400

        operator_name = (data.get("operator_name") or "").strip() or None
        station_id = (data.get("station_id") or "").strip() or None
        extra_json = data.get("extra_json")

        ts_utc = datetime.utcnow().isoformat(timespec="seconds") + "Z"

        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(
            "INSERT INTO scans (ts_utc, work_order_id, planned_qty, operation, actual_qty, operator_name, station_id, extra_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ts_utc, work_order_id, planned_qty, operation, actual_qty, operator_name, station_id, extra_json),
        )
        con.commit()
        con.close()

        return jsonify({"ok": True, "ts_utc": ts_utc})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/export", methods=["GET"])
def export():
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 500")
        rows = [dict(r) for r in cur.fetchall()]
        con.close()
        return jsonify({"ok": True, "rows": rows})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
