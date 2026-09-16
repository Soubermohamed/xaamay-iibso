from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os

app = Flask(__name__, static_folder='static')
DB_PATH = os.path.join(os.path.dirname(__file__), 'xaamay_iibso.db')

CATEGORIES = ['vehicules', 'immobilier', 'emploi', 'electronique', 'meubles', 'services', 'mode']

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            cat TEXT NOT NULL,
            price INTEGER,
            loc TEXT NOT NULL,
            phone TEXT NOT NULL,
            desc TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Seed with starter listings only if the table is empty (first run)
    count = conn.execute('SELECT COUNT(*) AS c FROM listings').fetchone()['c']
    if count == 0:
        seed = [
            ('Toyota Land Cruiser Prado 2016', 'vehicules', 9500000, 'Balbala', '77 12 34 56',
             "Land Cruiser Prado, moteur diesel, climatisation glaciale, pneus neufs. Papiers en règle."),
            ('Appartement 3 pièces à Héron', 'immobilier', 180000, 'Héron', '77 22 11 09',
             "Bel appartement 3 pièces, cuisine équipée, proche des commerces."),
            ('Comptable recherché(e) — CDD 6 mois', 'emploi', None, 'Djibouti Ville', '21 35 67 89',
             "Entreprise de logistique recherche un(e) comptable expérimenté(e)."),
            ('iPhone 13 Pro 256 Go', 'electronique', 145000, 'Ambouli', '77 45 90 12',
             "État neuf, batterie à 92%, avec boîte et chargeur d'origine."),
            ('Salon marocain 7 places', 'meubles', 220000, 'PK12', '77 66 33 21',
             "Fait sur mesure, tissu épais, très peu utilisé."),
            ('Cours particuliers de mathématiques', 'services', 5000, 'Boulaos', '77 88 02 14',
             "Niveau collège et lycée, déplacement possible à domicile."),
        ]
        conn.executemany(
            'INSERT INTO listings (title, cat, price, loc, phone, desc) VALUES (?,?,?,?,?,?)',
            seed
        )
        conn.commit()
    conn.close()

@app.route('/api/listings', methods=['GET'])
def get_listings():
    cat = request.args.get('cat')
    q = request.args.get('q', '').strip().lower()
    conn = get_db()
    rows = conn.execute('SELECT * FROM listings ORDER BY created_at DESC').fetchall()
    conn.close()
    items = [dict(r) for r in rows]
    if cat and cat != 'all':
        items = [i for i in items if i['cat'] == cat]
    if q:
        items = [i for i in items if q in (i['title'] + ' ' + i['desc'] + ' ' + i['loc']).lower()]
    return jsonify(items)

@app.route('/api/listings', methods=['POST'])
def create_listing():
    data = request.get_json(force=True)
    required = ['title', 'cat', 'loc', 'phone', 'desc']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Le champ "{field}" est requis.'}), 400
    if data['cat'] not in CATEGORIES:
        return jsonify({'error': 'Catégorie invalide.'}), 400

    price = data.get('price')
    price = int(price) if price not in (None, '') else None

    conn = get_db()
    cur = conn.execute(
        'INSERT INTO listings (title, cat, price, loc, phone, desc) VALUES (?,?,?,?,?,?)',
        (data['title'], data['cat'], price, data['loc'], data['phone'], data['desc'])
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute('SELECT * FROM listings WHERE id=?', (new_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/listings/<int:listing_id>', methods=['GET'])
def get_listing(listing_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM listings WHERE id=?', (listing_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Annonce introuvable.'}), 404
    return jsonify(dict(row))

@app.route('/api/listings/<int:listing_id>', methods=['DELETE'])
def delete_listing(listing_id):
    conn = get_db()
    conn.execute('DELETE FROM listings WHERE id=?', (listing_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/stats', methods=['GET'])
def stats():
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) AS c FROM listings').fetchone()['c']
    by_cat = conn.execute('SELECT cat, COUNT(*) AS c FROM listings GROUP BY cat').fetchall()
    conn.close()
    return jsonify({'total': total, 'by_category': {r['cat']: r['c'] for r in by_cat}})

# Serve the frontend
@app.route('/')
def index():
    return send_from_directory(os.path.dirname(__file__), 'index.html')

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
