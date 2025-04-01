# app.py
from flask import Flask, render_template, request, jsonify
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from sympy import symbols, sympify, lambdify
import re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html',css="style")

@app.route('/solve', methods=['POST'])
def solve():
    try:
        data = request.form
        
        # Get form data
        ode_str = data.get('ode')
        order = int(data.get('order'))
        x_start = float(data.get('x_start'))
        x_end = float(data.get('x_end'))
        method = data.get('method')
        
        # Get boundary conditions
        boundary_conditions = []
        for i in range(order):
            bc_type = data.get(f'bc{i}_type')
            bc_point = float(data.get(f'bc{i}_point'))
            bc_value = float(data.get(f'bc{i}_value'))
            boundary_conditions.append({'type': bc_type, 'point': bc_point, 'value': bc_value})
        
        # Get method-specific parameters
        if method == 'finite_difference':
            n_points = int(data.get('n_points'))
            solution, x_values = solve_finite_difference(ode_str, order, x_start, x_end, n_points, boundary_conditions)
        else:  # shooting method
            tol = float(data.get('tol'))
            max_iter = int(data.get('max_iter'))
            solution, x_values = solve_shooting(ode_str, order, x_start, x_end, boundary_conditions, tol, max_iter)
        
        # Generate plot
        plt.figure(figsize=(10, 6))
        plt.plot(x_values, solution, 'b-')
        plt.grid(True)
        plt.xlabel('x')
        plt.ylabel('y')
        plt.title(f'Solution using {method.replace("_", " ").title()} Method')
        
        # Convert plot to base64 for displaying in browser
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        return jsonify({
            'status': 'success',
            'plot': plot_data,
            'x_values': x_values.tolist(),
            'y_values': solution.tolist()
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def parse_ode(ode_str, order):
    """Parse the ODE string into a function."""
    # Replace y', y'', etc. with y[1], y[2], etc.
    for i in range(order, 0, -1):
        derivative = "y" + "'"*i
        ode_str = ode_str.replace(derivative, f"y[{i}]")
    
    ode_str = ode_str.replace("y", "y[0]")
    
    # Create symbols
    x, y0, y1, y2, y3, y4 = symbols('x y[0] y[1] y[2] y[3] y[4]')
    
    # Parse the expression
    expr = sympify(ode_str)
    
    # Create a lambda function
    func = lambdify((x, y0, y1, y2, y3, y4), expr)
    
    def ode_func(x, y_vector):
        # For first-order system, y_vector contains [y, y', y'', ...] 
        # We need to compute the highest derivative
        
        # Initialize array for derivatives
        derivatives = np.zeros(order)
        
        # For a system of ODEs, derivatives[0] = y', derivatives[1] = y'', etc.
        for i in range(order-1):
            derivatives[i] = y_vector[i+1]
        
        # Compute the highest derivative using the parsed function
        y_args = [y_vector[i] for i in range(min(5, order))]
        while len(y_args) < 5:
            y_args.append(0)  # Pad with zeros if order < 5
            
        derivatives[-1] = func(x, *y_args)
        
        return derivatives
    
    return ode_func

def solve_finite_difference(ode_str, order, x_start, x_end, n_points, boundary_conditions):
    """Solve ODE using finite difference method."""
    if order != 2:
        raise ValueError("Finite difference implementation currently supports only 2nd order ODEs")
    
    # Extract and process the differential equation: y'' = f(x, y, y')
    def extract_rhs(ode_str):
        # Find everything after the equals sign
        match = re.search(r'=\s*(.*)', ode_str)
        if match:
            return match.group(1).strip()
        return ode_str  # If no equals sign, assume the RHS directly
    
    rhs_str = extract_rhs(ode_str)
    
    # Set up the mesh
    h = (x_end - x_start) / (n_points - 1)
    x = np.linspace(x_start, x_end, n_points)
    
    # Initialize coefficient matrices for the system Ay = b
    A = np.zeros((n_points, n_points))
    b = np.zeros(n_points)
    
    # Parse the RHS of the ODE
    x_sym, y_sym, yp_sym = symbols('x y y\'')
    rhs_expr = sympify(rhs_str)
    rhs_func = lambdify((x_sym, y_sym, yp_sym), rhs_expr)
    
    # Apply boundary conditions
    left_bc = next((bc for bc in boundary_conditions if bc['point'] == x_start), None)
    right_bc = next((bc for bc in boundary_conditions if bc['point'] == x_end), None)
    
    if not (left_bc and right_bc):
        raise ValueError("Boundary conditions must be specified at both endpoints")
    
    # Set up boundary conditions
    A[0, 0] = 1
    b[0] = left_bc['value']
    
    A[-1, -1] = 1
    b[-1] = right_bc['value']
    
    # Set up the finite difference equation for interior points
    # Use the approximation: y''(x) ≈ (y(x+h) - 2y(x) + y(x-h))/h²
    for i in range(1, n_points-1):
        A[i, i-1] = 1
        A[i, i] = -2
        A[i, i+1] = 1
        
        # For a general 2nd order ODE: y'' = f(x, y, y')
        # We use a central difference for y': (y(x+h) - y(x-h))/(2h)
        # This is a simplification and may need iteration for accuracy
        b[i] = h**2 * rhs_func(x[i], 0, 0)  # Initial guess
    
    # Solve the linear system
    y = np.linalg.solve(A, b)
    
    # Refine solution through iteration (for non-linear terms)
    for _ in range(5):  # A few iterations for better accuracy
        for i in range(1, n_points-1):
            y_prime_approx = (y[i+1] - y[i-1]) / (2*h)
            b[i] = h**2 * rhs_func(x[i], y[i], y_prime_approx)
        
        y = np.linalg.solve(A, b)
    
    return y, x

def solve_shooting(ode_str, order, x_start, x_end, boundary_conditions, tol=1e-6, max_iter=50):
    """Solve ODE using shooting method."""
    if order != 2:
        raise ValueError("Shooting method implementation currently supports only 2nd order ODEs")
    
    # Get boundary conditions
    left_bc = next((bc for bc in boundary_conditions if bc['point'] == x_start), None)
    right_bc = next((bc for bc in boundary_conditions if bc['point'] == x_end), None)
    
    if not (left_bc and right_bc):
        raise ValueError("Boundary conditions must be specified at both endpoints")
    
    # Create ODE function
    ode_func = parse_ode(ode_str, order)
    
    # Define the shooting method
    def shoot(guess):
        # Initial conditions
        y0 = np.zeros(order)
        y0[0] = left_bc['value']
        y0[1] = guess  # guessed derivative
        
        # Solve initial value problem
        sol = solve_ivp(
            lambda t, y: ode_func(t, y), 
            [x_start, x_end], 
            y0, 
            method='RK45', 
            t_eval=np.linspace(x_start, x_end, 100),
            rtol=1e-6
        )
        
        return sol.y[0, -1] - right_bc['value']  # Error at right boundary
    
    # Use bisection method to find the correct initial derivative
    # Initial guesses
    guess_low = -100.0
    guess_high = 100.0
    
    # Check if the solution is in the range
    f_low = shoot(guess_low)
    f_high = shoot(guess_high)
    
    if f_low * f_high > 0:
        # Try wider range
        guess_low = -1000.0
        guess_high = 1000.0
        f_low = shoot(guess_low)
        f_high = shoot(guess_high)
        
        if f_low * f_high > 0:
            raise ValueError("Could not bracket the solution. Try different initial guesses.")
    
    # Bisection loop
    guess = (guess_low + guess_high) / 2
    iter_count = 0
    
    while abs(f_high - f_low) > tol and iter_count < max_iter:
        guess = (guess_low + guess_high) / 2
        f_guess = shoot(guess)
        
        if f_guess == 0:
            break
        
        if f_guess * f_low < 0:
            guess_high = guess
            f_high = f_guess
        else:
            guess_low = guess
            f_low = f_guess
        
        iter_count += 1
    
    # Solve with the final guess
    y0 = np.zeros(order)
    y0[0] = left_bc['value']
    y0[1] = guess
    
    sol = solve_ivp(
        lambda t, y: ode_func(t, y), 
        [x_start, x_end], 
        y0, 
        method='RK45', 
        t_eval=np.linspace(x_start, x_end, 100),
        rtol=1e-6
    )
    
    return sol.y[0], sol.t


@app.route('/documentation')
def documentation():
    return render_template('documentation.html',css="documentaton")


if __name__ == '__main__':
    app.run(debug=True)