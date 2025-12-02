from datetime import datetime
from flask_security import UserMixin, RoleMixin
from app.extensions import db

# Import GeoAlchemy2 for PostGIS support
try:
    from geoalchemy2 import Geometry
    from geoalchemy2.shape import from_shape
    from shapely.geometry import shape as shapely_shape
    POSTGIS_AVAILABLE = True
except ImportError:
    POSTGIS_AVAILABLE = False
    Geometry = None

# Association table for many-to-many relationship between users and roles
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

# Association table for users participating in initiatives
user_initiatives = db.Table('user_initiatives',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('initiative_id', db.Integer(), db.ForeignKey('initiative.id')),
    db.Column('joined_at', db.DateTime(), default=datetime.utcnow)
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean(), default=True)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    confirmed_at = db.Column(db.DateTime())
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    
    # Relationships
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    created_initiatives = db.relationship('Initiative', backref='creator', lazy='dynamic')
    participated_initiatives = db.relationship('Initiative', secondary=user_initiatives, backref='participants', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Initiative(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10))
    image_path = db.Column(db.String(300))
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected', 'active', 'cancelled'
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    view_count = db.Column(db.Integer, default=0)
    
    # Foreign key for creator
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    comments = db.relationship('Comment', backref='initiative', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def participant_count(self):
        return len(self.participants)
    
    @property
    def is_upcoming(self):
        return self.date >= datetime.now().date()
    
    @property
    def days_until(self):
        if self.is_upcoming:
            delta = self.date - datetime.now().date()
            return delta.days
        return -1
    
    @staticmethod
    def generate_slug(title):
        """Generate a URL-friendly slug from title"""
        from app.utils import generate_slug as util_generate_slug
        return util_generate_slug(title)
    
    def __repr__(self):
        return f'<Initiative {self.title}>'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    initiative_id = db.Column(db.Integer, db.ForeignKey('initiative.id'), nullable=False)
    
    def __repr__(self):
        return f'<Comment by {self.author.username}>'

class Participation(db.Model):
    """Track anonymous participations (for non-registered users)"""
    id = db.Column(db.Integer, primary_key=True)
    initiative_id = db.Column(db.Integer, db.ForeignKey('initiative.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    
    initiative_rel = db.relationship('Initiative', backref='anonymous_participants')

class District(db.Model):
    """Distritos administrativos de Tarragona"""
    __tablename__ = 'district'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)  # '01', '02', etc.
    name = db.Column(db.String(100), nullable=False)  # 'Districte 1', etc.
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sections = db.relationship('Section', backref='district', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<District {self.code}: {self.name}>'

class Section(db.Model):
    """Secciones administrativas dentro de un distrito"""
    __tablename__ = 'section'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), nullable=False)  # '001', '002', etc.
    district_code = db.Column(db.String(10), db.ForeignKey('district.code'), nullable=False)
    name = db.Column(db.String(100))  # Nombre descriptivo (opcional)
    
    # PostGIS geometry column for the polygon
    # Stored as Text (WKT format) - will be converted to PostGIS Geometry in PostgreSQL
    polygon = db.Column(db.Text, nullable=False)
    
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('InventoryItem', backref='section', lazy='dynamic')
    
    # Unique constraint: one section per code per district
    __table_args__ = (db.UniqueConstraint('district_code', 'code', name='unique_district_section'),)
    
    @property
    def full_code(self):
        """Return full code: district_code-section_code"""
        return f"{self.district_code}-{self.code}"
    
    @staticmethod
    def find_section_for_point(lat, lng):
        """Encontrar sección que contiene un punto usando PostGIS o Shapely (WKT)"""
        try:
            from sqlalchemy import func
            from app.extensions import db
            
            # Verificar si estamos usando PostgreSQL
            db_url = str(db.engine.url)
            is_postgresql = 'postgresql' in db_url
            
            # Intentar usar PostGIS si está disponible y es PostgreSQL
            if is_postgresql and POSTGIS_AVAILABLE and Geometry:
                try:
                    # Convertir WKT a PostGIS Geometry en la consulta
                    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
                    # Buscar sección que contiene el punto usando ST_GeomFromText para convertir WKT
                    section = Section.query.filter(
                        func.ST_Contains(
                            func.ST_GeomFromText(Section.polygon, 4326),
                            point
                        )
                    ).first()
                    if section:
                        return section
                except Exception as e:
                    # Si PostGIS falla, continuar con Shapely
                    import logging
                    logging.getLogger(__name__).debug(f"PostGIS query failed, trying Shapely: {e}")
            
            # Fallback: usar Shapely para verificar polígonos WKT
            if POSTGIS_AVAILABLE:
                try:
                    from shapely import wkt
                    from shapely.geometry import Point
                    
                    point = Point(lng, lat)
                    
                    # Buscar todas las secciones y verificar manualmente
                    sections = Section.query.all()
                    for section in sections:
                        if section.polygon:
                            try:
                                geom = wkt.loads(section.polygon)
                                if geom.contains(point):
                                    return section
                            except Exception:
                                continue
                except ImportError:
                    pass
            
            return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Error finding section: {e}")
            return None
    
    def __repr__(self):
        return f'<Section {self.full_code}: {self.name or "Sin nombre"}>'

class InventoryItem(db.Model):
    """Items del inventario (palomas, basura, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # 'palomas', 'basura', etc.
    subcategory = db.Column(db.String(50), nullable=False)  # 'nido', 'excremento', 'basura_desbordada', 'vertidos', etc.
    description = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200))  # Dirección legible
    image_path = db.Column(db.String(300))
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected', 'active', 'resolved', 'removed'
    importance_count = db.Column(db.Integer, default=0)  # Contador de importancia/votos
    resolved_count = db.Column(db.Integer, default=0)  # Contador de "ya no está"
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key (opcional - puede ser anónimo)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Foreign key to section (nuevo)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=True)
    
    # PostGIS point geometry (nuevo)
    # Por ahora nullable, se puede usar PostGIS si está disponible
    location = None  # Se puede añadir en migración si PostGIS está disponible
    
    # Relationships
    reporter = db.relationship('User', backref='reported_items')
    voters = db.relationship('InventoryVote', backref='item', lazy='dynamic', cascade='all, delete-orphan')
    resolved_by = db.relationship('InventoryResolved', backref='item', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def full_category(self):
        """Return full category path: category->subcategory"""
        return f"{self.category}->{self.subcategory}"
    
    def has_user_voted(self, user_id):
        """Check if a user has already voted for this item"""
        if not user_id:
            return False
        return self.voters.filter_by(user_id=user_id).first() is not None
    
    def has_user_resolved(self, user_id):
        """Check if a user has already reported this item as resolved"""
        if not user_id:
            return False
        return self.resolved_by.filter_by(user_id=user_id).first() is not None
    
    def assign_section(self):
        """Asignar automáticamente la sección basándose en las coordenadas"""
        if self.section_id:
            return True  # Ya tiene sección asignada
        
        section = Section.find_section_for_point(self.latitude, self.longitude)
        if section:
            self.section_id = section.id
            return True
        return False
    
    def __repr__(self):
        return f'<InventoryItem {self.category}->{self.subcategory} at ({self.latitude}, {self.longitude})>'

class InventoryVote(db.Model):
    """Track votes/importance for inventory items"""
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='inventory_votes')
    
    # Unique constraint: one vote per user per item
    __table_args__ = (db.UniqueConstraint('item_id', 'user_id', name='unique_item_user_vote'),)
    
    def __repr__(self):
        return f'<InventoryVote user:{self.user_id} item:{self.item_id}>'

class InventoryResolved(db.Model):
    """Track "ya no está" reports for inventory items"""
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='inventory_resolved')
    
    # Unique constraint: one "ya no está" report per user per item
    __table_args__ = (db.UniqueConstraint('item_id', 'user_id', name='unique_item_user_resolved'),)
    
    def __repr__(self):
        return f'<InventoryResolved user:{self.user_id} item:{self.item_id}>'

class Donation(db.Model):
    """Track donations received through Stripe"""
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)  # Amount in cents
    currency = db.Column(db.String(3), default='eur')
    email = db.Column(db.String(255))  # Donor email (optional)
    stripe_session_id = db.Column(db.String(255), unique=True, nullable=False)
    stripe_payment_intent_id = db.Column(db.String(255))  # Payment intent ID if available
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed', 'refunded'
    donation_type = db.Column(db.String(50), default='voluntary')  # 'voluntary', etc.
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    completed_at = db.Column(db.DateTime())  # When payment was completed
    
    # Optional: link to user if they were logged in
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='donations')
    
    @property
    def amount_euros(self):
        """Return amount in euros"""
        return self.amount / 100
    
    def __repr__(self):
        return f'<Donation {self.amount_euros}€ from {self.email or "anonymous"} - {self.status}>'

