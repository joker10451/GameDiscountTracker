"""
Database models for Game Discount Tracker Bot
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """User model for storing Telegram user information"""
    __tablename__ = 'users'
    
    id = db.Column(db.BigInteger, primary_key=True)  # Telegram user ID
    username = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    settings = db.Column(JSONB, default={})
    
    # Relationships
    subscriptions = db.relationship('Subscription', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User {self.id}: {self.username}>"


class Game(db.Model):
    """Game model for storing game information"""
    __tablename__ = 'games'
    
    id = db.Column(db.String(64), primary_key=True)  # Game ID from API
    title = db.Column(db.String(255), nullable=False)
    thumbnail = db.Column(db.String(512), nullable=True)
    details = db.Column(JSONB, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = db.relationship('Subscription', back_populates='game', cascade='all, delete-orphan')
    price_records = db.relationship('PriceRecord', back_populates='game', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Game {self.id}: {self.title}>"


class Subscription(db.Model):
    """Subscription model for storing user game subscriptions"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    game_id = db.Column(db.String(64), db.ForeignKey('games.id'), nullable=False)
    price_threshold = db.Column(db.Float, nullable=True)  # Optional price threshold for notifications
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='subscriptions')
    game = db.relationship('Game', back_populates='subscriptions')
    
    # Unique constraint to prevent duplicate subscriptions
    __table_args__ = (
        db.UniqueConstraint('user_id', 'game_id', name='unique_user_game_subscription'),
    )
    
    def __repr__(self):
        return f"<Subscription {self.id}: User {self.user_id} - Game {self.game_id}>"


class PriceRecord(db.Model):
    """Price record model for storing historical price data"""
    __tablename__ = 'price_records'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(64), db.ForeignKey('games.id'), nullable=False)
    store_id = db.Column(db.String(64), nullable=False)
    price = db.Column(db.Float, nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False, default=0)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    game = db.relationship('Game', back_populates='price_records')
    
    def __repr__(self):
        return f"<PriceRecord {self.id}: {self.game_id} - {self.store_id} - ${self.price}>"


class Store(db.Model):
    """Store model for caching store information"""
    __tablename__ = 'stores'
    
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    logo = db.Column(db.String(512), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Store {self.id}: {self.name}>"