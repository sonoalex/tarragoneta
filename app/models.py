from datetime import datetime
from enum import Enum
from flask_security import UserMixin, RoleMixin
from flask_babel import _
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

# ========== Enums para Estados ==========

class InventoryItemStatus(str, Enum):
    """Estados posibles para items del inventario"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    RESOLVED = 'resolved'
    REMOVED = 'removed'
    # NOTA: Eliminamos 'active' porque es redundante con 'approved'
    
    @classmethod
    def all(cls):
        """Retorna todos los valores como lista"""
        return [status.value for status in cls]
    
    @classmethod
    def visible_statuses(cls):
        """Estados visibles en el mapa público"""
        return [cls.APPROVED.value]
    
    @classmethod
    def can_be_approved_from(cls):
        """Estados desde los que se puede aprobar"""
        return [cls.PENDING.value]
    
    @classmethod
    def can_be_resolved_from(cls):
        """Estados desde los que se puede resolver"""
        return [cls.APPROVED.value]

class InitiativeStatus(str, Enum):
    """Estados posibles para iniciativas"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    ACTIVE = 'active'
    CANCELLED = 'cancelled'
    
    @classmethod
    def all(cls):
        return [status.value for status in cls]
    
    @classmethod
    def visible_statuses(cls):
        """Estados visibles públicamente"""
        return [cls.APPROVED.value, cls.ACTIVE.value]

class DonationStatus(str, Enum):
    """Estados posibles para donaciones"""
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    
    @classmethod
    def all(cls):
        return [status.value for status in cls]

class ReportPurchaseStatus(str, Enum):
    """Estados posibles para compras de reports"""
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    
    @classmethod
    def all(cls):
        return [status.value for status in cls]

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
    
    def is_section_responsible(self, section_id=None):
        """Verificar si el usuario es responsable de alguna sección o de una específica"""
        if not section_id:
            return SectionResponsible.query.filter_by(user_id=self.id).first() is not None
        return SectionResponsible.query.filter_by(user_id=self.id, section_id=section_id).first() is not None
    
    def get_managed_sections(self):
        """Obtener todas las secciones que gestiona el usuario"""
        return [sr.section for sr in SectionResponsible.query.filter_by(user_id=self.id).all()]
    
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
        """Encontrar sección que contiene un punto usando PostGIS"""
        try:
            from sqlalchemy import func
            from app.extensions import db
            
            # Usar PostGIS para buscar sección que contiene el punto
            point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
            section = Section.query.filter(
                func.ST_Contains(
                    func.ST_GeomFromText(Section.polygon, 4326),
                    point
                )
            ).first()
            
            if section:
                return section
            
            # Fallback: usar Shapely si PostGIS falla
            try:
                from shapely import wkt
                from shapely.geometry import Point
                
                point = Point(lng, lat)
                sections = Section.query.all()
                for section in sections:
                    if section.polygon:
                        try:
                            geom = wkt.loads(section.polygon)
                            if geom.contains(point):
                                return section
                        except Exception:
                            continue
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Shapely fallback failed: {e}")
            
            return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Error finding section: {e}")
            return None
    
    def __repr__(self):
        return f'<Section {self.full_code}: {self.name or "Sin nombre"}>'

class SectionResponsible(db.Model):
    """Relación entre usuarios y secciones que gestionan"""
    __tablename__ = 'section_responsible'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    assigned_at = db.Column(db.DateTime(), default=datetime.utcnow)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Admin que asignó
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='managed_sections')
    section = db.relationship('Section', backref='responsibles')
    assigner = db.relationship('User', foreign_keys=[assigned_by])
    
    # Unique constraint: un usuario puede ser responsable de una sección solo una vez
    __table_args__ = (db.UniqueConstraint('user_id', 'section_id', name='unique_user_section'),)
    
    def __repr__(self):
        return f'<SectionResponsible user={self.user_id} section={self.section_id}>'

