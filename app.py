from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///posts.db')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text)
    image_filename = db.Column(db.String(255))
    video_filename = db.Column(db.String(255))
    ip = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

ALLOWED_EXT = {'png','jpg','jpeg','gif','mp4','mov','avi','webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

@app.route('/', methods=['GET', 'POST'])
def index():
    # Auto delete old posts (2 weeks)
    old = Post.query.filter(Post.timestamp < datetime.utcnow() - timedelta(days=14)).all()
    for p in old:
        # delete files if exist
        db.session.delete(p)
    db.session.commit()

    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        image = request.files.get('image')
        video = request.files.get('video')
        ip = request.remote_addr

        image_fn = video_fn = None
        if image and allowed_file(image.filename):
            image_fn = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_fn))
        if video and allowed_file(video.filename):
            video_fn = secure_filename(video.filename)
            video.save(os.path.join(app.config['UPLOAD_FOLDER'], video_fn))

        if message or image_fn or video_fn:
            new_post = Post(message=message, image_filename=image_fn, video_filename=video_fn, ip=ip)
            db.session.add(new_post)
            db.session.commit()
        return redirect('/')

    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === ADMIN ===
ADMIN_PASS = "youradminpassword123"   # CHANGE THIS

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASS:
            # delete logic
            if 'delete_id' in request.form:
                post = Post.query.get(int(request.form.get('delete_id')))
                if post:
                    db.session.delete(post)
                    db.session.commit()
            return render_template('admin.html', posts=Post.query.order_by(Post.timestamp.desc()).all())
    return render_template_string('<form method="post"><input type="password" name="password"><button>Login</button></form>')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
