from flask import has_request_context, current_app
from flask_wtf import FlaskForm
from flask_security.forms import RegisterForm
from flask_babel import gettext as _, lazy_gettext as _l
from wtforms import StringField, TextAreaField, DateField, SelectField, FileField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional
from app.extensions import db
from app.models import User, InventoryCategory

class ExtendedRegisterForm(RegisterForm):
    username = StringField(_l('Nombre de usuario'), validators=[DataRequired(), Length(min=3, max=255)])
    accept_terms = BooleanField(_l('Accepto les condicions d\'ús i privacitat'), validators=[DataRequired(message=_l('Has d\'acceptar les condicions'))])
    
    def validate(self, extra_validators=None):
        # Call parent validate without extra_validators to avoid signature mismatch
        if not super().validate():
            return False
        
        # Check if username already exists
        if User.query.filter_by(username=self.username.data).first():
            self.username.errors.append(_('Este nombre de usuario ya está en uso'))
            return False
        
        return True

class InitiativeForm(FlaskForm):
    title = StringField(_l('Title'), validators=[DataRequired(), Length(min=5, max=200)])
    description = TextAreaField(_l('Description'), validators=[DataRequired(), Length(min=20)])
    location = StringField(_l('Location'), validators=[DataRequired()])
    category = SelectField(_l('Category'), validators=[DataRequired()])
    date = DateField(_l('Date'), validators=[DataRequired()])
    time = StringField(_l('Time'), validators=[Optional()])
    image = FileField(_l('Image'), validators=[Optional()])
    status = SelectField(_l('Status'), validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(InitiativeForm, self).__init__(*args, **kwargs)
        # Set status choices dynamically to support translations
        if has_request_context():
            from flask_babel import gettext as _
            self.status.choices = [
                ('pending', '⏳ ' + str(_('Pendent'))),
                ('approved', '✅ ' + str(_('Aprovada'))),
                ('rejected', '❌ ' + str(_('Rebutjada'))),
                ('active', '🟢 ' + str(_('Activa'))),
                ('cancelled', '🚫 ' + str(_('Cancel·lada')))
            ]
        else:
            # Fallback for when there's no request context
            self.status.choices = [
                ('pending', '⏳ Pending'),
                ('approved', '✅ Approved'),
                ('rejected', '❌ Rejected'),
                ('active', '🟢 Active'),
                ('cancelled', '🚫 Cancelled')
            ]
        # Set category choices dynamically to support translations
        if has_request_context():
            self.category.choices = [
                ('limpieza', '🧹 ' + str(_('Cleaning'))),
                ('reciclaje', '♻️ ' + str(_('Recycling'))),
                ('espacios_verdes', '🌳 ' + str(_('Green Spaces'))),
                ('movilidad', '🚴 ' + str(_('Sustainable Mobility'))),
                ('educacion', '📚 ' + str(_('Environmental Education'))),
                ('cultura', '🎭 ' + str(_('Culture and Civics'))),
                ('social', '🤝 ' + str(_('Social Action'))),
                ('escombreries_desbordades', '🗑️ ' + str(_('Escombreries Desbordades'))),
                ('vertidos', '💧 ' + str(_('Dumping')))
            ]
        else:
            # Fallback for when there's no request context
            self.category.choices = [
                ('limpieza', '🧹 Cleaning'),
                ('reciclaje', '♻️ Recycling'),
                ('espacios_verdes', '🌳 Green Spaces'),
                ('movilidad', '🚴 Sustainable Mobility'),
                ('educacion', '📚 Environmental Education'),
                ('cultura', '🎭 Culture and Civics'),
                ('social', '🤝 Social Action'),
                ('escombreries_desbordades', '🗑️ Escombreries Desbordades'),
                ('vertidos', '💧 Dumping')
            ]

class InventoryForm(FlaskForm):
    category = SelectField(_l('Category'), validators=[DataRequired()])
    subcategory = SelectField(_l('Subcategory'), validators=[DataRequired()])
    description = TextAreaField(_l('Description'), validators=[Optional(), Length(max=500)])
    latitude = StringField(_l('Latitude'), validators=[Optional()])  # Opcional: se obtiene de imagen GPS o navegador
    longitude = StringField(_l('Longitude'), validators=[Optional()])  # Opcional: se obtiene de imagen GPS o navegador
    address = StringField(_l('Address'), validators=[Optional()])
    image = FileField(_l('Photo'), validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        super(InventoryForm, self).__init__(*args, **kwargs)
        # Cargar categorías desde BD (con fallback a hardcoded si falla)
        try:
            if has_request_context():
                # Cargar categorías principales desde BD
                main_categories = InventoryCategory.query.filter_by(
                    parent_id=None,
                    is_active=True
                ).order_by(InventoryCategory.sort_order).all()
                
                if main_categories:
                    self.category.choices = [
                        (cat.code, f"{cat.icon} {cat.get_name()}")
                        for cat in main_categories
                    ]
                    
                    # Cargar todas las subcategorías (para validación)
                    # Se filtrarán por JavaScript según la categoría seleccionada
                    all_subcategories = InventoryCategory.query.filter(
                        InventoryCategory.parent_id.isnot(None),
                        InventoryCategory.is_active == True
                    ).order_by(InventoryCategory.sort_order).all()
                    
                    self.subcategory.choices = [
                        (subcat.code, f"{subcat.icon} {subcat.get_name()}")
                        for subcat in all_subcategories
                    ]
                else:
                    # Fallback: usar categorías hardcoded si BD está vacía
                    self._load_hardcoded_categories()
            else:
                # Sin request context: usar fallback hardcoded
                self._load_hardcoded_categories()
        except Exception as e:
            # Si hay error accediendo a BD, usar fallback
            if current_app:
                current_app.logger.warning(f"Error loading categories from DB, using fallback: {e}")
            self._load_hardcoded_categories()
    
    def _load_hardcoded_categories(self):
        """Fallback: cargar categorías hardcoded (para compatibilidad)"""
        if has_request_context():
            self.category.choices = [
                ('coloms', '🕊️ ' + str(_('Coloms'))),
                ('contenidors', '🗑️ ' + str(_('Contenidors'))),
                ('canis', '🐕 ' + str(_('Canis'))),
                ('mobiliari_deteriorat', '🔧 ' + str(_('Mobiliari Deteriorat'))),
                ('bruticia', '🧹 ' + str(_('Brutícia'))),
                ('vandalisme', '🎨 ' + str(_('Vandalisme'))),
                ('vegetacio', '🌳 ' + str(_('Vegetació'))),
                ('infraestructura', '🏗️ ' + str(_('Infraestructura')))
            ]
            self.subcategory.choices = [
                # Coloms
                ('niu', '🪺 ' + str(_('Niu'))),
                ('excrement', '💩 ' + str(_('Excrement'))),
                ('ploma', '🪶 ' + str(_('Ploma'))),
                # Contenidors
                ('abocaments', '💧 ' + str(_('Abocaments'))),
                ('deixadesa', '🧹 ' + str(_('Deixadesa'))),
                # Canis
                ('excrements', '💩 ' + str(_('Excrements'))),
                ('pixades', '💧 ' + str(_('Pixades'))),
                # Mobiliari Deteriorat
                ('faroles', '💡 ' + str(_('Faroles'))),
                ('bancs', '🪑 ' + str(_('Bancs'))),
                ('senyals', '🚦 ' + str(_('Senyals'))),
                ('paviment', '🛣️ ' + str(_('Paviment'))),
                ('papereres', '🗑️ ' + str(_('Papereres'))),
                ('parades', '🚏 ' + str(_('Parades'))),
                # Brutícia
                ('terra', '🌍 ' + str(_('Terra'))),
                ('fulles', '🍂 ' + str(_('Fulles'))),
                ('grafit', '🎨 ' + str(_('Grafit'))),
                # Vandalisme
                ('pintades', '🖌️ ' + str(_('Pintades'))),
                # Vegetació
                ('arbres', '🌳 ' + str(_('Arbres'))),
                ('arbustos', '🌿 ' + str(_('Arbustos'))),
                ('gespa', '🌱 ' + str(_('Gespa'))),
                # Infraestructura
                ('carreteres', '🛣️ ' + str(_('Carreteres'))),
                ('voreres', '🚶 ' + str(_('Voreres'))),
                ('enllumenat', '💡 ' + str(_('Enllumenat')))
            ]
        else:
            # Sin request context
            self.category.choices = [
                ('coloms', '🕊️ Coloms'),
                ('contenidors', '🗑️ Contenidors'),
                ('canis', '🐕 Canis'),
                ('mobiliari_deteriorat', '🔧 Mobiliari Deteriorat'),
                ('bruticia', '🧹 Brutícia'),
                ('vandalisme', '🎨 Vandalisme'),
                ('vegetacio', '🌳 Vegetació'),
                ('infraestructura', '🏗️ Infraestructura')
            ]
            self.subcategory.choices = [
                ('niu', '🪺 Niu'),
                ('excrement', '💩 Excrement'),
                ('ploma', '🪶 Ploma'),
                ('abocaments', '💧 Abocaments'),
                ('deixadesa', '🧹 Deixadesa'),
                ('excrements', '💩 Excrements'),
                ('pixades', '💧 Pixades'),
                ('faroles', '💡 Faroles'),
                ('bancs', '🪑 Bancs'),
                ('senyals', '🚦 Senyals'),
                ('paviment', '🛣️ Paviment'),
                ('papereres', '🗑️ Papereres'),
                ('parades', '🚏 Parades'),
                ('terra', '🌍 Terra'),
                ('fulles', '🍂 Fulles'),
                ('grafit', '🎨 Grafit'),
                ('pintades', '🖌️ Pintades'),
                ('arbres', '🌳 Arbres'),
                ('arbustos', '🌿 Arbustos'),
                ('gespa', '🌱 Gespa'),
                ('carreteres', '🛣️ Carreteres'),
                ('voreres', '🚶 Voreres'),
                ('enllumenat', '💡 Enllumenat')
            ]
    
    def validate_subcategory(self, field):
        """Custom validation to ensure subcategory matches selected category"""
        category_code = self.category.data
        subcategory_code = field.data
        
        if not category_code or not subcategory_code:
            return
        
        try:
            # Validar desde BD
            main_category = InventoryCategory.query.filter_by(
                code=category_code,
                parent_id=None,
                is_active=True
            ).first()
            
            if main_category:
                # Verificar que la subcategoría pertenece a esta categoría
                subcategory = InventoryCategory.query.filter_by(
                    code=subcategory_code,
                    parent_id=main_category.id,
                    is_active=True
                ).first()
                
                if not subcategory:
                    from wtforms.validators import ValidationError
                    raise ValidationError(_('Subcategoría no válida para esta categoría'))
            else:
                # Fallback: validación hardcoded (para compatibilidad)
                self._validate_subcategory_hardcoded(category_code, subcategory_code)
        except Exception as e:
            # Si hay error, usar validación hardcoded
            if current_app:
                current_app.logger.warning(f"Error validating subcategory from DB, using fallback: {e}")
            self._validate_subcategory_hardcoded(category_code, subcategory_code)
    
    def _validate_subcategory_hardcoded(self, category_code, subcategory_code):
        """Fallback: validación hardcoded (para compatibilidad)"""
        valid_subcategories = {
            'coloms': ['niu', 'excrement', 'ploma'],
            'contenidors': ['abocaments', 'deixadesa'],
            'canis': ['excrements', 'pixades'],
            'mobiliari_deteriorat': ['faroles', 'bancs', 'senyals', 'paviment', 'papereres', 'parades'],
            'bruticia': ['terra', 'fulles', 'grafit'],
            'vandalisme': ['pintades'],
            'vegetacio': ['arbres', 'arbustos', 'gespa'],
            'infraestructura': ['carreteres', 'voreres', 'enllumenat']
        }
        
        if category_code not in valid_subcategories:
                from wtforms.validators import ValidationError
                raise ValidationError(_('Categoría no válida'))
        if subcategory_code not in valid_subcategories.get(category_code, []):
                from wtforms.validators import ValidationError
                raise ValidationError(_('Subcategoría no válida para esta categoría'))

