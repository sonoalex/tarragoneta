from flask import has_request_context
from flask_wtf import FlaskForm
from flask_security.forms import RegisterForm
from flask_babel import gettext as _, lazy_gettext as _l
from wtforms import StringField, TextAreaField, DateField, SelectField, FileField
from wtforms.validators import DataRequired, Email, Length, Optional
from app.extensions import db
from app.models import User

class ExtendedRegisterForm(RegisterForm):
    username = StringField('Nombre de usuario', validators=[DataRequired(), Length(min=3, max=255)])
    
    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        
        # Check if username already exists
        if User.query.filter_by(username=self.username.data).first():
            self.username.errors.append('Este nombre de usuario ya está en uso')
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
                ('basura_desborda', '🗑️ ' + str(_('Overflowing Trash'))),
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
                ('basura_desborda', '🗑️ Overflowing Trash'),
                ('vertidos', '💧 Dumping')
            ]

class InventoryForm(FlaskForm):
    category = SelectField(_l('Category'), validators=[DataRequired()])
    subcategory = SelectField(_l('Subcategory'), validators=[DataRequired()])
    description = TextAreaField(_l('Description'), validators=[Optional(), Length(max=500)])
    latitude = StringField(_l('Latitude'), validators=[DataRequired()])
    longitude = StringField(_l('Longitude'), validators=[DataRequired()])
    address = StringField(_l('Address'), validators=[Optional()])
    image = FileField(_l('Photo'), validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(InventoryForm, self).__init__(*args, **kwargs)
        # Set main category choices
        if has_request_context():
            self.category.choices = [
                ('palomas', '🕊️ ' + str(_('Palomas'))),
                ('basura', '🗑️ ' + str(_('Basura')))
            ]
            # Set all possible subcategories (for validation)
            # These will be filtered by JavaScript on the client side
            self.subcategory.choices = [
                # Palomas subcategories
                ('nido', '🪺 ' + str(_('Nido'))),
                ('excremento', '💩 ' + str(_('Excremento'))),
                ('plumas', '🪶 ' + str(_('Plumas'))),
                # Basura subcategories
                ('basura_desborda', '🗑️ ' + str(_('Basura Desbordada'))),
                ('vertidos', '💧 ' + str(_('Vertidos')))
            ]
        else:
            self.category.choices = [
                ('palomas', '🕊️ Palomas'),
                ('basura', '🗑️ Basura')
            ]
            self.subcategory.choices = [
                ('nido', '🪺 Nido'),
                ('excremento', '💩 Excremento'),
                ('plumas', '🪶 Plumas'),
                ('basura_desborda', '🗑️ Basura Desbordada'),
                ('vertidos', '💧 Vertidos')
            ]
    
    def validate_subcategory(self, field):
        """Custom validation to ensure subcategory matches selected category"""
        category = self.category.data
        subcategory = field.data
        
        # Define valid subcategories for each category
        valid_subcategories = {
            'palomas': ['nido', 'excremento', 'plumas'],
            'basura': ['basura_desborda', 'vertidos']
        }
        
        if category and subcategory:
            if category not in valid_subcategories:
                from wtforms.validators import ValidationError
                raise ValidationError(_('Categoría no válida'))
            if subcategory not in valid_subcategories.get(category, []):
                from wtforms.validators import ValidationError
                raise ValidationError(_('Subcategoría no válida para esta categoría'))

