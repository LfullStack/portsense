from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date
from config import Config
from database import db, User, Ship, Cargo, Alert, Operation

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def analyze_risk(ship):
    alerts = []
    cargo_count = Cargo.query.filter_by(ship_id=ship.id).count()
    if cargo_count == 0:
        alerts.append(('documents', 'medium', 'Buque sin mercancia registrada'))
    if ship.status == 'pending':
        alerts.append(('delay', 'low', 'Buque en estado pendiente - posible retraso'))
    today = date.today()
    if ship.arrival_date < today and ship.status == 'pending':
        alerts.append(('delay', 'high', 'Buque atrasado - fecha de llegada ya paso'))
    return alerts

def get_risk_level(alerts):
    severities = [a[1] for a in alerts]
    if 'high' in severities:
        return 'alto'
    elif 'medium' in severities:
        return 'medio'
    return 'bajo'

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Bienvenido a PortuSense', 'success')
            return redirect(url_for('dashboard'))
        flash('Usuario o contrasena incorrectos', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'operator')
        if User.query.filter_by(username=username).first():
            flash('El usuario ya existe', 'danger')
            return render_template('register.html')
        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Cuenta creada exitosamente. Inicia sesion.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    ships = Ship.query.all()
    total_ships = len(ships)
    pending_ships = Ship.query.filter_by(status='pending').count()
    in_progress_ships = Ship.query.filter_by(status='in_progress').count()
    completed_ships = Ship.query.filter_by(status='completed').count()
    recent_alerts = Alert.query.filter_by(is_read=False).order_by(Alert.created_at.desc()).limit(5).all()
    risk_data = []
    for ship in ships:
        alerts = analyze_risk(ship)
        risk_data.append({
            'ship': ship,
            'risk': get_risk_level(alerts),
            'alert_count': len(alerts)
        })
    return render_template('dashboard.html',
        total_ships=total_ships,
        pending_ships=pending_ships,
        in_progress_ships=in_progress_ships,
        completed_ships=completed_ships,
        recent_alerts=recent_alerts,
        risk_data=risk_data)

@app.route('/ships', methods=['GET', 'POST'])
@login_required
def ships():
    if request.method == 'POST':
        name = request.form['name']
        arrival_date = datetime.strptime(request.form['arrival_date'], '%Y-%m-%d').date()
        eta = datetime.strptime(request.form['eta'], '%H:%M').time()
        cargo_type = request.form.get('cargo_type', '')
        status = request.form.get('status', 'pending')
        ship = Ship(name=name, arrival_date=arrival_date, eta=eta,
                    cargo_type=cargo_type, status=status, created_by=current_user.id)
        db.session.add(ship)
        db.session.commit()
        flash('Buque registrado exitosamente', 'success')
        return redirect(url_for('ships'))
    all_ships = Ship.query.order_by(Ship.created_at.desc()).all()
    return render_template('ships.html', ships=all_ships)

@app.route('/ships/edit/<int:ship_id>', methods=['GET', 'POST'])
@login_required
def edit_ship(ship_id):
    ship = Ship.query.get_or_404(ship_id)
    if request.method == 'POST':
        ship.name = request.form['name']
        ship.arrival_date = datetime.strptime(request.form['arrival_date'], '%Y-%m-%d').date()
        ship.eta = datetime.strptime(request.form['eta'], '%H:%M').time()
        ship.cargo_type = request.form.get('cargo_type', '')
        ship.status = request.form.get('status', 'pending')
        db.session.commit()
        flash('Buque actualizado', 'success')
        return redirect(url_for('ships'))
    return render_template('ships.html', ships=Ship.query.order_by(Ship.created_at.desc()).all(), edit_ship=ship)

@app.route('/ships/delete/<int:ship_id>')
@login_required
def delete_ship(ship_id):
    ship = Ship.query.get_or_404(ship_id)
    db.session.delete(ship)
    db.session.commit()
    flash('Buque eliminado', 'success')
    return redirect(url_for('ships'))

@app.route('/cargo', methods=['GET', 'POST'])
@login_required
def cargo():
    if request.method == 'POST':
        ship_id = int(request.form['ship_id'])
        cargo_type = request.form['cargo_type']
        quantity = int(request.form['quantity'])
        weight = float(request.form['weight'])
        location = request.form.get('location', '')
        destination = request.form.get('destination', '')
        item = Cargo(ship_id=ship_id, cargo_type=cargo_type, quantity=quantity,
                     weight=weight, location=location, destination=destination)
        db.session.add(item)
        db.session.commit()
        flash('Mercancia registrada', 'success')
        return redirect(url_for('cargo'))
    all_cargo = Cargo.query.order_by(Cargo.created_at.desc()).all()
    ships = Ship.query.all()
    return render_template('cargo.html', cargo_items=all_cargo, ships=ships)

@app.route('/cargo/delete/<int:cargo_id>')
@login_required
def delete_cargo(cargo_id):
    item = Cargo.query.get_or_404(cargo_id)
    db.session.delete(item)
    db.session.commit()
    flash('Mercancia eliminada', 'success')
    return redirect(url_for('cargo'))

@app.route('/alerts')
@login_required
def alerts():
    all_alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    ships = Ship.query.all()
    return render_template('alerts.html', alerts_list=all_alerts, ships=ships)

@app.route('/alerts/generate', methods=['POST'])
@login_required
def generate_alerts():
    ships = Ship.query.all()
    new_alerts = 0
    for ship in ships:
        existing = Alert.query.filter_by(ship_id=ship.id).filter(
            Alert.created_at >= datetime.combine(date.today(), datetime.min.time())
        ).count()
        if existing > 0:
            continue
        risk_alerts = analyze_risk(ship)
        for alert_type, severity, message in risk_alerts:
            alert = Alert(ship_id=ship.id, alert_type=alert_type,
                         severity=severity, message=message)
            db.session.add(alert)
            new_alerts += 1
    db.session.commit()
    flash(f'Se generaron {new_alerts} nuevas alertas', 'info')
    return redirect(url_for('alerts'))

@app.route('/alerts/read/<int:alert_id>')
@login_required
def mark_alert_read(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_read = True
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/reports')
@login_required
def reports():
    ships = Ship.query.all()
    total_ships = len(ships)
    pending = Ship.query.filter_by(status='pending').count()
    in_progress = Ship.query.filter_by(status='in_progress').count()
    completed = Ship.query.filter_by(status='completed').count()
    total_cargo = Cargo.query.count()
    total_weight = db.session.query(db.func.sum(Cargo.weight)).scalar() or 0
    high_alerts = Alert.query.filter_by(severity='high', is_read=False).count()
    medium_alerts = Alert.query.filter_by(severity='medium', is_read=False).count()
    low_alerts = Alert.query.filter_by(severity='low', is_read=False).count()
    return render_template('reports.html',
        total_ships=total_ships, pending=pending,
        in_progress=in_progress, completed=completed,
        total_cargo=total_cargo, total_weight=total_weight,
        high_alerts=high_alerts, medium_alerts=medium_alerts,
        low_alerts=low_alerts, ships=ships)

@app.route('/api/dashboard-data')
@login_required
def dashboard_data():
    return jsonify({
        'pending': Ship.query.filter_by(status='pending').count(),
        'in_progress': Ship.query.filter_by(status='in_progress').count(),
        'completed': Ship.query.filter_by(status='completed').count(),
        'high_alerts': Alert.query.filter_by(severity='high', is_read=False).count(),
        'medium_alerts': Alert.query.filter_by(severity='medium', is_read=False).count(),
        'low_alerts': Alert.query.filter_by(severity='low', is_read=False).count()
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
