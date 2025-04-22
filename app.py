from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import os
import json
import uuid
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
from utils.pdf_generator import generate_pdf

app = Flask(__name__)
app.secret_key = 'valtservice_secret_key'  # Cambiare in produzione
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['DATA_FOLDER'] = os.path.join(app.root_path, 'data')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# Inizializzazione delle cartelle necessarie
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Controlla se l'estensione del file è consentita"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.context_processor
def inject_now():
    """Inietta la data attuale nei template"""
    return {'now': datetime.now()}

def get_next_offer_number():
    """Genera il prossimo numero di offerta nel formato YYYY-XXXX"""
    counter_file = os.path.join(app.config['DATA_FOLDER'], "counter.json")
    
    # Inizializza il contatore se non esiste
    if not os.path.exists(counter_file):
        current_year = str(datetime.now().year)
        counter = {current_year: 0}
        with open(counter_file, 'w') as f:
            json.dump(counter, f)
    
    # Carica il contatore
    with open(counter_file, 'r') as f:
        counter = json.load(f)
    
    current_year = str(datetime.now().year)
    if current_year not in counter:
        counter[current_year] = 0
    
    counter[current_year] += 1
    
    # Salva il contatore aggiornato
    with open(counter_file, 'w') as f:
        json.dump(counter, f)
    
    return f"{current_year}-{counter[current_year]:04d}"

def update_offerte_index(data, data_folder):
    """Aggiorna il file di indice delle offerte"""
    try:
        index_file = os.path.join(data_folder, "offerte_index.json")
        
        # Carica l'indice esistente
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = []
        
        # Verifica se l'offerta è già presente nell'indice
        for i, entry in enumerate(index):
            if entry.get('id') == data['id']:
                # Aggiorna la voce esistente
                index[i] = {
                    'id': data['id'],
                    'offer_number': data['offer_number'],
                    'date': data['date'],
                    'customer': data['customer'],
                    'customer_email': data['customer_email'],
                    'description': data['offer_description'][:100] + '...' if len(data['offer_description']) > 100 else data['offer_description']
                }
                break
        else:
            # Aggiungi una nuova voce
            index.append({
                'id': data['id'],
                'offer_number': data['offer_number'],
                'date': data['date'],
                'customer': data['customer'],
                'customer_email': data['customer_email'],
                'description': data['offer_description'][:100] + '...' if len(data['offer_description']) > 100 else data['offer_description']
            })
        
        # Salva l'indice aggiornato
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=4, ensure_ascii=False)
        
        print(f"DEBUG: Indice offerte aggiornato con successo")
        
    except Exception as e:
        print(f"ERRORE nell'aggiornamento dell'indice: {e}")

def get_offerta_direct(offerta_id, data_folder):
    """Ottiene direttamente un'offerta dal file JSON usando l'ID"""
    try:
        # Carica l'indice
        index_file = os.path.join(data_folder, "offerte_index.json")
        if not os.path.exists(index_file):
            print(f"ERRORE: File indice non trovato: {index_file}")
            return None
            
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
            
        # Trova l'offerta nell'indice
        for entry in index:
            if entry.get('id') == offerta_id:
                # Costruisci il percorso del file JSON
                customer_folder = os.path.join(data_folder, entry['customer'].upper())
                offer_folder = os.path.join(customer_folder, entry['offer_number'])
                json_path = os.path.join(offer_folder, "dati_offerta.json")
                
                if not os.path.exists(json_path):
                    print(f"ERRORE: File JSON non trovato: {json_path}")
                    return None
                    
                # Carica i dati completi
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Assicurati che tabs esista
                if 'tabs' not in data or not isinstance(data['tabs'], list):
                    data['tabs'] = []
                    
                print(f"DEBUG get_offerta_direct: Caricata offerta con {len(data['tabs'])} tab")
                return data
                
        print(f"ERRORE: Offerta con ID {offerta_id} non trovata nell'indice")
        return None
        
    except Exception as e:
        print(f"ERRORE in get_offerta_direct: {e}")
        return None

def get_all_offerte():
    """Restituisce tutte le offerte dall'indice"""
    index_file = os.path.join(app.config['DATA_FOLDER'], "offerte_index.json")
    try:
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"ERRORE nel caricamento dell'indice: {e}")
    return []

@app.route('/')
def index():
    offerte = get_all_offerte()
    return render_template('index.html', offerte=offerte)

