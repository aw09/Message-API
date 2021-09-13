from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Api, Resource

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app)

# ===============================================
# Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(12), unique=True)
    password = db.Column(db.String(50))

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_message = db.Column(db.Text)

class MemberOfRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_room = db.Column(db.Integer, db.ForeignKey('room.id'))
    id_user = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_read = db.Column(db.DateTime)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.String(12),db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    created_on = db.Column(db.DateTime, server_default=db.func.now())

# ===============================================
# Schema

class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "username")

class RoomSchema(ma.Schema):
    class Meta:
        fields = ("id", "last_message")

class MemberOfRoomSchema(ma.Schema):
    class Meta:
        fields = ("id", "id_room", "id_user", "last_read")

class MessageSchema(ma.Schema):
    class Meta:
        fields = ("id", "id_user", "content")

# ===============================================

user_schema = UserSchema()
users_schema = UserSchema(many=True)

room_schema = RoomSchema()
rooms_schema = RoomSchema(many=True)

member_schema = MemberOfRoomSchema()
members_schema = MemberOfRoomSchema(many=True)

message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)

# ===============================================
class ListAllUsers(Resource):
    def get(self):
        users = User.query.all()
        return users_schema.dump(users)


# ===============================================

api.add_resource(ListAllUsers, '/users')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2000)