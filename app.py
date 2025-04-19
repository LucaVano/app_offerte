from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import os
import json
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename

from models.database import Database
from models.offerta import Offerta
from utils.pdf_generator import generate_pdf
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'valtservice_secret_key'  # Cambiare in produzione
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['DATA_FOLDER'] = os.path.join(app.root_path, 'data')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# Inizializzazione delle cartelle necessarie
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

# Inizializzazione del database
db = Database(app.config['DATA_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/')
def index():
    offerte = db.get_all_offerte()
    return render_template('index.html', offerte=offerte)

@app.route('/nuova-offerta', methods=['GET', 'POST'])
def nuova_offerta():
    if request.method == 'GET':
        # Genera un nuovo numero di offerta per il form
        next_number = db.get_next_offer_number()
        return render_template('nuova_offerta.html', next_number=next_number)
    
    elif request.method == 'POST':
        # Gestisce il salvataggio della nuova offerta
        data = {
            'date': request.form.get('date'),
            'customer': request.form.get('customer'),
            'customer_email': request.form.get('customer_email'),
            'address': request.form.get('address'),
            'offer_description': request.form.get('offer_description'),
            'offer_number': request.form.get('offer_number'),
            'tabs': []
        }
        
        # Processa i tab del form
        tab_count = int(request.form.get('tab_count', 0))
        for i in range(tab_count):
            tab_type = request.form.get(f'tab_type_{i}')
            
            if tab_type == 'single_product':
                # Gestione caricamento immagine
                product_image = request.files.get(f'product_image_{i}')
                image_path = ''
                
                if product_image and allowed_file(product_image.filename):
                    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{product_image.filename}")
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    product_image.save(image_path)
                    image_path = '/static/uploads/' + filename  # Path relativo per il salvataggio
                
                data['tabs'].append({
                    'type': 'single_product',
                    'product_code': request.form.get(f'product_code_{i}'),
                    'product_name': request.form.get(f'product_name_{i}'),
                    'quantity': request.form.get(f'quantity_{i}'),
                    'unit_price': request.form.get(f'unit_price_{i}'),
                    'description': request.form.get(f'description_{i}'),
                    'discount': request.form.get(f'discount_{i}', '0'),
                    'discount_flag': request.form.get(f'discount_flag_{i}') == 'on',
                    'power_w': request.form.get(f'power_w_{i}'),
                    'volts': request.form.get(f'volts_{i}'),
                    'size': request.form.get(f'size_{i}'),
                    'posizione': request.form.get(f'posizione_{i}'),
                    'product_image_path': image_path
                })
            
            elif tab_type == 'multi_product':
                products = []
                product_count = int(request.form.get(f'product_count_{i}', 0))
                
                for j in range(product_count):
                    products.append([
                        request.form.get(f'product_name_{i}_{j}'),
                        request.form.get(f'product_model_{i}_{j}'),
                        request.form.get(f'product_price_{i}_{j}'),
                        request.form.get(f'product_quantity_{i}_{j}'),
                        request.form.get(f'product_description_{i}_{j}')
                    ])
                
                data['tabs'].append({
                    'type': 'multi_product',
                    'max_items_per_page': int(request.form.get(f'max_items_per_page_{i}', 3)),
                    'products': products
                })
        
        # Salva l'offerta e genera PDF
        offerta_id = db.save_offerta(data)
        offerta = db.get_offerta(offerta_id)
        
        pdf_path = generate_pdf(offerta, app.root_path)
        db.update_offerta_pdf_path(offerta_id, os.path.basename(pdf_path))
        
        flash('Offerta creata con successo!', 'success')
        return redirect(url_for('view_offerta', offerta_id=offerta_id))

@app.route('/offerta/<offerta_id>')
def view_offerta(offerta_id):
    offerta = db.get_offerta(offerta_id)
    if not offerta:
        flash('Offerta non trovata', 'danger')
        return redirect(url_for('index'))
    
    return render_template('vista_offerta.html', offerta=offerta)

@app.route('/offerta/<offerta_id>/modifica', methods=['GET', 'POST'])
def edit_offerta(offerta_id):
    offerta = db.get_offerta(offerta_id)
    if not offerta:
        flash('Offerta non trovata', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'GET':
        return render_template('nuova_offerta.html', offerta=offerta, is_edit=True)
    
    elif request.method == 'POST':
        # Implementazione simile a nuova_offerta ma aggiorna un'offerta esistente
        # [Codice per l'aggiornamento]
        
        flash('Offerta aggiornata con successo!', 'success')
        return redirect(url_for('view_offerta', offerta_id=offerta_id))

@app.route('/offerta/<offerta_id>/pdf')
def download_pdf(offerta_id):
    offerta = db.get_offerta(offerta_id)
    if not offerta or not offerta.get('pdf_path'):
        flash('PDF non trovato', 'danger')
        return redirect(url_for('view_offerta', offerta_id=offerta_id))
    
    pdf_path = os.path.join(app.config['DATA_FOLDER'], offerta['customer'].upper(), 
                           offerta['offer_number'], offerta['pdf_path'])
    
    return send_file(pdf_path, as_attachment=True)

@app.route('/offerta/<offerta_id>/elimina', methods=['POST'])
def delete_offerta(offerta_id):
    if db.delete_offerta(offerta_id):
        flash('Offerta eliminata con successo', 'success')
    else:
        flash('Errore durante l\'eliminazione dell\'offerta', 'danger')
    
    return redirect(url_for('index'))

@app.route('/api/next-offer-number', methods=['GET'])
def api_next_offer_number():
    next_number = db.get_next_offer_number()
    return jsonify({'next_number': next_number})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)