class CityBoundary(db.Model):
    """Boundary externo de Tarragona (unión de todas las secciones)"""
    __tablename__ = 'city_boundary'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default='Tarragona', nullable=False)
    polygon = db.Column(db.Text, nullable=False)  # WKT format
    calculated_at = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def calculate_boundary():
        """Calcular el boundary externo de Tarragona usando todos los polígonos de secciones"""
        try:
            from sqlalchemy import func, select
            from app.extensions import db
            
            # Usar PostGIS: ST_Union de todos los polígonos (une todos sin dejar áreas vacías)
            # Esto crea un boundary que sigue los contornos reales de las secciones
            # Primero corregimos la topología con ST_MakeValid, luego unimos
            valid_geoms = select(
                func.ST_MakeValid(
                    func.ST_GeomFromText(Section.polygon, 4326)
                ).label('geom')
            ).where(Section.polygon.isnot(None)).subquery()
            
            # Unir todas las geometrías válidas
            result = db.session.query(
                func.ST_AsText(
                    func.ST_Union(valid_geoms.c.geom)
                ).label('boundary')
            ).first()
            
            if result and result.boundary:
                return result.boundary
            
            # Fallback: usar Shapely si PostGIS falla
            try:
                from shapely import wkt
                from shapely.ops import unary_union
                
                sections = Section.query.all()
                polygons = []
                for section in sections:
                    if section.polygon:
                        try:
                            geom = wkt.loads(section.polygon)
                            polygons.append(geom)
                        except Exception:
                            continue
                
                if polygons:
                    union = unary_union(polygons)
                    return union.wkt
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Shapely boundary calculation failed: {e}")
            
            return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error calculating city boundary: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_or_create_boundary():
        """Obtener el boundary existente o calcularlo y guardarlo"""
        boundary = CityBoundary.query.first()
        
        if not boundary:
            # Calcular y guardar
            polygon_wkt = CityBoundary.calculate_boundary()
            if polygon_wkt:
                boundary = CityBoundary(
                    name='Tarragona',
                    polygon=polygon_wkt
                )
                db.session.add(boundary)
                db.session.commit()
                return boundary
        
        return boundary
    
    @staticmethod
    def point_is_inside(lat, lng):
        """Verificar si un punto está dentro del boundary de Tarragona"""
        boundary = CityBoundary.get_or_create_boundary()
        
        if not boundary or not boundary.polygon:
            # Si no hay boundary, usar validación básica por bounding box
            import logging
            logging.getLogger(__name__).warning(f"City boundary not found, using bounding box validation for point ({lat}, {lng})")
            return 40.5 <= lat <= 41.5 and 0.5 <= lng <= 2.0
        
        try:
            from sqlalchemy import func
            from app.extensions import db
            
            # Usar PostGIS ST_Contains (funciona con Polygon y MultiPolygon)
            # Primero validar el boundary con ST_MakeValid por si acaso
            point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
            boundary_geom = func.ST_MakeValid(
                func.ST_GeomFromText(boundary.polygon, 4326)
            )
            
            result = db.session.query(
                func.ST_Contains(
                    boundary_geom,
                    point
                ).label('inside')
            ).first()
            
            if result is not None:
                is_inside = bool(result.inside)
                import logging
                logging.getLogger(__name__).debug(
                    f"PostGIS validation: point ({lat}, {lng}) is {'INSIDE' if is_inside else 'OUTSIDE'} boundary"
                )
                return is_inside
            
            # Fallback: usar Shapely si PostGIS falla
            try:
                from shapely import wkt
                from shapely.geometry import Point
                
                geom = wkt.loads(boundary.polygon)
                point = Point(lng, lat)
                is_inside = geom.contains(point)
                import logging
                logging.getLogger(__name__).debug(
                    f"Shapely validation: point ({lat}, {lng}) is {'INSIDE' if is_inside else 'OUTSIDE'} boundary"
                )
                return is_inside
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Shapely point check failed: {e}")
            
            # Último fallback: bounding box básico
            import logging
            logging.getLogger(__name__).warning(
                f"Using bounding box fallback validation for point ({lat}, {lng})"
            )
            return 40.5 <= lat <= 41.5 and 0.5 <= lng <= 2.0
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error checking point inside boundary: {e}", exc_info=True)
            # Fallback a validación básica
            return 40.5 <= lat <= 41.5 and 0.5 <= lng <= 2.0
    
    def __repr__(self):
        return f'<CityBoundary {self.name} - calculated: {self.calculated_at}>'

