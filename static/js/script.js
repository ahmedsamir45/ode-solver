function setSampleEquation(eq) {
    document.getElementById('equation').value = eq;
}

    document.getElementById('odeForm').addEventListener('submit', function(e) {
        const equation = document.getElementById('equation').value.trim();
        const validPattern = /^[\d\s\w\+\-\*\/\^\(\)\.]*$/;
    
        if (!validPattern.test(equation)) {
            alert('Please enter a valid equation using only math symbols like +, -, *, /, ^, and functions like sin, cos.');
            e.preventDefault(); // Stop form from submitting
        }
    });
  
    
$(document).ready(function() {
    $('#odeForm').on('submit', function(e) {
        e.preventDefault();
        
        // Show loading indicator
        $('#loading').show();
        $('#results').hide();
        $('#error-display').hide();
        
        // Get form data
        const formData = new FormData(this);
        
        // Submit form data via AJAX
        $.ajax({
            url: '/solve',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                $('#loading').hide();
                
                if (response.success) {
                    displayResults(response.results);
                } else {
                    $('#error-display').text('Error: ' + response.error).show();
                }
            },
            error: function() {
                $('#loading').hide();
                $('#error-display').text('Server error. Please try again.').show();
            }
        });
    });
    
    function displayResults(results) {
        // Clear previous results
        $('#fd-table-body').empty();
        $('#shooting-table-body').empty();
        $('#fd-plot').empty();
        $('#shooting-plot').empty();
        
        // Display finite difference results
        if (results.finite_difference) {
            const fdData = results.finite_difference;
            
            // Show plot
            $('#fd-plot').html('<img src="data:image/png;base64,' + fdData.plot + '" alt="Finite Difference Solution">');
            
            // Populate table
            fdData.table.forEach(function(row) {
                $('#fd-table-body').append(
                    `<tr>
                        <td>${row.i}</td>
                        <td>${row.x.toFixed(4)}</td>
                        <td>${row.y.toFixed(6)}</td>
                    </tr>`
                );
            });
        }
        
        // Display shooting method results
        if (results.shooting) {
            const shootingData = results.shooting;
            
            // Show plot
            $('#shooting-plot').html('<img src="data:image/png;base64,' + shootingData.plot + '" alt="Shooting Method Solution">');
            
            // Populate table
            shootingData.table.forEach(function(row) {
                $('#shooting-table-body').append(
                    `<tr>
                        <td>${row.i}</td>
                        <td>${row.x.toFixed(4)}</td>
                        <td>${row.y.toFixed(6)}</td>
                    </tr>`
                );
            });
        }
        
        // Show results section
        $('#results').show();
    }
});