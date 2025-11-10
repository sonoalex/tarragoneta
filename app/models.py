from datetime import datetime
from flask_security import UserMixin, RoleMixin
from app.extensions import db

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

class InventoryItem(db.Model):
    """Items del inventario (palomas, basura, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # 'palomas', 'basura', etc.
    subcategory = db.Column(db.String(50), nullable=False)  # 'nido', 'excremento', 'basura_desborda', 'vertidos', etc.
    description = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200))  # Dirección legible
    image_path = db.Column(db.String(300))
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected', 'active', 'resolved', 'removed'
    importance_count = db.Column(db.Integer, default=0)  # Contador de importancia/votos
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key (opcional - puede ser anónimo)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    reporter = db.relationship('User', backref='reported_items')
    voters = db.relationship('InventoryVote', backref='item', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def full_category(self):
        """Return full category path: category->subcategory"""
        return f"{self.category}->{self.subcategory}"
    
    def has_user_voted(self, user_id):
        """Check if a user has already voted for this item"""
        if not user_id:
            return False
        return self.voters.filter_by(user_id=user_id).first() is not None
    
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

