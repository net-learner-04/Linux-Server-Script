import sqlite3
import datetime as dt
import logging as log
from contextlib import closing
from config import DB_FILE


def init_db():
    '''Function that creates the SQLite database and tables if they do not exist.'''
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS metric_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                recorded_at TEXT NOT NULL
            )
        ''')
        conn.commit()
        log.info("State database initialized.")


def get_state(key, default=None):
    '''Function that reads a single key/value pair from the state table.'''
    with closing(sqlite3.connect(DB_FILE)) as conn:
        row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default


def set_state(key, value):
    '''Function that writes (or overwrites) a single key/value pair in the state table.'''
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.execute('''
            INSERT INTO state (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        ''', (key, str(value)))
        conn.commit()


def record_alert(item, severity, message):
    '''Function that appends a sent alert to the alert history table.'''
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.execute('''
            INSERT INTO alert_history (item, severity, message, sent_at)
            VALUES (?, ?, ?, ?)
        ''', (item, severity, message, dt.datetime.now().isoformat()))
        conn.commit()


def record_metric(name, value):
    '''Function that appends a metric sample to the metric history table (used for trend prediction).'''
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.execute('''
            INSERT INTO metric_history (name, value, recorded_at)
            VALUES (?, ?, ?)
        ''', (name, value, dt.datetime.now().isoformat()))
        conn.commit()


def get_metric_history(name, since_days):
    '''Function that returns (recorded_at, value) samples for a metric within the last N days.'''
    cutoff = (dt.datetime.now() - dt.timedelta(days=since_days)).isoformat()
    with closing(sqlite3.connect(DB_FILE)) as conn:
        rows = conn.execute('''
            SELECT recorded_at, value FROM metric_history
            WHERE name = ? AND recorded_at >= ?
            ORDER BY recorded_at ASC
        ''', (name, cutoff)).fetchall()
        return rows


def prune_metric_history(days_to_keep):
    '''Function that deletes metric samples older than the given number of days (keeps the DB small).'''
    cutoff = (dt.datetime.now() - dt.timedelta(days=days_to_keep)).isoformat()
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.execute("DELETE FROM metric_history WHERE recorded_at < ?", (cutoff,))
        conn.commit()
