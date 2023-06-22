import sqlite3 as sq

async def db_start():
    global db, cur

    db = sq.connect('db.sqlite3')
    cur = db.cursor()
    db.commit()

async def get_user_presentations(client_id):
    presentations = cur.execute('SELECT * FROM meetups_presentation WHERE speaker_id = ?', (client_id,))
    print(presentations.fetchall())

async def get_user_events(client_id):
    events = cur.execute('SELECT * FROM meetups_visitor WHERE client_id = ?', (client_id,))
    print(events.fetchall())
