from uliweb.form import *

class ManageForm(Form):
    static_url = StringField(label='Static URL prefix:', required=True, key='ASGI_MIDDLEWARES/staticfiles')
