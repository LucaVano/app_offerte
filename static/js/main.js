/**
 * Script principale per l'applicazione Generatore Offerte
 */
document.addEventListener('DOMContentLoaded', function() {
    // Inizializza i tooltip Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Chiudi automaticamente gli alert dopo 5 secondi
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var alertInstance = new bootstrap.Alert(alert);
            alertInstance.close();
        });
    }, 5000);

    // Formatta i campi numerici con separatore delle migliaia
    document.querySelectorAll('input[type="number"]').forEach(function(input) {
        input.addEventListener('change', function() {
            var value = parseFloat(this.value);
            if (!isNaN(value)) {
                if (this.step === '0.01' || this.step === 'any') {
                    // Formatta con 2 decimali per i campi monetari
                    this.value = value.toFixed(2);
                } else {
                    // Arrotonda all'intero per gli altri campi
                    this.value = Math.round(value);
                }
            }
        });
    });

    // Gestione dinamica del form per la creazione/modifica dell'offerta
    const offerForm = document.getElementById('offerForm');
    if (offerForm) {
        // Controlla se i campi obbligatori sono compilati prima di inviare il form
        offerForm.addEventListener('submit', function(event) {
            var requiredFields = offerForm.querySelectorAll('[required]');
            var valid = true;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    valid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!valid) {
                event.preventDefault();
                alert('Compila tutti i campi obbligatori prima di continuare.');
                // Scorri fino al primo campo non valido
                var firstInvalid = offerForm.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstInvalid.focus();
                }
            }
        });
        
        // Rimuovi la classe is-invalid quando l'utente modifica il campo
        offerForm.querySelectorAll('.form-control').forEach(function(input) {
            input.addEventListener('input', function() {
                this.classList.remove('is-invalid');
            });
        });
    }

    // Gestione della data corrente per i nuovi form
    const dateInput = document.getElementById('date');
    if (dateInput && !dateInput.value) {
        const today = new Date();
        const year = today.getFullYear();
        let month = today.getMonth() + 1;
        let day = today.getDate();
        
        // Aggiungi zero iniziale se necessario
        month = month < 10 ? '0' + month : month;
        day = day < 10 ? '0' + day : day;
        
        dateInput.value = `${year}-${month}-${day}`;
    }

    // Gestione del campo numero offerta
    const offerNumberInput = document.getElementById('offer_number');
    const updateCounterCheckbox = document.getElementById('update_counter');
    
    if (offerNumberInput && updateCounterCheckbox) {
        // Se l'utente modifica manualmente il numero, attiva il checkbox
        offerNumberInput.addEventListener('input', function() {
            if (this.value.trim() !== '' && this.defaultValue !== this.value) {
                updateCounterCheckbox.checked = true;
            }
        });
    }

    // Aggiorna i totali nella visualizzazione dell'offerta
    function updateTotals() {
        const priceElements = document.querySelectorAll('.product-price');
        const quantityElements = document.querySelectorAll('.product-quantity');
        const totalElements = document.querySelectorAll('.product-total');
        
        let grandTotal = 0;
        
        for (let i = 0; i < priceElements.length; i++) {
            const price = parseFloat(priceElements[i].textContent) || 0;
            const quantity = parseFloat(quantityElements[i].textContent) || 0;
            const total = price * quantity;
            
            if (totalElements[i]) {
                totalElements[i].textContent = total.toFixed(2) + ' €';
            }
            
            grandTotal += total;
        }
        
        const grandTotalElement = document.getElementById('grand-total');
        if (grandTotalElement) {
            grandTotalElement.textContent = grandTotal.toFixed(2) + ' €';
        }
    }
    
    // Chiama updateTotals solo se ci sono elementi price/quantity nella pagina
    if (document.querySelector('.product-price')) {
        updateTotals();
    }
});