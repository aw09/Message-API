import logging
from operator import is_
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Api, Resource, abort
from datetime import date, datetime
import pytz, sys
from sqlalchemy.orm import relationship, aliased
import os
from flask_jwt import JWT, jwt_required, current_identity
from hmac import compare_digest

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
db = SQLAlchemy(app=app, session_options={"autoflush": False})
session = db.session
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
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    unread_count = db.Column(db.Integer)

    room = relationship("Room", foreign_keys=[room_id])
    user = relationship("User", foreign_keys=[user_id])

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer,db.ForeignKey('room.id'))
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    created_on = db.Column(db.DateTime, server_default=db.func.now())
    read_on = db.Column(db.DateTime)

    room = relationship("Room", foreign_keys=[room_id])
    user = relationship("User", foreign_keys=[user_id])

# ===============================================
# Schema

class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "username")

class RoomSchema(ma.Schema):
    class Meta:
        fields = ("id", "last_message", "unread_count", "name")

class MemberOfRoomSchema(ma.Schema):
    class Meta:
        fields = ("id", "room_id", "user_id", "unread_count")

class MessageSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_id", "content", "created_on", "read_on")

# ===============================================

users_schema = UserSchema(many=True)

rooms_schema = RoomSchema(many=True)

messages_schema = MessageSchema(many=True)

# ===============================================

class Register(Resource):
    def post(self):
        username = request.json['username']
        password = request.json['password']
        checkUsername = User.query.filter_by(username=username).first()
        if checkUsername is not None:
            return ({"message": "Already exists."}, 409)     

        new_user = User(
            username = username,
            password = hash(password)
        )
        session.add(new_user)
        session.commit()
        return {"status": "registration completed."}

class OtherUsers(Resource):
    @jwt_required()
    def get(self):
        other_user = User.query.filter(User.id != current_identity.id)
        return users_schema.dump(other_user)

class AllUsers(Resource):
    def get(self):
        users = User.query.all()
        return users_schema.dump(users)

class ListRoom(Resource):
    @jwt_required()
    def get(self):
        user_id = current_identity.id
        user = aliased(MemberOfRoom)
        other_user = aliased(MemberOfRoom)

        rooms = session.query(Room.id, Room.last_message,  user.unread_count, User.username.label('name')) \
                    .filter(
                        (Room.id == user.room_id)
                        & (user.user_id == user_id)
                        & (other_user.room_id == Room.id)
                        & (other_user.user_id != user_id)
                        & (User.id == other_user.user_id)
                    )
        return rooms_schema.dump(rooms)
class RoomResource(Resource):
    @jwt_required()
    def get(self, room_id):
        user_id = current_identity.id
        member = MemberOfRoom.query.filter_by(user_id = user_id, room_id = room_id).first()
        if member is None:
            return ({"message": "Invalid input."}, 422)
        
        member.unread_count = 0
        messages = Message.query.filter(Message.room_id == room_id)
        unread_messages = Message.query.filter((Message.room_id == room_id) \
                                                & (Message.user_id != user_id) \
                                                & (Message.read_on.is_(None)) ) \
                                        .update({'read_on': datetime.now(tz=pytz.timezone('Asia/Jakarta'))})
        session.commit()

        return messages_schema.dump(messages)
        
class MessageResource(Resource):
    @jwt_required()
    def post(self, receiver_id):
        sender_id = current_identity.id
        
        if sender_id == receiver_id:
            return ({"message": "Invalid input. Cannot send message to yourself"}, 422)

        room = checkRoom2User(sender_id, receiver_id)

        if room is None:
            room = newRoom(sender_id, receiver_id)
        
        content = request.json['content']
        message = Message(
            user_id = sender_id,
            room_id = room.id,
            content = content
        )
        room.last_message = message.content
        
        receiver = MemberOfRoom.query.filter_by(id=receiver_id, room_id=room.id).first()
        logging.debug("receiver = "+str(receiver.id))
        receiver.unread_count += 1
        session.add(message)
        session.commit()
        return {"status": "message sent."}

# ===============================================
def authenticate(username, password):
    user = User.query.filter_by(username=username).first()
    print(user.password)
    print(password)
    if user and compare_digest(user.password, str(hash(password))):
        return user

def identity(payload):
    user_id = payload['identity']
    return User.query.filter_by(id=user_id).first()

jwt = JWT(app, authenticate, identity)

def checkRoom2User(user_id_1, user_id_2):
    room_id_1 = session.query(MemberOfRoom.room_id).filter(MemberOfRoom.user_id==user_id_1)
    room_id_2 = session.query(MemberOfRoom.room_id).filter(MemberOfRoom.user_id==user_id_2)
    room = session.query(Room).filter((Room.id.in_(room_id_1)) & (Room.id.in_(room_id_2))).first()
    return room


def newRoom(user_id_1, user_id_2):
    new_room = Room(
        last_message=''
    )
    session.add(new_room)
    session.commit()

    addMember(new_room.id, user_id_1)
    addMember(new_room.id, user_id_2)

    logging.debug(new_room)
    return new_room

def addMember(room_id, id_member):
    new_member = MemberOfRoom(
        room_id = room_id,
        user_id = id_member,
        unread_count = 0
    )
    session.add(new_member)
    session.commit()
    

# ===============================================
api.add_resource(AllUsers, '/')

api.add_resource(Register, '/user')
api.add_resource(OtherUsers, '/users')
api.add_resource(ListRoom, '/rooms')
api.add_resource(RoomResource, '/room/<int:room_id>')
api.add_resource(MessageResource, '/message/<int:receiver_id>')

if __name__ == '__main__':
    db.create_all()
    port = sys.argv[1] if len(sys.argv) > 1 else 2000
    app.run(host='0.0.0.0', port=port, debug=True)