from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

DB = os.environ.get('DB_PATH', '/tmp/klinik.db')

def kon():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def kurulum():
    db = kon()
    db.execute('''CREATE TABLE IF NOT EXISTS kayitlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hasta TEXT NOT NULL,
        tarih TEXT NOT NULL,
        doktor TEXT NOT NULL,
        islemler TEXT NOT NULL,
        ucret REAL NOT NULL DEFAULT 0,
        odeme TEXT NOT NULL DEFAULT 'nakit',
        notlar TEXT DEFAULT ''
    )''')
    db.commit()
    db.close()

kurulum()

@app.route('/api/kayitlar', methods=['GET'])
def listele():
    db = kon()
    rows = db.execute('SELECT * FROM kayitlar ORDER BY tarih DESC').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/kayitlar', methods=['POST'])
def ekle():
    d = request.get_json()
    if not d or not d.get('hasta') or not d.get('tarih'):
        return jsonify({'hata': 'Eksik bilgi'}), 400
    islemler = ','.join(d['islemler']) if isinstance(d['islemler'], list) else d['islemler']
    db = kon()
    cur = db.execute(
        'INSERT INTO kayitlar (hasta,tarih,doktor,islemler,ucret,odeme,notlar) VALUES (?,?,?,?,?,?,?)',
        (d['hasta'], d['tarih'], d.get('doktor','ortopedi'), islemler,
         float(d.get('ucret', 0)), d.get('odeme','nakit'), d.get('notlar',''))
    )
    yeni_id = cur.lastrowid
    db.commit()
    row = db.execute('SELECT * FROM kayitlar WHERE id=?', (yeni_id,)).fetchone()
    db.close()
    return jsonify(dict(row)), 201

@app.route('/api/kayitlar/<int:kid>', methods=['PUT'])
def guncelle(kid):
    d = request.get_json()
    if not d:
        return jsonify({'hata': 'Veri yok'}), 400
    islemler = ','.join(d['islemler']) if isinstance(d['islemler'], list) else d['islemler']
    db = kon()
    db.execute(
        'UPDATE kayitlar SET hasta=?,tarih=?,doktor=?,islemler=?,ucret=?,odeme=?,notlar=? WHERE id=?',
        (d['hasta'], d['tarih'], d.get('doktor','ortopedi'), islemler,
         float(d.get('ucret', 0)), d.get('odeme','nakit'), d.get('notlar',''), kid)
    )
    db.commit()
    row = db.execute('SELECT * FROM kayitlar WHERE id=?', (kid,)).fetchone()
    db.close()
    return jsonify(dict(row))

@app.route('/api/kayitlar/<int:kid>', methods=['DELETE'])
def sil(kid):
    db = kon()
    db.execute('DELETE FROM kayitlar WHERE id=?', (kid,))
    db.commit()
    db.close()
    return jsonify({'ok': True})

@app.route('/api/rapor')
def rapor():
    bas = request.args.get('bas', '2000-01-01')
    bit = request.args.get('bit', '2099-12-31')
    doc = request.args.get('doktor', '')
    db = kon()
    q = 'SELECT * FROM kayitlar WHERE tarih>=? AND tarih<=?'
    p = [bas + 'T00:00:00', bit + 'T23:59:59']
    if doc:
        q += ' AND doktor=?'
        p.append(doc)
    rows = [dict(r) for r in db.execute(q, p).fetchall()]
    db.close()
    toplam   = sum(r['ucret'] for r in rows)
    nakit    = sum(r['ucret'] for r in rows if r['odeme'] == 'nakit')
    kk       = sum(r['ucret'] for r in rows if r['odeme'] == 'kk')
    havale   = sum(r['ucret'] for r in rows if r['odeme'] == 'havale')
    return jsonify({'kayitlar': rows, 'toplam': toplam,
                    'nakit': nakit, 'kk': kk, 'havale': havale})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def spa(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
