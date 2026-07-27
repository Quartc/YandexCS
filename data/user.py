import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    steam_id = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False, index=True)
    steam_id_64 = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
    username = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    avatar_url = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    profile_url = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=sqlalchemy.func.now())
    queue_entry = orm.relationship("Queue", back_populates="user", uselist=False)

    def __repr__(self):
        return f'<User> {self.id} {self.username} ({self.steam_id})'