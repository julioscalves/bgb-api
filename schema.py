from app import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40))
    is_banned = db.Column(db.Boolean)
    blocked_until = db.Column(db.DateTime)

    def __repr__(self):
        return f'[{self.id}] {self.username}'


class Ad(db.Model):
    __tablename__ = 'ads'

    id = db.Column(db.String(9), primary_key=True)
    content = db.Column(db.JSON)

    def __repr__(self):
        return f'[{self.id}]'
