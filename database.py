import csv
import os
import sqlite3
from datetime import datetime
import subprocess
import json
import logging
import configparser

script_directory = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

config = configparser.ConfigParser()
config.read(os.path.join(script_directory, 'config.ini'))

DB_PATH = os.path.join(script_directory, config['paths']['DB_PATH'])
REGOLANCER_DIR = script_directory

def setup_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS peers (
            id INTEGER PRIMARY KEY,
            peer_alias TEXT,
            chan_id TEXT,
            remote_pubkey TEXT,
            rebal_rate INTEGER
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS rebalances (
            id INTEGER PRIMARY KEY,
            timestamp INTEGER,
            date TEXT,
            from_channel TEXT,
            to_channel TEXT,
            amount_sats INTEGER,
            fees_sats INTEGER,
            ppm INTEGER
        )
    """)
    conn.commit()
    logging.info("Database setup completed successfully.")
    return conn

def save_to_database(conn, data):
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO rebalances (timestamp, date, from_channel, to_channel, amount_sats, fees_sats, ppm)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    logging.info(f"Data saved to rebalances: {data}")

def read_and_save_csv(file_path, alias_dict, conn):
    cursor = conn.cursor()
    if not os.path.exists(file_path):
        logging.warning(f"CSV file not found: {file_path}")
        return
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            timestamp = int(row['timestamp'])
            
            cursor.execute(f"SELECT COUNT(*) FROM rebalances WHERE timestamp = ?", (timestamp,))
            if cursor.fetchone()[0] > 0:
                logging.info(f"Skipping existing record with timestamp {timestamp}")
                continue
            
            readable_date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            from_channel = alias_dict.get(row['from_channel'], row['from_channel'])
            to_channel = alias_dict.get(row['to_channel'], row['to_channel'])
            amount_sats = int(int(row['amount_msat']) / 1000)
            fees_sats = int(int(row['fees_msat']) / 1000)
            if amount_sats > 0:
                ppm = (1000000 / amount_sats) * fees_sats
            else:
                ppm = 0
            data = (timestamp, readable_date, from_channel, to_channel, amount_sats, fees_sats, int(ppm))
            save_to_database(conn, data)

def calculate_and_update_rebal_rate(conn):
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT to_channel, SUM(amount_sats) as total_amount, SUM(fees_sats) as total_fees
        FROM rebalances
        GROUP BY to_channel
    """)
    results = cursor.fetchall()
    for result in results:
        to_channel, total_amount, total_fees = result
        if total_amount > 0:
            rebal_rate = int((total_fees * 1000000) / total_amount)
        else:
            rebal_rate = 0
        logging.info(f"Rebal rate calculated for {to_channel}: {rebal_rate} (total_amount: {total_amount}, total_fees: {total_fees})")
        
        cursor.execute("""
            SELECT id FROM peers WHERE peer_alias = ?
        """, (to_channel,))
        peer = cursor.fetchone()
        
        if peer:
            cursor.execute("""
                UPDATE peers
                SET rebal_rate = ?
                WHERE id = ?
            """, (rebal_rate, peer[0]))
            logging.info(f"Rebal rate updated for {to_channel}: {rebal_rate}")
        else:
            logging.warning(f"Peer with alias {to_channel} not found. Cannot update rebal rate.")
    
    conn.commit()
    logging.info("Rebal rate updates committed successfully.")

def update_peers_table(conn):
    result = subprocess.run(['lncli', 'listchannels'], capture_output=True, text=True)
    if result.returncode != 0:
        logging.error("Error obtaining channel list. Ensure lncli is configured correctly.")
        return

    channels_json = result.stdout
    channels = json.loads(channels_json)['channels']

    cursor = conn.cursor()
    cursor.execute("DELETE FROM peers")
    for channel in channels:
        peer_alias = channel.get('peer_alias', 'Unknown')
        chan_id = channel['chan_id']
        remote_pubkey = channel['remote_pubkey']
        cursor.execute(f"""
            INSERT INTO peers (peer_alias, chan_id, remote_pubkey)
            VALUES (?, ?, ?)
        """, (peer_alias, chan_id, remote_pubkey))
    conn.commit()
    logging.info("Peers table updated successfully.")
    calculate_and_update_rebal_rate(conn)

def main():
    conn = setup_database(DB_PATH)

    if conn is not None:
        update_peers_table(conn)

        cursor = conn.cursor()
        cursor.execute("SELECT chan_id, peer_alias FROM peers")
        alias_dict = {row[0]: row[1] for row in cursor.fetchall()}

        csv_file = os.path.join(script_directory, 'stats-auto-rebal.csv')
        read_and_save_csv(csv_file, alias_dict, conn)
        
        conn.close()

if __name__ == "__main__":
    main()