@app.route('/nuova-offerta', methods=['GET', 'POST'])
def nuova_offerta():
    try:
        if request.method == 'GET':
            # Genera un nuovo numero di offerta per il form
            next_number = get_next_offer_number()
            today_date = datetime.now().strftime('%Y-%m-%d')
            return render_template('nuova_offerta.html', next_number=next_number, today_date=today_date)
        
        elif request.method == 'POST':
            # Stampa tutte le chiavi del form per debug
            form_keys = list(request.form.keys())
            print(f"DEBUG: Form contiene {len(form_keys)} campi")
            print(f"DEBUG: Alcuni campi del form: {form_keys[:10]}")
            
            # Raccogli tutti i campi tab_type
            tab_types = {k: v for k, v in request.form.items() if k.startswith('tab_type_')}
            print(f"DEBUG: Trovati {len(tab_types)} tab_type: {tab_types}")
            
            # Crea un dizionario per la nuova offerta
            data = {
                'date': request.form.get('date'),
                'customer': request.form.get('customer'),
                'customer_email': request.form.get('customer_email'),
                'address': request.form.get('address'),
                'offer_description': request.form.get('offer_description'),
                'offer_number': request.form.get('offer_number'),
                'id': str(uuid.uuid4()),
                'tabs': []
            }
            
            # Elabora tutti i tab basandosi sui campi tab_type trovati
            for tab_key, tab_type in tab_types.items():
                tab_index = tab_key.replace('tab_type_', '')
                print(f"DEBUG: Elaborazione tab {tab_index}, tipo: {tab_type}")
                
                if tab_type == 'single_product':
                    # Gestione caricamento immagine
                    product_image = request.files.get(f'product_image_{tab_index}')
                    image_path = ''
                    
                    if product_image and product_image.filename and allowed_file(product_image.filename):
                        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{product_image.filename}")
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        product_image.save(file_path)
                        image_path = '/static/uploads/' + filename
                    
                    # Crea il dizionario per il tab prodotto singolo
                    single_product_tab = {
                        'type': 'single_product',
                        'product_code': request.form.get(f'product_code_{tab_index}'),
                        'product_name': request.form.get(f'product_name_{tab_index}'),
                        'quantity': request.form.get(f'quantity_{tab_index}'),
                        'unit_price': request.form.get(f'unit_price_{tab_index}'),
                        'description': request.form.get(f'description_{tab_index}'),
                        'discount': request.form.get(f'discount_{tab_index}', '0'),
                        'discount_flag': request.form.get(f'discount_flag_{tab_index}') == 'on',
                        'power_w': request.form.get(f'power_w_{tab_index}'),
                        'volts': request.form.get(f'volts_{tab_index}'),
                        'size': request.form.get(f'size_{tab_index}'),
                        'posizione': request.form.get(f'posizione_{tab_index}'),
                        'product_image_path': image_path
                    }
                    
                    data['tabs'].append(single_product_tab)
                    print(f"DEBUG: Aggiunto prodotto singolo: {single_product_tab['product_name']}")
                
                elif tab_type == 'multi_product':
                    # Ottieni il numero di prodotti in questo tab
                    product_count = int(request.form.get(f'product_count_{tab_index}', 0))
                    print(f"DEBUG: Tab multiprodotto {tab_index} ha {product_count} prodotti")
                    
                    products = []
                    for j in range(product_count):
                        product = [
                            request.form.get(f'product_name_{tab_index}_{j}'),
                            request.form.get(f'product_model_{tab_index}_{j}'),
                            request.form.get(f'product_price_{tab_index}_{j}'),
                            request.form.get(f'product_quantity_{tab_index}_{j}'),
                            request.form.get(f'product_description_{tab_index}_{j}')
                        ]
                        products.append(product)
                    
                    multi_product_tab = {
                        'type': 'multi_product',
                        'max_items_per_page': int(request.form.get(f'max_items_per_page_{tab_index}', 3)),
                        'products': products
                    }
                    
                    data['tabs'].append(multi_product_tab)
                    print(f"DEBUG: Aggiunto tab multiprodotto con {len(products)} prodotti")
            
            print(f"DEBUG: Dati finali contengono {len(data['tabs'])} tab")
            
            # Salva direttamente i dati in un file JSON
            customer_folder = os.path.join(app.config['DATA_FOLDER'], data['customer'].upper())
            offer_folder = os.path.join(customer_folder, data['offer_number'])
            os.makedirs(offer_folder, exist_ok=True)
            
            json_path = os.path.join(offer_folder, "dati_offerta.json")
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print(f"DEBUG: JSON salvato con successo in {json_path}")
            
            # Aggiorna indice offerte
            update_offerte_index(data, app.config['DATA_FOLDER'])
            
            # Genera il PDF
            pdf_path = generate_pdf(data, app.root_path)
            
            # Aggiorna il percorso del PDF
            data['pdf_path'] = os.path.basename(pdf_path)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            flash('Offerta creata con successo!', 'success alert-permanent')
            return redirect(url_for('view_offerta', offerta_id=data['id']))
        
        return redirect(url_for('index'))
    
    except Exception as e:
        import traceback
        print(f"ERRORE in nuova_offerta: {e}")
        print(traceback.format_exc())
        flash(f'Si è verificato un errore: {str(e)}', 'danger alert-permanent')
        return redirect(url_for('index'))

