import json
import sqlite3
import sys


# Usage: python3 migrate.py <input_file>
# Use this to migrate from the old json file to the new sqlite3 database
# The input file should be the old json file
# Just replace the database that is created when you first start the container with the one created by this script

input_file = sys.argv[1]

def insert_guild(guild_id, updates_channel):
    conn = sqlite3.connect("data.sqlite3")
    cur = conn.cursor()

    query = """
        INSERT INTO Guilds (guild_id, updates_channel)
        VALUES (?, ?)
    """

    cur.execute(query, (guild_id, updates_channel))
    conn.commit()
    conn.close()

with open("data.sqlite3", "w") as file:
    pass

conn = sqlite3.connect("data.sqlite3")
cur = conn.cursor()

query = """
ATTACH DATABASE 'data.sqlite3' AS GuildData;

CREATE TABLE IF NOT EXISTS Packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_id TEXT,
    courier_name TEXT,
    description TEXT,
    last_location TEXT,
    guild_id TEXT,
    FOREIGN KEY (guild_id) REFERENCES Guilds(guild_id)
);

CREATE TABLE IF NOT EXISTS Guilds (
    guild_id TEXT PRIMARY KEY,
    updates_channel TEXT
);
"""

cur.executescript(query)
conn.commit()
conn.close()


with open(input_file, "r") as f:
    guild_data = json.load(f)
    for guild_id in guild_data:
        updates_channel = guild_data[guild_id]["updates_channel"]
        insert_guild(guild_id, updates_channel)

