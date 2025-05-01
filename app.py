from flask import Flask, render_template, request, jsonify
import numpy as np
import sympy as sp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from scipy.integrate import solve_ivp

app = Flask(__name__)

def parse_equation(equation_str):
    x, y, yp = sp.symbols('x y yp')  # yp for y'
    # Replace y' and y'' correctly
    equation_str = equation_str.replace("y''", 'd2y')
    equation_str = equation_str.replace("y'", 'yp')
    equation_str = equation_str.replace("d2y", 'd2y')  # maintain replacement order

    try:
        equation = sp.sympify(equation_str)
        return equation
    except Exception:
        return None

def equation_to_function(equation_str):
    """Convert equation string to a callable function"""
    x, y, p = sp.symbols('x y p')
    equation = parse_equation(equation_str)
    
    # Convert to lambda function that takes x, y, p
    func = sp.lambdify((x, y, p), equation, 'numpy')
    
    def odefunc(x, Y):
        y, p = Y
        dydt = p
        dpdt = func(x, y, p)
        return [dydt, dpdt]
    
    return odefunc

def finite_difference_method(equation_str, a, b, alpha, beta, bc_type, h):
    x, y = sp.symbols('x y')
    n = int((b - a) / h) + 1
    x_vals = np.linspace(a, b, n)

    # Assume equation is of the form y'' = f(x, y, y')
    # We ignore y' in FD and treat f(x, y) only for simplicity
    # Replace y'' = f(x, y), approximate y'' ≈ (y[i-1] - 2*y[i] + y[i+1]) / h²

    equation = parse_equation(equation_str)
    if equation is None:
        return None, None

    # Convert to a function f(x, y)
    f_func = sp.lambdify((x, y), equation.subs('yp', 0), 'numpy')

    A = np.zeros((n, n))
    B = np.zeros(n)

    for i in range(1, n - 1):
        xi = x_vals[i]
        A[i, i - 1] = 1
        A[i, i] = -2
        A[i, i + 1] = 1
        B[i] = h ** 2 * f_func(xi, 0)  # we don't know y yet, initial approx y=0

    if bc_type == "dirichlet":
        A[0, 0] = 1
        B[0] = alpha
        A[-1, -1] = 1
        B[-1] = beta
    else:  # Neumann at right, Dirichlet at left
        A[0, 0] = 1
        B[0] = alpha
        A[-1, -2] = -1
        A[-1, -1] = 1
        B[-1] = h * beta

    try:
        y_vals = np.linalg.solve(A, B)
        return x_vals, y_vals
    except Exception:
        return None, None

def shooting_method(equation_str, a, b, alpha, beta, bc_type, h):
    x_sym, y_sym, yp_sym = sp.symbols('x y yp')
    equation_str = equation_str.replace("y''", 'd2y')
    equation_str = equation_str.replace("y'", 'yp')
    equation_str = equation_str.replace("d2y", 'd2y')

    try:
        equation = sp.sympify(equation_str)
    except Exception:
        return None, None

    # Build RHS of the second-order ODE as a system of two first-order ODEs
    f_expr = equation.subs('yp', yp_sym)
    f = sp.lambdify((x_sym, y_sym, yp_sym), f_expr, 'numpy')

    def system(x, Y):
        y1, y2 = Y  # y1 = y, y2 = y'
        return [y2, f(x, y1, y2)]

    def solve_for_guess(guess):
        sol = solve_ivp(system, (a, b), [alpha, guess], t_eval=np.arange(a, b + h, h))
        return sol.y[0, -1] - beta  # mismatch at x=b

    from scipy.optimize import root_scalar

    # Bracket the root for initial guesses
    try:
        sol = root_scalar(solve_for_guess, bracket=[-100, 100], method='bisect', xtol=1e-6)
    except ValueError:
        return None, None

    if not sol.converged:
        return None, None

    # Final solution with best initial derivative
    s = sol.root
    final_sol = solve_ivp(system, (a, b), [alpha, s], t_eval=np.arange(a, b + h, h))

    return final_sol.t, final_sol.y[0]

def create_plot(x, y, method_name):
    """Create a plot of the solution"""
    plt.figure(figsize=(10, 6))
    plt.plot(x, y, 'b-', linewidth=2)
    plt.scatter(x, y, color='red', s=20)
    plt.grid(True)
    plt.xlabel('x')
    plt.ylabel('y(x)')
    plt.title(f'Solution using {method_name}')
    
    # Convert plot to PNG image
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()
    
    return plot_url

@app.route('/')
def index():
    return render_template('index.html',css="style")

@app.route('/solve', methods=['POST'])
def solve():
    try:
        # Get form data
        equation = request.form.get('equation')
        a = float(request.form.get('a'))
        b = float(request.form.get('b'))
        alpha = float(request.form.get('alpha'))
        beta = float(request.form.get('beta'))
        bc_type = request.form.get('bc_type')
        h = float(request.form.get('h'))
        
        # Solve using finite difference method
        x_fd, y_fd = finite_difference_method(equation, a, b, alpha, beta, bc_type, h)
        
        # Solve using shooting method
        x_shooting, y_shooting = shooting_method(equation, a, b, alpha, beta, bc_type, h)
        
        results = {}
        
        if x_fd is not None and y_fd is not None:
            # Create finite difference plot
            plot_url_fd = create_plot(x_fd, y_fd, "Finite Difference Method")
            
            # Prepare table data
            fd_table = []
            for i, (xi, yi) in enumerate(zip(x_fd, y_fd)):
                fd_table.append({'i': i, 'x': xi, 'y': yi})
            
            results['finite_difference'] = {
                'plot': plot_url_fd,
                'table': fd_table
            }
        
        if x_shooting is not None and y_shooting is not None:
            # Create shooting method plot
            plot_url_shooting = create_plot(x_shooting, y_shooting, "Shooting Method")
            
            # Prepare table data
            shooting_table = []
            for i, (xi, yi) in enumerate(zip(x_shooting, y_shooting)):
                shooting_table.append({'i': i, 'x': xi, 'y': yi})
            
            results['shooting'] = {
                'plot': plot_url_shooting,
                'table': shooting_table
            }
        
        return jsonify({'success': True, 'results': results})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    




@app.route('/documentation')
def documentation():
    return render_template('documentation.html',css="documentaton")




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)