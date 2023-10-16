import sqlite3

import models
from typing import List

def get_distinct_tracking_ids_for_courier_name(courier_name: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        SELECT DISTINCT tracking_id FROM Packages
        WHERE courier_name = ?
    """

    cur.execute(query, (courier_name,))
    tracking_ids = [row[0] for row in cur.fetchall()]

    conn.close()

    return tracking_ids

def get_tracking_ids_for_guild_id(guild_id: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        SELECT tracking_id FROM Packages
        WHERE guild_id = ?
    """

    cur.execute(query, (guild_id,))
    tracking_ids = [row[0] for row in cur.fetchall()]

    conn.close()

    return tracking_ids

def get_guild_ids_for_tracking_id(tracking_id: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        SELECT guild_id FROM Packages
        WHERE tracking_id = ?
    """

    cur.execute(query, (tracking_id,))
    guild_ids = [row[0] for row in cur.fetchall()]

    conn.close()

    return guild_ids

def get_update_channels_for_guild_ids(guild_ids: List[str]):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        SELECT updates_channel FROM Guilds
        WHERE guild_id IN ({});
    """.format(', '.join(['?'] * len(guild_ids)))

    cur.execute(query, guild_ids)
    update_channels = cur.fetchall()

    conn.close()

    return update_channels


def get_last_location_for_tracking_id(tracking_id: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        SELECT last_location FROM Packages
        WHERE tracking_id = ?
    """

    cur.execute(query, (tracking_id,))
    last_location = cur.fetchone()[0]

    conn.close()

    return last_location

def insert_guild(guild_id: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        INSERT INTO Guilds (guild_id, updates_channel)
        VALUES (?, NULL)
    """

    cur.execute(query, (guild_id,))
    conn.commit()
    conn.close()

def insert_package(guild_id: str, package: models.Package):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        INSERT INTO Packages (guild_id, tracking_id, courier_name, last_location, description)
        VALUES (?, ?, ?, ?, ?)
    """

    cur.execute(query, (guild_id, package.tracking_id, package.courier_name, package.last_location, package.description))
    conn.commit()
    conn.close()

def delete_guild(guild_id: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        DELETE FROM Guilds
        WHERE guild_id = ?
    """

    cur.execute(query, (guild_id,))
    conn.commit()
    conn.close()

def delete_package(guild_ids: List[str], tracking_id: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        DELETE FROM Packages
        WHERE tracking_id = ? AND guild_id IN ({});    
    """.format(', '.join(['?'] * len(guild_ids)))

    cur.execute(query, (tracking_id,) + tuple(guild_ids))
    conn.commit()
    conn.close()

def update_channel(guild_id: str, update_channel: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        UPDATE Guilds
        SET updates_channel = ?
        WHERE guild_id = ?
    """

    cur.execute(query, (update_channel, guild_id))
    conn.commit()
    conn.close()

def update_package_last_location(tracking_id: str, location: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        UPDATE Packages
        SET last_location = ?
        WHERE tracking_id = ?
    """

    cur.execute(query, (location, tracking_id))
    conn.commit()
    conn.close()

def update_package_description(guild_id: str, tracking_id: str, description: str):
    conn = sqlite3.connect("/data/data.sqlite3")
    cur = conn.cursor()

    query = """
        UPDATE Packages
        SET description = ?
        WHERE tracking_id = ? AND guild_id = ?
    """

    cur.execute(query, (description, tracking_id, guild_id))
    conn.commit()
    conn.close()