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
    
    def __init__(self, *args, **kwargs):
        super(InitiativeForm, self).__init__(*args, **kwargs)
        # Set category choices dynamically to support translations
        if has_request_context():
            self.category.choices = [
                ('limpieza', '🧹 ' + str(_('Cleaning'))),
                ('reciclaje', '♻️ ' + str(_('Recycling'))),
                ('espacios_verdes', '🌳 ' + str(_('Green Spaces'))),
                ('movilidad', '🚴 ' + str(_('Sustainable Mobility'))),
                ('educacion', '📚 ' + str(_('Environmental Education'))),
                ('cultura', '🎭 ' + str(_('Culture and Civics'))),
                ('social', '🤝 ' + str(_('Social Action')))
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
                ('social', '🤝 Social Action')
            ]

class InventoryForm(FlaskForm):
    category = SelectField(_l('Category'), validators=[DataRequired()])
    description = TextAreaField(_l('Description'), validators=[Optional(), Length(max=500)])
    latitude = StringField(_l('Latitude'), validators=[DataRequired()])
    longitude = StringField(_l('Longitude'), validators=[DataRequired()])
    address = StringField(_l('Address'), validators=[Optional()])
    image = FileField(_l('Photo'), validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(InventoryForm, self).__init__(*args, **kwargs)
        # Set category choices for palomas
        if has_request_context():
            self.category.choices = [
                ('excremento', '💩 ' + str(_('Excremento'))),
                ('nido', '🪺 ' + str(_('Nido'))),
                ('paloma', '🕊️ ' + str(_('Paloma'))),
                ('plumas', '🪶 ' + str(_('Plumas'))),
                ('otro', '📌 ' + str(_('Otro')))
            ]
        else:
            self.category.choices = [
                ('excremento', '💩 Excremento'),
                ('nido', '🪺 Nido'),
                ('paloma', '🕊️ Paloma'),
                ('plumas', '🪶 Plumas'),
                ('otro', '📌 Otro')
            ]

