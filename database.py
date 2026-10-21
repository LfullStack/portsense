from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='operator')
    full_name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    access_logs = db.relationship('AccessLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Ship(db.Model):
    __tablename__ = 'ships'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    arrival_date = db.Column(db.Date, nullable=False)
    eta = db.Column(db.Time, nullable=False)
    cargo_type = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cargo_items = db.relationship('Cargo', backref='ship', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='ship', lazy=True, cascade='all, delete-orphan')

class Cargo(db.Model):
    __tablename__ = 'cargo'
    id = db.Column(db.Integer, primary_key=True)
    ship_id = db.Column(db.Integer, db.ForeignKey('ships.id'), nullable=False)
    cargo_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(50))
    destination = db.Column(db.String(100))
    status = db.Column(db.String(20), default='stored')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    traces = db.relationship('CargoTrace', backref='cargo', lazy=True, cascade='all, delete-orphan')

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    ship_id = db.Column(db.Integer, db.ForeignKey('ships.id'), nullable=True)
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(10), nullable=False, default='low')
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Operation(db.Model):
    __tablename__ = 'operations'
    id = db.Column(db.Integer, primary_key=True)
    ship_id = db.Column(db.Integer, db.ForeignKey('ships.id'), nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='in_progress')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Driver(db.Model):
    __tablename__ = 'drivers'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    license_expiry = db.Column(db.Date)
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trucks = db.relationship('Truck', backref='driver', lazy=True)

class Truck(db.Model):
    __tablename__ = 'trucks'
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    truck_type = db.Column(db.String(50), nullable=False)
    capacity_tons = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='available')
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    current_cargo_id = db.Column(db.Integer, db.ForeignKey('cargo.id'), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    last_location = db.Column(db.String(200))
    last_report_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    route_events = db.relationship('RouteEvent', backref='truck', lazy=True)

class Yard(db.Model):
    __tablename__ = 'yards'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    yard_type = db.Column(db.String(20), nullable=False, default='yard')
    capacity_tons = db.Column(db.Float, nullable=False, default=0)
    current_occupancy_tons = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(20), default='active')
    location = db.Column(db.String(200))
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    slots = db.relationship('YardSlot', backref='yard', lazy=True, cascade='all, delete-orphan')

class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    equipment_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='active')
    location = db.Column(db.String(200))
    last_maintenance = db.Column(db.Date)
    next_maintenance = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Personnel(db.Model):
    __tablename__ = 'personnel'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    position = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(80))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    status = db.Column(db.String(20), default='active')
    hire_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accidents = db.relationship('Accident', backref='personnel', lazy=True)

class DocumentRecord(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    doc_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    ship_id = db.Column(db.Integer, db.ForeignKey('ships.id'), nullable=True)
    personnel_id = db.Column(db.Integer, db.ForeignKey('personnel.id'), nullable=True)
    truck_id = db.Column(db.Integer, db.ForeignKey('trucks.id'), nullable=True)
    expires_at = db.Column(db.Date)
    is_valid = db.Column(db.Boolean, default=True)
    file_reference = db.Column(db.String(300))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Accident(db.Model):
    __tablename__ = 'accidents'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='minor')
    location = db.Column(db.String(200))
    ship_id = db.Column(db.Integer, db.ForeignKey('ships.id'), nullable=True)
    ship = db.relationship('Ship', backref='accidents')
    truck_id = db.Column(db.Integer, db.ForeignKey('trucks.id'), nullable=True)
    truck = db.relationship('Truck', backref='accidents')
    personnel_id = db.Column(db.Integer, db.ForeignKey('personnel.id'), nullable=True)
    accident_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='reported')
    injuries_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    creator = db.relationship('User', backref='reported_accidents')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    follow_ups = db.relationship('AccidentFollowUp', backref='accident', lazy=True, cascade='all, delete-orphan')

class AccidentFollowUp(db.Model):
    __tablename__ = 'accident_followups'
    id = db.Column(db.Integer, primary_key=True)
    accident_id = db.Column(db.Integer, db.ForeignKey('accidents.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    action_taken = db.Column(db.Text)
    followup_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CargoTrace(db.Model):
    __tablename__ = 'cargo_traces'
    id = db.Column(db.Integer, primary_key=True)
    cargo_id = db.Column(db.Integer, db.ForeignKey('cargo.id'), nullable=False)
    from_location = db.Column(db.String(100))
    to_location = db.Column(db.String(100), nullable=False)
    moved_by = db.Column(db.String(100))
    moved_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

class AccessLog(db.Model):
    __tablename__ = 'access_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(20), nullable=False)
    ip_address = db.Column(db.String(45))
    details = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class YardSlot(db.Model):
    __tablename__ = 'yard_slots'
    id = db.Column(db.Integer, primary_key=True)
    yard_id = db.Column(db.Integer, db.ForeignKey('yards.id'), nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    status = db.Column(db.String(10), nullable=False, default='empty')
    cargo_name = db.Column(db.String(200))
    internal_code = db.Column(db.String(50))
    onu_number = db.Column(db.String(20))
    weight = db.Column(db.String(50))
    quantity = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RouteEvent(db.Model):
    __tablename__ = 'route_events'
    id = db.Column(db.Integer, primary_key=True)
    truck_id = db.Column(db.Integer, db.ForeignKey('trucks.id'), nullable=True)
    driver_name = db.Column(db.String(120))
    event_type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    detail = db.Column(db.Text)
    severity = db.Column(db.String(10), nullable=False, default='ok')
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reporter = db.relationship('User', backref='route_reports')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
