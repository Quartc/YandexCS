import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Queue(SqlAlchemyBase):
    __tablename__ = 'queue'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), unique=True)
    joined_at = sqlalchemy.Column(sqlalchemy.DateTime, default=sqlalchemy.func.now())
    is_in_match = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    user = orm.relationship("User", back_populates="queue_entry")

    def __repr__(self):
        return f'<Queue> {self.id} {self.user.username}'