@app.route('/offerta/<offerta_id>/json')
def debug_offerta_json(offerta_id):
    """Endpoint di debug che mostra il JSON dell'offerta"""
    try:
        offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
        if not offerta:
            return jsonify({"error": "Offerta non trovata"}), 404
        return jsonify(offerta)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/offerta/<offerta_id>')
def view_offerta(offerta_id):
    try:
        # Ottieni l'offerta direttamente dal file JSON
        offerta_data = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
        
        if not offerta_data:
            flash('Offerta non trovata', 'danger')
            return redirect(url_for('index'))
        
        # Debug info
        print(f"DEBUG view_offerta: ID={offerta_id}, tabs={len(offerta_data.get('tabs', []))}")
        
        return render_template('vista_offerta.html', offerta=offerta_data)
    except Exception as e:
        import traceback
        print(f"Errore in view_offerta: {e}")
        print(traceback.format_exc())
        flash(f'Errore nel caricamento dell\'offerta: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/offerta/<offerta_id>/modifica', methods=['GET', 'POST'])
def edit_offerta(offerta_id):
    try:
        if request.method == 'GET':
            # Ottieni l'offerta direttamente dal file JSON
            offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
            if not offerta:
                flash('Offerta non trovata', 'danger')
                return redirect(url_for('index'))
                
            return render_template('nuova_offerta.html', offerta=offerta, is_edit=True, today_date=datetime.now().strftime('%Y-%m-%d'))
            
        elif request.method == 'POST':
            # Stesso approccio di nuova_offerta, ma manteniamo l'ID originale
            # Ottieni prima i dati dell'offerta esistente
            original_offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
            if not original_offerta:
                flash('Offerta non trovata', 'danger')
                return redirect(url_for('index'))
            
            # Raccogli tutti i campi tab_type
            tab_types = {k: v for k, v in request.form.items() if k.startswith('tab_type_')}
            print(f"DEBUG edit: Trovati {len(tab_types)} tab_type: {tab_types}")
            
            # Aggiorna i dati dell'offerta
            data = {
                'date': request.form.get('date'),
                'customer': request.form.get('customer'),
                'customer_email': request.form.get('customer_email'),
                'address': request.form.get('address'),
                'offer_description': request.form.get('offer_description'),
                'offer_number': request.form.get('offer_number'),
                'id': offerta_id,  # Mantieni l'ID originale
                'tabs': []
            }
            
            # Elabora tutti i tab basandosi sui campi tab_type trovati
            for tab_key, tab_type in tab_types.items():
                tab_index = tab_key.replace('tab_type_', '')
                
                if tab_type == 'single_product':
                    # Gestione caricamento immagine
                    product_image = request.files.get(f'product_image_{tab_index}')
                    image_path = request.form.get(f'existing_image_{tab_index}', '')
                    
                    if product_image and product_image.filename and allowed_file(product_image.filename):
                        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{product_image.filename}")
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        product_image.save(file_path)
                        image_path = '/static/uploads/' + filename
                    
                    # Crea il dizionario per il tab prodotto singolo
                    single_product_tab = {
                        'type': 'single_product',
                        'product_code': request.form.get(f'product_code_{tab_index}'),
                        'product_name': request.form.get(f'product_name_{tab_index}'),
                        'quantity': request.form.get(f'quantity_{tab_index}'),
                        'unit_price': request.form.get(f'unit_price_{tab_index}'),
                        'description': request.form.get(f'description_{tab_index}'),
                        'discount': request.form.get(f'discount_{tab_index}', '0'),
                        'discount_flag': request.form.get(f'discount_flag_{tab_index}') == 'on',
                        'power_w': request.form.get(f'power_w_{tab_index}'),
                        'volts': request.form.get(f'volts_{tab_index}'),
                        'size': request.form.get(f'size_{tab_index}'),
                        'posizione': request.form.get(f'posizione_{tab_index}'),
                        'product_image_path': image_path
                    }
                    
                    data['tabs'].append(single_product_tab)
                
                elif tab_type == 'multi_product':
                    # Ottieni il numero di prodotti in questo tab
                    product_count = int(request.form.get(f'product_count_{tab_index}', 0))
                    
                    products = []
                    for j in range(product_count):
                        product = [
                            request.form.get(f'product_name_{tab_index}_{j}'),
                            request.form.get(f'product_model_{tab_index}_{j}'),
                            request.form.get(f'product_price_{tab_index}_{j}'),
                            request.form.get(f'product_quantity_{tab_index}_{j}'),
                            request.form.get(f'product_description_{tab_index}_{j}')
                        ]
                        products.append(product)
                    
                    multi_product_tab = {
                        'type': 'multi_product',
                        'max_items_per_page': int(request.form.get(f'max_items_per_page_{tab_index}', 3)),
                        'products': products
                    }
                    
                    data['tabs'].append(multi_product_tab)
            
            # Mantieni il percorso PDF esistente
            if original_offerta and 'pdf_path' in original_offerta:
                data['pdf_path'] = original_offerta['pdf_path']
            
            # Gestisci il caso in cui il cliente o il numero offerta sono cambiati
            old_customer = original_offerta.get('customer', '').upper()
            old_offer_number = original_offerta.get('offer_number', '')
            
            new_customer = data['customer'].upper()
            new_offer_number = data['offer_number']
            
            old_folder = os.path.join(app.config['DATA_FOLDER'], old_customer, old_offer_number)
            new_folder = os.path.join(app.config['DATA_FOLDER'], new_customer, new_offer_number)
            
            # Crea nuova cartella se necessario
            os.makedirs(os.path.dirname(new_folder), exist_ok=True)
            os.makedirs(new_folder, exist_ok=True)
            
            # Salva i dati aggiornati
            json_path = os.path.join(new_folder, "dati_offerta.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            # Se la posizione è cambiata, copia i file necessari
            if old_folder != new_folder and os.path.exists(old_folder):
                for filename in os.listdir(old_folder):
                    if filename != "dati_offerta.json":  # File JSON già riscritto
                        src_path = os.path.join(old_folder, filename)
                        dst_path = os.path.join(new_folder, filename)
                        shutil.copy2(src_path, dst_path)
                
                # Prova a rimuovere le vecchie cartelle
                try:
                    shutil.rmtree(old_folder)
                    # Se la cartella cliente è vuota, rimuovi anche quella
                    old_customer_folder = os.path.join(app.config['DATA_FOLDER'], old_customer)
                    if os.path.exists(old_customer_folder) and not os.listdir(old_customer_folder):
                        shutil.rmtree(old_customer_folder)
                except:
                    pass  # Ignora errori nella pulizia
            
            # Aggiorna l'indice
            update_offerte_index(data, app.config['DATA_FOLDER'])
            
            # Rigenera il PDF
            pdf_path = generate_pdf(data, app.root_path)
            data['pdf_path'] = os.path.basename(pdf_path)
            
            # Salva di nuovo con il percorso PDF aggiornato
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            flash('Offerta aggiornata con successo!', 'success')
            return redirect(url_for('view_offerta', offerta_id=offerta_id))
            
    except Exception as e:
        import traceback
        print(f"ERRORE in edit_offerta: {e}")
        print(traceback.format_exc())
        flash(f'Si è verificato un errore: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/offerta/<offerta_id>/pdf')
def download_pdf(offerta_id):
    try:
        offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
        if not offerta or not offerta.get('pdf_path'):
            flash('PDF non trovato', 'danger')
            return redirect(url_for('view_offerta', offerta_id=offerta_id))
        
        pdf_path = os.path.join(app.config['DATA_FOLDER'], offerta['customer'].upper(), 
                               offerta['offer_number'], offerta['pdf_path'])
        
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        flash(f'Errore nel download del PDF: {str(e)}', 'danger')
        return redirect(url_for('view_offerta', offerta_id=offerta_id))

@app.route('/offerta/<offerta_id>/elimina', methods=['POST'])
def delete_offerta(offerta_id):
    try:
        offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
        if not offerta:
            flash('Offerta non trovata', 'danger')
            return redirect(url_for('index'))
        
        # Rimuovi dall'indice
        index_file = os.path.join(app.config['DATA_FOLDER'], "offerte_index.json")
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            index = [entry for entry in index if entry.get('id') != offerta_id]
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=4, ensure_ascii=False)
        
        # Rimuovi i file
        customer_folder = os.path.join(app.config['DATA_FOLDER'], offerta['customer'].upper())
        offer_folder = os.path.join(customer_folder, offerta['offer_number'])
        
        if os.path.exists(offer_folder):
            shutil.rmtree(offer_folder)
        
        # Se la cartella cliente è vuota, rimuovi anche quella
        if os.path.exists(customer_folder) and not os.listdir(customer_folder):
            shutil.rmtree(customer_folder)
        
        flash('Offerta eliminata con successo', 'success')
    except Exception as e:
        print(f"ERRORE nell'eliminazione dell'offerta: {e}")
        flash(f'Errore durante l\'eliminazione dell\'offerta: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/api/next-offer-number', methods=['GET'])
def api_next_offer_number():
    next_number = get_next_offer_number()
    return jsonify({'next_number': next_number})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)