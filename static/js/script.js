// static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    // Method selection toggle
    const methodSelect = document.getElementById('method');
    const finiteDifferenceParams = document.getElementById('finite-difference-params');
    const shootingParams = document.getElementById('shooting-params');
    
    methodSelect.addEventListener('change', function() {
        if (this.value === 'finite_difference') {
            finiteDifferenceParams.style.display = 'block';
            shootingParams.style.display = 'none';
        } else {
            finiteDifferenceParams.style.display = 'none';
            shootingParams.style.display = 'block';
        }
    });
    
    // Handle form submission
    const odeForm = document.getElementById('ode-form');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultsDiv = document.getElementById('results');
    const errorMessage = document.getElementById('error-message');
    
    odeForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Form validation
        if (!odeForm.checkValidity()) {
            e.stopPropagation();
            odeForm.classList.add('was-validated');
            return;
        }
        
        // Show loading indicator
        loadingIndicator.style.display = 'block';
        resultsDiv.style.display = 'none';
        errorMessage.style.display = 'none';
        
        // Get form data
        const formData = new FormData(odeForm);
        
        // Append ODE string (add "y'' = " if not already included)
        let odeValue = formData.get('ode');
        if (!odeValue.includes('=')) {
            formData.set('ode', "y'' = " + odeValue);
        }
        
        // AJAX request
        fetch('/solve', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingIndicator.style.display = 'none';
            
            if (data.status === 'success') {
                // Display the results
                document.getElementById('solution-plot').src = 'data:image/png;base64,' + data.plot;
                
                // Populate the solution table
                const tableBody = document.getElementById('solution-table').getElementsByTagName('tbody')[0];
                tableBody.innerHTML = '';
                
                // Only show a subset of points to avoid overwhelming the table
                const displayStep = Math.max(1, Math.floor(data.x_values.length / 100));
                
                for (let i = 0; i < data.x_values.length; i += displayStep) {
                    const row = tableBody.insertRow();
                    const xCell = row.insertCell(0);
                    const yCell = row.insertCell(1);
                    
                    xCell.textContent = data.x_values[i].toFixed(6);
                    yCell.textContent = data.y_values[i].toFixed(6);
                }
                
                // Enable CSV download
                document.getElementById('download-csv').onclick = function() {
                    downloadCSV(data.x_values, data.y_values);
                };
                
                resultsDiv.style.display = 'block';
                
                // Scroll to results
                resultsDiv.scrollIntoView({ behavior: 'smooth' });
            } else {
                // Show error message
                errorMessage.textContent = data.message;
                errorMessage.style.display = 'block';
            }
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            errorMessage.textContent = 'An error occurred: ' + error.message;
            errorMessage.style.display = 'block';
        });
    });
    
    // Function to download solution as CSV
    function downloadCSV(xValues, yValues) {
        let csvContent = 'x,y\n';
        
        for (let i = 0; i < xValues.length; i++) {
            csvContent += xValues[i] + ',' + yValues[i] + '\n';
        }
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', 'ode_solution.csv');
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    // Handle example problem clicks
    const exampleProblems = document.querySelectorAll('.example-problem');
    
    exampleProblems.forEach(problem => {
        problem.addEventListener('click', function() {
            // Set form values from data attributes
            document.getElementById('ode').value = this.dataset.ode;
            document.getElementById('order').value = this.dataset.order;
            document.getElementById('x_start').value = this.dataset.xStart;
            document.getElementById('x_end').value = this.dataset.xEnd;
            
            // Set boundary conditions
            document.querySelector('[name="bc0_type"]').value = this.dataset.bc0Type;
            document.querySelector('[name="bc0_point"]').value = this.dataset.bc0Point;
            document.querySelector('[name="bc0_value"]').value = this.dataset.bc0Value;
            
            document.querySelector('[name="bc1_type"]').value = this.dataset.bc1Type;
            document.querySelector('[name="bc1_point"]').value = this.dataset.bc1Point;
            document.querySelector('[name="bc1_value"]').value = this.dataset.bc1Value;
            
            // Set method
            const methodValue = this.dataset.method;
            document.getElementById('method').value = methodValue;
            
            // Trigger change event to update UI
            const event = new Event('change');
            document.getElementById('method').dispatchEvent(event);
            
            // Set method-specific parameters
            if (methodValue === 'finite_difference') {
                document.getElementById('n_points').value = this.dataset.nPoints;
            } else {
                document.getElementById('tol').value = this.dataset.tol;
                document.getElementById('max_iter').value = this.dataset.maxIter;
            }
            
            // Scroll to form
            odeForm.scrollIntoView({ behavior: 'smooth' });
        });
    });
    
    // Initialize MathJax
    if (typeof MathJax !== 'undefined') {
        MathJax.Hub.Queue(['Typeset', MathJax.Hub]);
    }
    
    // Form validation
    (function() {
        'use strict';
        
        const forms = document.querySelectorAll('.needs-validation');
        
        Array.prototype.slice.call(forms).forEach(function(form) {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                
                form.classList.add('was-validated');
            }, false);
        });
    })();
    
    // Ensure boundary conditions are at endpoints
    const x_start = document.getElementById('x_start');
    const x_end = document.getElementById('x_end');
    const bc0_point = document.querySelector('[name="bc0_point"]');
    const bc1_point = document.querySelector('[name="bc1_point"]');
    
    x_start.addEventListener('change', function() {
        bc0_point.value = this.value;
    });
    
    x_end.addEventListener('change', function() {
        bc1_point.value = this.value;
    });
    
    // Update UI based on initial method selection
    methodSelect.dispatchEvent(new Event('change'));
});