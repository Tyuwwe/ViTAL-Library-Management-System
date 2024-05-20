from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from config import Config
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='covers')
app.config.from_object(Config)
CORS(app)  # 允许所有来源访问

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    
class Books(db.Model):
    __tablename__ = 'books'

    book_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    isbn = db.Column(db.String(20), unique=True)
    type = db.Column(db.String(50))
    author = db.Column(db.String(255))
    cover_image = db.Column(db.String(255))
    location = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1)
    description = db.Column(db.Text)
    published_date = db.Column(db.Date)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), server_onupdate=db.func.current_timestamp())

    def serialize(self):
        return {
            'book_id': self.book_id,
            'title': self.title,
            'isbn': self.isbn,
            'type': self.type,
            'author': self.author,
            'cover_image': self.cover_image,
            'location': self.location,
            'quantity': self.quantity,
            'description': self.description,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class ShoppingCart(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, primary_key=True)
    
class BorrowingRecord(db.Model):
    __tablename__ = 'borrowing_records'

    record_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    extension_count = db.Column(db.Integer, default=0)
    
    def serialize(self):
        return {
            'record_id': self.record_id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'borrow_date': self.borrow_date.isoformat() if self.borrow_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'extension_count': self.extension_count
        }
        
class Admins(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)

class Reservations(db.Model):
    __tablename__ = 'reservations'

    reservation_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id'), nullable=False)
    reservation_date = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    def serialize(self):
        return {
            'reservation_id': self.reservation_id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'reservation_date': self.reservation_date.isoformat() if self.reservation_date else None
        }

# 创建数据库和表
with app.app_context():
    db.create_all()

# 用户注册
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    password = data['password']
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = Users(username=username, password=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 用户登录
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    user = Users.query.filter_by(username=username).first()

    if user and bcrypt.check_password_hash(user.password, password):
        return jsonify({'message': 'Login successful!', 'user': username, 'userId': user.id}), 200
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

# 管理员登录
@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    admin = Admins.query.filter_by(username=username).first()

    if admin and bcrypt.check_password_hash(admin.password, password):
        return jsonify({'userId': admin.id, 'username': admin.username}), 200
    else:
        return jsonify({'error': 'Invalid username or password'}), 401
    
# 用户列表
@app.route('/api/users', methods=['GET'])
def get_users():
    search_keyword = request.args.get('search')
    if search_keyword:
        users = Users.query.filter(
            (Users.username.ilike(f'%{search_keyword}%'))
        ).all()
    else:
        users = Users.query.all()
    user_list = [{'id': user.id, 'username': user.username} for user in users]
    return jsonify(user_list), 200   

# 获取所有书籍列表
@app.route('/api/books', methods=['GET'])
def get_books():
    search_keyword = request.args.get('search')
    if search_keyword:
        books = Books.query.filter(
            (Books.title.ilike(f'%{search_keyword}%')) |
            (Books.author.ilike(f'%{search_keyword}%')) |
            (Books.description.ilike(f'%{search_keyword}%'))
        ).all()
    else:
        books = Books.query.all()
        
    book_list = [book.serialize() for book in books]
    return jsonify(book_list), 200

# 获取单个书籍的详细信息
@app.route('/api/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = Books.query.get(book_id)
    if book:
        return jsonify(book.serialize()), 200
    else:
        return jsonify({'error': 'Book not found'}), 404

# 获取推荐书籍
@app.route('/api/books/recommendations', methods=['GET'])
def get_recommendations():
    book_id = request.args.get('book_id')
    author = request.args.get('author')
    type = request.args.get('type')

    recommendations = Books.query.filter(
        ((Books.author == author) | (Books.type == type)) &
        (Books.book_id != book_id)
    ).limit(5).all()

    recommendation_list = [book.serialize() for book in recommendations]
    return jsonify(recommendation_list), 200

@app.route('/api/shopping_cart/add', methods=['POST'])
def add_to_shopping_cart():
    data = request.get_json()
    user_id = data.get('user_id')
    book_id = data.get('book_id')

    if user_id and book_id:
        # 检查购物车中是否已经存在相同的记录
        existing_item = ShoppingCart.query.filter_by(user_id=user_id, book_id=book_id).first()
        if existing_item:
            return jsonify({'message': 'Book already exists in Borrowing List'}), 400
        else:
            new_item = ShoppingCart(user_id=user_id, book_id=book_id)
            db.session.add(new_item)
            db.session.commit()
            return jsonify({'message': 'Book added to Borrowing List successfully'}), 200
    else:
        return jsonify({'error': 'Invalid user ID or book ID'}), 400

# 根据用户ID获取借阅列表
@app.route('/api/shopping_cart/<int:user_id>', methods=['GET'])
def get_borrowing_list(user_id):
    borrowing_list = ShoppingCart.query.filter_by(user_id=user_id).all()
    if borrowing_list:
        list_data = []
        for record in borrowing_list:
            book = Books.query.get(record.book_id)
            if book:
                book_data = {
                    'book_id': book.book_id,
                    'title': book.title,
                    'author': book.author,
                    'quantity': book.quantity
                }
                list_data.append(book_data)
        return jsonify(list_data), 200
    else:
        return jsonify({}), 200

# 获取某个用户的借书记录
@app.route('/api/borrowing_records/<int:user_id>', methods=['GET'])
def get_borrowing_records(user_id):
    borrowing_records = BorrowingRecord.query.filter_by(user_id=user_id).all()
    if borrowing_records:
        records = [record.serialize() for record in borrowing_records]
        return jsonify(records), 200
    else:
        return jsonify({'message': 'No borrowing records found for this user'}), 404

# 添加新书籍
@app.route('/api/books', methods=['POST'])
def add_book():
    data = request.get_json()
    new_book = Books(
        title=data['title'],
        author=data['author'],
        quantity=data['quantity'],
        isbn=data.get('isbn'),
        type=data.get('type'),
        cover_image=data.get('cover_image'),
        location=data.get('location'),
        description=data.get('description'),
        published_date=data.get('published_date')
    )
    db.session.add(new_book)
    db.session.commit()
    return jsonify({'message': 'Book added successfully!'}), 201

# 更新现有书籍
@app.route('/api/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.get_json()
    book = Books.query.get(book_id)
    if book:
        book.title = data['title']
        book.author = data['author']
        book.quantity = data['quantity']
        book.isbn = data.get('isbn')
        book.type = data.get('type')
        book.cover_image = data.get('cover_image')
        book.location = data.get('location')
        book.description = data.get('description')
        book.published_date = data.get('published_date')
        db.session.commit()
        return jsonify({'message': 'Book updated successfully!'}), 200
    else:
        return jsonify({'error': 'Book not found'}), 404

# 删除书籍
@app.route('/api/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    try:
        book = Books.query.get(book_id)
        if book:
            db.session.delete(book)
            db.session.commit()
            return jsonify({'message': 'Book deleted successfully!'}), 200
        else:
            return jsonify({'error': 'Book not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 删除Cart中图书
@app.route('/api/shopping_cart/<int:user_id>/<int:book_id>', methods=['DELETE'])
def delete_book_from_cart(user_id, book_id):
    try:
        item = ShoppingCart.query.filter_by(user_id=user_id, book_id=book_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            return jsonify({'message': 'Book removed from borrowing list successfully'}), 200
        else:
            return jsonify({'error': 'Book not found in borrowing list'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 修改密码
@app.route('/api/change_password', methods=['POST'])
def change_password():
    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('newPassword')
    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

    user = Users.query.get(user_id)
    if user:
        try:
            user.password = hashed_password
            db.session.commit()
            return jsonify({'message': 'Password changed successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    else:
        return jsonify({'error': 'User not found'}), 404
    
# 创建借书记录
@app.route('/api/borrowing_records', methods=['POST'])
def create_borrowing_record():
    data = request.get_json()
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    
    book = Books.query.get(book_id)
    book_title = book.title
    if book and book.quantity > 1:
        new_record = BorrowingRecord(
            user_id=user_id,
            book_id=book_id,
            borrow_date=datetime.utcnow(),
            return_date=datetime.utcnow() + timedelta(days=30),
            extension_count=0
        )
        book.quantity -= 1
        try:
            db.session.add(new_record)
            db.session.commit()
            return jsonify({'message': 'Borrowing record created successfully!'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    else:
        return jsonify({'error': f'Book {book_title} is not available for borrowing'}), 200

# 删除借书记录
@app.route('/api/borrowing_records/<int:record_id>', methods=['DELETE'])
def delete_borrowing_record(record_id):
    try:
        record = BorrowingRecord.query.get(record_id)
        if record:
            book = Books.query.get(record.book_id)
            if book:
                book.quantity += 1
            db.session.delete(record)
            db.session.commit()
            return jsonify({'message': 'Borrowing record deleted successfully'}), 200
        else:
            return jsonify({'error': 'Borrowing record not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 延长还书期限
@app.route('/api/borrowing_records/extend/<int:record_id>', methods=['PUT'])
def extend_borrowing_record(record_id):
    try:
        record = BorrowingRecord.query.get(record_id)
        if record:
            if record.extension_count < 3:
                record.return_date += timedelta(days=30)
                record.extension_count += 1
                db.session.commit()
                return jsonify({'message': 'Borrowing record extended successfully'}), 200
            else:
                return jsonify({'message': 'Maximum extension limit reached'}), 400
        else:
            return jsonify({'message': 'Borrowing record not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 某个用户的借书记录
@app.route('/api/user_borrowing_records/<int:user_id>', methods=['GET'])
def get_user_borrowing_records(user_id):
    try:
        user_borrowing_records = BorrowingRecord.query.filter_by(user_id=user_id).all()
        records = []
        for record in user_borrowing_records:
            book = Books.query.get(record.book_id)
            if book:
                book_info = {
                    'record_id': record.record_id,
                    'book_id': book.book_id,
                    'title': book.title,
                    'author': book.author,
                    'location': book.location,
                    'borrow_date': record.borrow_date.isoformat() if record.borrow_date else None,
                    'return_date': record.return_date.isoformat() if record.return_date else None,
                    'extension_count': record.extension_count
                }
                records.append(book_info)
        return jsonify(records), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 创建新的预定记录
@app.route('/api/reservations', methods=['POST'])
def create_reservation():
    data = request.get_json()
    user_id = data.get('user_id')
    book_id = data.get('book_id')

    if user_id and book_id:
        # 检查是否已预定该书
        existing_reservation = Reservations.query.filter_by(user_id=user_id, book_id=book_id).first()
        if existing_reservation:
            return jsonify({'message': 'Book already reserved'}), 400
        else:
            new_reservation = Reservations(user_id=user_id, book_id=book_id)
            try:
                db.session.add(new_reservation)
                db.session.commit()
                return jsonify({'message': 'Reservation created successfully!'}), 201
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': str(e)}), 400
    else:
        return jsonify({'error': 'Invalid user ID or book ID'}), 400

# 删除预定记录
@app.route('/api/reservations/<int:reservation_id>', methods=['DELETE'])
def delete_reservation(reservation_id):
    try:
        reservation = Reservations.query.get(reservation_id)
        if reservation:
            db.session.delete(reservation)
            db.session.commit()
            return jsonify({'message': 'Reservation deleted successfully'}), 200
        else:
            return jsonify({'error': 'Reservation not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    
# 查询用户的预定记录
@app.route('/api/reservations/user/<int:user_id>', methods=['GET'])
def get_user_reservations(user_id):
    reservations = Reservations.query.filter_by(user_id=user_id).all()
    if reservations:
        records = []
        for record in reservations:
            book = Books.query.get(record.book_id)
            if book:
                book_info = {
                    'reservation_id': record.reservation_id,
                    'book_id': book.book_id,
                    'title': book.title,
                    'author': book.author,
                    'quantity': book.quantity,
                    'reservation_date': record.reservation_date.isoformat() if record.reservation_date else None
                }
                records.append(book_info)
        return jsonify(records), 200
    else:
        return jsonify({'message': 'No reservations found for this user'}), 404

# 检查用户是否预定了某一本书
@app.route('/api/reservations/check', methods=['POST'])
def check_reservation():
    data = request.get_json()
    user_id = data.get('user_id')
    book_id = data.get('book_id')

    if user_id and book_id:
        reservation = Reservations.query.filter_by(user_id=user_id, book_id=book_id).first()
        if reservation:
            return jsonify({'reserved': True, 'reservation_id': reservation.reservation_id}), 200
        else:
            return jsonify({'reserved': False}), 200
    else:
        return jsonify({'error': 'Invalid user ID or book ID'}), 400

if __name__ == '__main__':
    app.run(debug=True)
