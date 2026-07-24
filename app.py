from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-super-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///posts.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text)
    image_filename = db.Column(db.String(255))
    video_filename = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

ALLOWED_EXT = {'png','jpg','jpeg','gif','mp4','mov','avi','webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

@app.route('/', methods=['GET', 'POST'])
def index():
    # Auto delete old (2 weeks)
    cutoff = datetime.utcnow() - timedelta(days=14)
    old_posts = Post.query.filter(Post.timestamp < cutoff).all()
    for p in old_posts:
        db.session.delete(p)
    db.session.commit()

    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        image = request.files.get('image')
        video = request.files.get('video')

        image_fn = video_fn = None
        if image and allowed_file(image.filename):
            image_fn = secure_filename(image.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_fn))
        if video and allowed_file(video.filename):
            video_fn = secure_filename(video.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            video.save(os.path.join(app.config['UPLOAD_FOLDER'], video_fn))

        if message or image_fn or video_fn:
            new_post = Post(message=message, image_filename=image_fn, video_filename=video_fn)
            db.session.add(new_post)
            db.session.commit()
        return redirect('/')

    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Admin
ADMIN_PASS = "@Lordbeema1" 

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == ADMIN_PASS:
            if 'delete_id' in request.form:
                post = Post.query.get(int(request.form.get('delete_id')))
                if post:
                    db.session.delete(post)
                    db.session.commit()
            posts = Post.query.order_by(Post.timestamp.desc()).all()
            return render_template('admin.html', posts=posts)
    return render_template_string("""
        <h1>Admin Login</h1>
        <form method="post">
            <input type="password" name="password" placeholder="Password">
            <button type="submit">Login</button>
        </form>
    """)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
