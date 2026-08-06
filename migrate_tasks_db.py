#!/usr/bin/env python3
import os
import sqlite3

DEFAULT_PATHS = [
    os.getenv('DB_PATH'),
    '/app/data/orders.db',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'orders.db'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'orders.db')
]

DB_PATH = next((p for p in DEFAULT_PATHS if p and os.path.exists(p)), None)

if not DB_PATH:
    print('ERROR: database file not found. Checked paths:')
    for p in DEFAULT_PATHS:
        print(' -', p)
    raise SystemExit(1)

print('Using database:', DB_PATH)
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Helper functions

def table_exists(name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def column_exists(table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row['name'] == column for row in cur.fetchall())


def create_pending_tasks():
    print('Creating table pending_tasks...')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pending_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_text TEXT NOT NULL,
            author TEXT,
            author_id TEXT,
            priority TEXT DEFAULT 'Обычный',
            deadline TEXT,
            order_id INTEGER,
            taken_by TEXT,
            taken_by_id TEXT,
            taken_at TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE SET NULL
        )
    ''')
    conn.commit()
    print('pending_tasks created or already exists')


def create_completed_tasks():
    print('Creating table completed_tasks...')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS completed_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_text TEXT NOT NULL,
            author TEXT,
            author_id TEXT,
            completed_by TEXT,
            completed_by_id TEXT,
            completion_time TEXT,
            order_id INTEGER,
            taken_by TEXT,
            taken_by_id TEXT,
            taken_at TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE SET NULL
        )
    ''')
    conn.commit()
    print('completed_tasks created or already exists')


def add_column(table, column, definition):
    if column_exists(table, column):
        print(f'Column {column} already exists in {table}')
        return
    print(f'Adding column {column} to {table}')
    cur.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
    conn.commit()


print()  # newline
print('Checking tables...')

if not table_exists('pending_tasks'):
    create_pending_tasks()
else:
    print('pending_tasks already exists')
    add_column('pending_tasks', 'task_text', 'TEXT')
    add_column('pending_tasks', 'author', 'TEXT')
    add_column('pending_tasks', 'author_id', 'TEXT')
    add_column('pending_tasks', 'priority', "TEXT DEFAULT 'Обычный'")
    add_column('pending_tasks', 'deadline', 'TEXT')
    add_column('pending_tasks', 'order_id', 'INTEGER')
    add_column('pending_tasks', 'taken_by', 'TEXT')
    add_column('pending_tasks', 'taken_by_id', 'TEXT')
    add_column('pending_tasks', 'taken_at', 'TEXT')
    add_column('pending_tasks', 'created_at', 'TEXT')
    add_column('pending_tasks', 'updated_at', 'TEXT')

if not table_exists('completed_tasks'):
    create_completed_tasks()
else:
    print('completed_tasks already exists')
    add_column('completed_tasks', 'task_text', 'TEXT')
    add_column('completed_tasks', 'author', 'TEXT')
    add_column('completed_tasks', 'author_id', 'TEXT')
    add_column('completed_tasks', 'completed_by', 'TEXT')
    add_column('completed_tasks', 'completed_by_id', 'TEXT')
    add_column('completed_tasks', 'completion_time', 'TEXT')
    add_column('completed_tasks', 'order_id', 'INTEGER')
    add_column('completed_tasks', 'taken_by', 'TEXT')
    add_column('completed_tasks', 'taken_by_id', 'TEXT')
    add_column('completed_tasks', 'taken_at', 'TEXT')

print()  # newline
print('Ensuring indexes...')
cur.execute('CREATE INDEX IF NOT EXISTS idx_order_number ON orders(order_number)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_phone ON orders(phone)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_client_name ON orders(client_name)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_device ON orders(device)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_status ON orders(status)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_master ON orders(master)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_pending_tasks_taken_by_id ON pending_tasks(taken_by_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_pending_tasks_author_id ON pending_tasks(author_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_completed_tasks_completed_by_id ON completed_tasks(completed_by_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_completed_tasks_completion_time ON completed_tasks(completion_time)')
conn.commit()
print('Indexes ensured')

print()  # newline
print('Schema check completed. Table definitions:')
for table in ['pending_tasks', 'completed_tasks']:
    if table_exists(table):
        print(f'-- {table}')
        cur.execute(f'PRAGMA table_info({table})')
        for row in cur.fetchall():
            print('   ', row['cid'], row['name'], row['type'], 'NULL' if row['notnull'] == 0 else 'NOT NULL', 'DEFAULT=' + str(row['dflt_value']))
    else:
        print(f'-- {table} missing')

conn.close()
print('Done.')