class InventoryItem(db.Model):
    """Items del inventario (palomas, basura, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # 'palomas', 'basura', etc.
    subcategory = db.Column(db.String(50), nullable=False)  # 'nido', 'excremento', 'escombreries_desbordades', 'vertidos', etc.
    description = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200))  # Dirección legible
    image_path = db.Column(db.String(300))
    
    # GPS from image EXIF (for comparison with final location)
    image_gps_latitude = db.Column(db.Float, nullable=True)  # GPS lat from image EXIF
    image_gps_longitude = db.Column(db.Float, nullable=True)  # GPS lng from image EXIF
    location_source = db.Column(db.String(50), nullable=True)  # 'image_gps', 'browser_geolocation', 'manual', 'form_coordinates'
    status = db.Column(
        db.String(20), 
        default=InventoryItemStatus.PENDING.value,
        nullable=False
    )
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
    
    # ========== Métodos de consulta (Tell, Don't Ask) ==========
    
    def is_pending(self):
        """Verificar si el item está pendiente"""
        return self.status == InventoryItemStatus.PENDING.value
    
    def is_approved(self):
        """Verificar si el item está aprobado"""
        return self.status == InventoryItemStatus.APPROVED.value
    
    def is_resolved(self):
        """Verificar si el item está resuelto"""
        return self.status == InventoryItemStatus.RESOLVED.value
    
    def is_rejected(self):
        """Verificar si el item está rechazado"""
        return self.status == InventoryItemStatus.REJECTED.value
    
    def is_removed(self):
        """Verificar si el item está eliminado"""
        return self.status == InventoryItemStatus.REMOVED.value
    
    def can_be_approved(self):
        """Verificar si el item puede ser aprobado"""
        return self.status in InventoryItemStatus.can_be_approved_from()
    
    def can_be_rejected(self):
        """Verificar si el item puede ser rechazado"""
        return self.status == InventoryItemStatus.PENDING.value
    
    def can_be_resolved(self):
        """Verificar si el item puede ser resuelto"""
        return self.status in InventoryItemStatus.can_be_resolved_from()
    
    def is_visible(self):
        """Verificar si el item es visible en el mapa público"""
        return self.status in InventoryItemStatus.visible_statuses()
    
    # ========== Métodos de acción (Tell, Don't Ask) ==========
    
    def approve(self, approved_by=None):
        """Aprobar el item. Retorna (success: bool, message: str)"""
        if not self.can_be_approved():
            return False, _('Este item no puede ser aprobado')
        
        self.status = InventoryItemStatus.APPROVED.value
        self.updated_at = datetime.utcnow()
        
        from flask import current_app
        if current_app:
            current_app.logger.info(
                f'Item {self.id} approved by {approved_by.id if approved_by else "system"}'
            )
        
        return True, _('Item aprobado correctamente')
    
    def reject(self, reason=None, rejected_by=None):
        """Rechazar el item. Retorna (success: bool, message: str)"""
        if not self.can_be_rejected():
            return False, _('Este item no puede ser rechazado')
        
        self.status = InventoryItemStatus.REJECTED.value
        self.updated_at = datetime.utcnow()
        
        from flask import current_app
        if current_app:
            current_app.logger.info(
                f'Item {self.id} rejected by {rejected_by.id if rejected_by else "system"}. Reason: {reason}'
            )
        
        return True, _('Item rechazado')
    
    def resolve(self, resolved_by=None):
        """Marcar el item como resuelto. Retorna (success: bool, message: str)"""
        if not self.can_be_resolved():
            return False, _('Este item no puede ser resuelto')
        
        self.status = InventoryItemStatus.RESOLVED.value
        self.updated_at = datetime.utcnow()
        
        from flask import current_app
        if current_app:
            current_app.logger.info(
                f'Item {self.id} resolved by {resolved_by.id if resolved_by else "system"}'
            )
        
        return True, _('Item marcado como resuelto')
    
    def remove(self, removed_by=None):
        """Eliminar/ocultar el item. Retorna (success: bool, message: str)"""
        self.status = InventoryItemStatus.REMOVED.value
        self.updated_at = datetime.utcnow()
        
        from flask import current_app
        if current_app:
            current_app.logger.info(
                f'Item {self.id} removed by {removed_by.id if removed_by else "system"}'
            )
        
        return True, _('Item eliminado')
    
    def add_resolved_report(self, user_id):
        """Añadir un reporte de "ya no está" y auto-resolver si alcanza el threshold.
        Retorna (success: bool, auto_resolved: bool, message: str)"""
        from app.models import InventoryResolved
        from flask import current_app
        
        if self.has_user_resolved(user_id):
            return False, False, _('Ya has reportado que este item ya no está')
        
        if self.is_resolved():
            return False, False, _('Este item ya está marcado como resuelto')
        
        # Si el usuario votó "encara hi és", remover ese voto
        if self.has_user_voted(user_id):
            vote = self.voters.filter_by(user_id=user_id).first()
            if vote:
                db.session.delete(vote)
                if self.importance_count and self.importance_count > 0:
                    self.importance_count -= 1
                else:
                    self.importance_count = 0
        
        # Crear reporte de resuelto
        resolved = InventoryResolved(item_id=self.id, user_id=user_id)
        db.session.add(resolved)
        
        # Incrementar contador
        if self.resolved_count is None:
            self.resolved_count = 0
        self.resolved_count += 1
        
        # Auto-resolver si alcanza el threshold
        auto_resolved = False
        auto_resolve_threshold = current_app.config.get('INVENTORY_AUTO_RESOLVE_THRESHOLD', 3) if current_app else 3
        
        if self.resolved_count >= auto_resolve_threshold and self.can_be_resolved():
            success, _ = self.resolve()
            auto_resolved = success
            if auto_resolved:
                current_app.logger.info(
                    f'Item {self.id} auto-resolved after {self.resolved_count} "ya no está" reports'
                )
        
        message = _('Item marcado como resuelto automáticamente') if auto_resolved else _('Reporte registrado correctamente')
        return True, auto_resolved, message
    
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

class ReportPurchase(db.Model):
    """Track purchases of reports"""
    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(50), nullable=False)  # e.g., 'inventory_by_zone', 'trends'
    report_params = db.Column(db.Text, nullable=True)  # JSON string of filters used for the report
    amount = db.Column(db.Integer, nullable=False)  # Amount in cents
    currency = db.Column(db.String(3), default='eur')
    email = db.Column(db.String(255), nullable=True)  # Purchaser email
    stripe_session_id = db.Column(db.String(255), unique=True, nullable=False)
    stripe_payment_intent_id = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed', 'refunded'
    download_token = db.Column(db.String(255), unique=True, nullable=True)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    completed_at = db.Column(db.DateTime())
    downloaded_at = db.Column(db.DateTime())
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='report_purchases')
    
    @property
    def amount_euros(self):
        return self.amount / 100
    
    def __repr__(self):
        return f'<ReportPurchase {self.report_type} - {self.amount_euros}€ - {self.status}>'

