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
    try:
        if request.method == 'GET':
            # Genera un nuovo numero di offerta per il form
            next_number = db.get_next_offer_number()
            return render_template('nuova_offerta.html', next_number=next_number)
        
        elif request.method == 'POST':
            # Crea un dizionario per la nuova offerta (NON un'istanza di Offerta)
            data = {
                'date': request.form.get('date'),
                'customer': request.form.get('customer'),
                'customer_email': request.form.get('customer_email'),
                'address': request.form.get('address'),
                'offer_description': request.form.get('offer_description'),
                'offer_number': request.form.get('offer_number'),
                'tabs': []  # Inizializza tabs come lista vuota
            }
            
            # Processa i tab del form
            tab_count = int(request.form.get('tab_count', 0))
            print(f"DEBUG: Trovati {tab_count} tabs nel form")
            
            # Debug - stampa tutti i campi del form che iniziano con tab_type
            tab_types = [key for key in request.form if key.startswith('tab_type_')]
            print(f"DEBUG: Tab types trovati nel form: {tab_types}")
            
            for i in range(tab_count):
                tab_type = request.form.get(f'tab_type_{i}')
                print(f"DEBUG: Processing tab {i}, type: {tab_type}")
                
                if tab_type == 'single_product':
                    # Gestione caricamento immagine
                    product_image = request.files.get(f'product_image_{i}')
                    image_path = ''
                    
                    if product_image and product_image.filename and allowed_file(product_image.filename):
                        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{product_image.filename}")
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        product_image.save(file_path)
                        image_path = '/static/uploads/' + filename
                    
                    # Crea il dizionario per il tab single_product
                    single_product_tab = {
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
                    }
                    
                    # Aggiungi il tab all'array tabs
                    data['tabs'].append(single_product_tab)
                    print(f"DEBUG: Added single product: {single_product_tab['product_name']}")
                
                elif tab_type == 'multi_product':
                    # Crea il dizionario per il tab multi_product
                    products = []
                    product_count = int(request.form.get(f'product_count_{i}', 0))
                    print(f"DEBUG: Tab {i} has {product_count} products")
                    
                    for j in range(product_count):
                        # Crea l'array per ogni prodotto
                        product = [
                            request.form.get(f'product_name_{i}_{j}'),
                            request.form.get(f'product_model_{i}_{j}'),
                            request.form.get(f'product_price_{i}_{j}'),
                            request.form.get(f'product_quantity_{i}_{j}'),
                            request.form.get(f'product_description_{i}_{j}')
                        ]
                        products.append(product)
                        print(f"DEBUG: Added product {j}: {product[0]}")
                    
                    multi_product_tab = {
                        'type': 'multi_product',
                        'max_items_per_page': int(request.form.get(f'max_items_per_page_{i}', 3)),
                        'products': products
                    }
                    
                    # Aggiungi il tab all'array tabs
                    data['tabs'].append(multi_product_tab)
                    print(f"DEBUG: Added multi-product tab with {len(products)} products")
            
            print(f"DEBUG: Data before save: tabs count = {len(data['tabs'])}")
            print(f"DEBUG: Data structure: {data}")
            
            # Salva direttamente il dizionario (NON convertirlo in Offerta)
            offerta_id = db.save_offerta(data)
            
            # Verifica che l'offerta sia stata salvata correttamente
            offerta = db.get_offerta(offerta_id)
            print(f"DEBUG: Retrieved offerta: tabs = {len(offerta.get('tabs', []))}")
            
            # Genera il PDF
            pdf_path = generate_pdf(offerta, app.root_path)
            db.update_offerta_pdf_path(offerta_id, os.path.basename(pdf_path))
            
            flash('Offerta creata con successo!', 'success alert-permanent')
            return redirect(url_for('view_offerta', offerta_id=offerta_id))
        
        return redirect(url_for('index'))
    
    except Exception as e:
        import traceback
        print(f"ERROR in nuova_offerta: {e}")
        print(traceback.format_exc())
        flash(f'Si è verificato un errore: {str(e)}', 'danger alert-permanent')
        return redirect(url_for('index'))

# Aggiungere questa funzione di utility per l'endpoint di debug
@app.route('/offerta/<offerta_id>/json')
def debug_offerta_json(offerta_id):
    """Endpoint di debug che mostra il JSON dell'offerta"""
    try:
        offerta = db.get_offerta(offerta_id)
        if not offerta:
            return jsonify({"error": "Offerta non trovata"}), 404
        return jsonify(offerta)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/offerta/<offerta_id>')
def view_offerta(offerta_id):
    try:
        # Ottieni l'offerta dal database
        offerta_data = db.get_offerta(offerta_id)
        if not offerta_data:
            flash('Offerta non trovata', 'danger')
            return redirect(url_for('index'))
        
        # Assicurati che offerta_data sia un dizionario con tabs
        if not isinstance(offerta_data, dict):
            offerta_data = offerta_data.to_dict() if hasattr(offerta_data, 'to_dict') else {'id': offerta_id, 'tabs': []}
        
        # Assicurati che ci sia la chiave 'tabs'
        if 'tabs' not in offerta_data or not isinstance(offerta_data['tabs'], list):
            offerta_data['tabs'] = []
        
        # Debug: stampiamo cosa contiene l'offerta
        print(f"DEBUG view_offerta: ID={offerta_id}, tabs={len(offerta_data['tabs'])}")
        
        return render_template('vista_offerta.html', offerta=offerta_data)
    except Exception as e:
        import traceback
        print(f"Errore in view_offerta: {e}")
        print(traceback.format_exc())
        flash(f'Errore nel caricamento dell\'offerta: {str(e)}', 'danger')
        return redirect(url_for('index'))

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
        data = {
            'date': request.form.get('date'),
            'customer': request.form.get('customer'),
            'customer_email': request.form.get('customer_email'),
            'address': request.form.get('address'),
            'offer_description': request.form.get('offer_description'),
            'offer_number': request.form.get('offer_number'),
            'tabs': []
        }
    
    tab_count = int(request.form.get('tab_count', 0))
    
    for i in range(tab_count):
        tab_type = request.form.get(f'tab_type_{i}')
        
        if tab_type == 'single_product':
            # Gestione caricamento immagine
            product_image = request.files.get(f'product_image_{i}')
            image_path = request.form.get(f'existing_image_{i}', '')
            
            if product_image and allowed_file(product_image.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{product_image.filename}")
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                product_image.save(image_path)
                image_path = '/static/uploads/' + filename
            
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
    
    # Mantieni il percorso PDF esistente se presente
    offerta_attuale = db.get_offerta(offerta_id)
    if offerta_attuale and 'pdf_path' in offerta_attuale:
        data['pdf_path'] = offerta_attuale['pdf_path']
    
    # Aggiorna l'offerta
    if db.update_offerta(offerta_id, data):
        # Rigenera il PDF
        offerta = db.get_offerta(offerta_id)
        pdf_path = generate_pdf(offerta, app.root_path)
        db.update_offerta_pdf_path(offerta_id, os.path.basename(pdf_path))
        
        flash('Offerta aggiornata con successo!', 'success')
    else:
        flash('Errore durante l\'aggiornamento dell\'offerta', 'danger')
    
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