"""
SHRAMIC NETWORKS CMS - Complete Flask Application
==================================================
Single file Flask CMS with full admin control
"""

import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

# =============================================================================
# FLASK APP CONFIGURATION
# =============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/cms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Get absolute paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')

# Ensure folders exist
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Update database URI to use absolute path
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(INSTANCE_DIR, "cms.db")}'

db = SQLAlchemy(app)

# =============================================================================
# DATABASE MODELS
# =============================================================================

class User(db.Model):
    """Admin user model"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class PageSection(db.Model):
    """Dynamic page sections (Home, About, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(50), nullable=False)  # home, about, contact
    section_name = db.Column(db.String(100), nullable=False)  # hero, about, features
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    button_text = db.Column(db.String(100))
    button_link = db.Column(db.String(200))
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BlogCategory(db.Model):
    """Blog categories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    posts = db.relationship('BlogPost', backref='category', lazy=True)


class BlogPost(db.Model):
    """Blog posts with full content"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    excerpt = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    featured_image = db.Column(db.String(500))
    author = db.Column(db.String(100), default='Admin')
    category_id = db.Column(db.Integer, db.ForeignKey('blog_category.id'))
    tags = db.Column(db.String(200))  # Comma-separated
    meta_description = db.Column(db.String(160))
    read_time = db.Column(db.Integer, default=5)  # minutes
    is_published = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Testimonial(db.Model):
    """Customer testimonials"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    role = db.Column(db.String(100))  # e.g., "Farmer", "Wheat Farmer"
    avatar_url = db.Column(db.String(500))
    testimonial = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)  # 1-5 stars
    
    # Impact metrics
    yield_increase = db.Column(db.String(50))
    water_saved = db.Column(db.String(50))
    income_increase = db.Column(db.String(50))
    
    video_url = db.Column(db.String(500))  # YouTube embed
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TeamMember(db.Model):
    """Team members for About page"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(500))
    email = db.Column(db.String(120))
    linkedin = db.Column(db.String(200))
    twitter = db.Column(db.String(200))
    order_index = db.Column(db.Integer, default=0)
    is_leadership = db.Column(db.Boolean, default=False)  # Show in leadership section
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Statistic(db.Model):
    """Homepage statistics"""
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(50), nullable=False)
    suffix = db.Column(db.String(20))  # e.g., '+', '%', 'Cr'
    icon = db.Column(db.String(100))  # FontAwesome icon class
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


class Settings(db.Model):
    """Site-wide settings"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Feature(db.Model):
    """Features/Services cards"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))  # Icon class
    image_url = db.Column(db.String(500))
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


# =============================================================================
# AUTHENTICATION DECORATOR
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access admin panel.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_setting(key, default=''):
    """Get setting value by key"""
    setting = Settings.query.filter_by(key=key).first()
    return setting.value if setting else default


def update_setting(key, value, description=''):
    """Update or create setting"""
    setting = Settings.query.filter_by(key=key).first()
    if setting:
        setting.value = value
        setting.updated_at = datetime.utcnow()
    else:
        setting = Settings(key=key, value=value, description=description)
        db.session.add(setting)
    db.session.commit()


def create_slug(text):
    """Create URL-friendly slug"""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def init_default_data():
    """Initialize default data if database is empty"""
    try:
        # Create admin user if doesn't exist
        if not User.query.first():
            admin = User(
                username='admin',
                email='admin@shramic.com'
            )
            admin.set_password('admin123')  # Change this!
            db.session.add(admin)
            print("✓ Admin user created: username='admin', password='admin123'")
        
        # Create default settings
        if not Settings.query.first():
            default_settings = [
                ('site_title', 'Shramic Networks', 'Website title'),
                ('site_tagline', 'Empowering Agriculture Through Innovation', 'Website tagline'),
                ('contact_email', 'shramicnetworks@gmail.com', 'Contact email'),
                ('contact_phone', '+91 98765 43210', 'Contact phone'),
                ('contact_address', 'Bengaluru, Karnataka, India', 'Contact address'),
                ('facebook_url', '#', 'Facebook URL'),
                ('twitter_url', '#', 'Twitter URL'),
                ('linkedin_url', '#', 'LinkedIn URL'),
                ('instagram_url', 'https://www.instagram.com/shramic.info', 'Instagram URL'),
                ('github_url', 'https://github.com/Amit-Ashok-Swain', 'GitHub URL'),
            ]
            for key, value, desc in default_settings:
                setting = Settings(key=key, value=value, description=desc)
                db.session.add(setting)
            print("✓ Default settings created")
        
        # Create default blog categories
        if not BlogCategory.query.first():
            categories = [
                ('Technology', 'technology', 'Agricultural technology and innovation'),
                ('Sustainability', 'sustainability', 'Sustainable farming practices'),
                ('Training', 'training', 'Farmer training and education'),
                ('Market', 'market', 'Market insights and trends'),
            ]
            for name, slug, desc in categories:
                cat = BlogCategory(name=name, slug=slug, description=desc)
                db.session.add(cat)
            print("✓ Blog categories created")
        
        # Create default statistics
        if not Statistic.query.first():
            stats = [
                ('Farmers Empowered', '50K', '+', 'fas fa-users', 1),
                ('Average Yield Increase', '40', '%', 'fas fa-chart-line', 2),
                ('Additional Income Generated', '₹2.5', 'Cr', 'fas fa-rupee-sign', 3),
                ('Satisfaction Rate', '95', '%', 'fas fa-smile', 4),
            ]
            for label, value, suffix, icon, order in stats:
                stat = Statistic(label=label, value=value, suffix=suffix, icon=icon, order_index=order)
                db.session.add(stat)
            print("✓ Statistics created")
        
        db.session.commit()
        print("✓ Database initialized successfully!")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing database: {e}")


# =============================================================================
# PUBLIC ROUTES
# =============================================================================

@app.route('/')
def index():
    """Home page"""
    try:
        hero = PageSection.query.filter_by(page='home', section_name='hero', is_active=True).first()
        about_cards = PageSection.query.filter_by(page='home', section_name='about_card', is_active=True).order_by(PageSection.order_index).all()
        features = Feature.query.filter_by(is_active=True).order_by(Feature.order_index).all()
        stats = Statistic.query.filter_by(is_active=True).order_by(Statistic.order_index).all()
        
        return render_template('public/index.html',
            hero=hero,
            about_cards=about_cards,
            features=features,
            stats=stats
        )
    except Exception as e:
        app.logger.error(f"Error loading home page: {e}")
        return render_template('public/index.html', hero=None, about_cards=[], features=[], stats=[])


@app.route('/about')
def about():
    """About page with team"""
    try:
        story = PageSection.query.filter_by(page='about', section_name='story', is_active=True).first()
        mission = PageSection.query.filter_by(page='about', section_name='mission', is_active=True).first()
        vision = PageSection.query.filter_by(page='about', section_name='vision', is_active=True).first()
        values = PageSection.query.filter_by(page='about', section_name='value', is_active=True).order_by(PageSection.order_index).all()
        leadership = TeamMember.query.filter_by(is_leadership=True, is_active=True).order_by(TeamMember.order_index).all()
        team = TeamMember.query.filter_by(is_leadership=False, is_active=True).order_by(TeamMember.order_index).all()
        
        return render_template('public/about.html',
            story=story,
            mission=mission,
            vision=vision,
            values=values,
            leadership=leadership,
            team=team
        )
    except Exception as e:
        app.logger.error(f"Error loading about page: {e}")
        return render_template('public/about.html', story=None, mission=None, vision=None, values=[], leadership=[], team=[])


@app.route('/blog')
def blog():
    """Blog listing page"""
    try:
        page = request.args.get('page', 1, type=int)
        category_slug = request.args.get('category', None)
        
        query = BlogPost.query.filter_by(is_published=True)
        
        if category_slug:
            category = BlogCategory.query.filter_by(slug=category_slug).first()
            if category:
                query = query.filter_by(category_id=category.id)
        
        posts = query.order_by(BlogPost.published_at.desc()).paginate(
            page=page, per_page=9, error_out=False
        )
        
        categories = BlogCategory.query.all()
        featured_post = BlogPost.query.filter_by(is_published=True, is_featured=True).first()
        
        return render_template('public/blog.html',
            posts=posts,
            categories=categories,
            featured_post=featured_post,
            current_category=category_slug
        )
    except Exception as e:
        app.logger.error(f"Error loading blog page: {e}")
        return render_template('public/blog.html', posts=None, categories=[], featured_post=None)


@app.route('/blog/<slug>')
def blog_detail(slug):
    """Single blog post detail page"""
    try:
        post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
        
        # Increment views
        post.views += 1
        db.session.commit()
        
        # Get related posts from same category
        related_posts = BlogPost.query.filter(
            BlogPost.id != post.id,
            BlogPost.category_id == post.category_id,
            BlogPost.is_published == True
        ).order_by(db.func.random()).limit(3).all()
        
        return render_template('public/blog_detail.html',
            post=post,
            related_posts=related_posts
        )
    except Exception as e:
        app.logger.error(f"Error loading blog detail: {e}")
        abort(404)


@app.route('/testimonials')
def testimonials():
    """Testimonials page"""
    try:
        all_testimonials = Testimonial.query.filter_by(is_active=True).order_by(Testimonial.order_index).all()
        featured = Testimonial.query.filter_by(is_active=True, is_featured=True).first()
        stats = Statistic.query.filter_by(is_active=True).order_by(Statistic.order_index).all()
        
        return render_template('public/testimonial.html',
            testimonials=all_testimonials,
            featured=featured,
            stats=stats
        )
    except Exception as e:
        app.logger.error(f"Error loading testimonials page: {e}")
        return render_template('public/testimonial.html', testimonials=[], featured=None, stats=[])


@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('public/contact.html')


# =============================================================================
# ADMIN AUTHENTICATION ROUTES
# =============================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                flash('Login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid username or password', 'danger')
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash('An error occurred during login', 'danger')
    
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))


# =============================================================================
# ADMIN DASHBOARD
# =============================================================================

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    try:
        stats = {
            'total_posts': BlogPost.query.count(),
            'published_posts': BlogPost.query.filter_by(is_published=True).count(),
            'total_testimonials': Testimonial.query.filter_by(is_active=True).count(),
            'team_members': TeamMember.query.filter_by(is_active=True).count(),
        }
        
        recent_posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(5).all()
        recent_testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html',
            stats=stats,
            recent_posts=recent_posts,
            recent_testimonials=recent_testimonials
        )
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard', 'danger')
        return render_template('admin/dashboard.html', stats={}, recent_posts=[], recent_testimonials=[])


# =============================================================================
# ADMIN - HOME PAGE MANAGEMENT
# =============================================================================

@app.route('/admin/home', methods=['GET', 'POST'])
@login_required
def admin_edit_home():
    """Edit home page content"""
    if request.method == 'POST':
        try:
            # Update hero section
            hero = PageSection.query.filter_by(page='home', section_name='hero').first()
            if not hero:
                hero = PageSection(page='home', section_name='hero')
                db.session.add(hero)
            
            hero.title = request.form.get('hero_title')
            hero.content = request.form.get('hero_content')
            hero.image_url = request.form.get('hero_image')
            hero.button_text = request.form.get('hero_button_text')
            hero.button_link = request.form.get('hero_button_link')
            
            db.session.commit()
            flash('Home page updated successfully!', 'success')
            return redirect(url_for('admin_edit_home'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating home page: {e}")
            flash(f'Error: {str(e)}', 'danger')
    
    hero = PageSection.query.filter_by(page='home', section_name='hero').first()
    about_cards = PageSection.query.filter_by(page='home', section_name='about_card').order_by(PageSection.order_index).all()
    features = Feature.query.order_by(Feature.order_index).all()
    
    return render_template('admin/edit_home.html',
        hero=hero,
        about_cards=about_cards,
        features=features
    )


# =============================================================================
# ADMIN - ABOUT PAGE MANAGEMENT
# =============================================================================

@app.route('/admin/about', methods=['GET', 'POST'])
@login_required
def admin_edit_about():
    """Edit about page content"""
    if request.method == 'POST':
        try:
            section = request.form.get('section')
            
            # Update specific section
            page_section = PageSection.query.filter_by(page='about', section_name=section).first()
            if not page_section:
                page_section = PageSection(page='about', section_name=section)
                db.session.add(page_section)
            
            page_section.title = request.form.get('title')
            page_section.content = request.form.get('content')
            page_section.image_url = request.form.get('image_url')
            
            db.session.commit()
            flash(f'{section.title()} section updated successfully!', 'success')
            return redirect(url_for('admin_edit_about'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating about page: {e}")
            flash(f'Error: {str(e)}', 'danger')
    
    story = PageSection.query.filter_by(page='about', section_name='story').first()
    mission = PageSection.query.filter_by(page='about', section_name='mission').first()
    vision = PageSection.query.filter_by(page='about', section_name='vision').first()
    values = PageSection.query.filter_by(page='about', section_name='value').order_by(PageSection.order_index).all()
    
    return render_template('admin/edit_about.html',
        story=story,
        mission=mission,
        vision=vision,
        values=values
    )


# =============================================================================
# ADMIN - BLOG MANAGEMENT
# =============================================================================

@app.route('/admin/blog')
@login_required
def admin_manage_blog():
    """Manage all blog posts"""
    try:
        page = request.args.get('page', 1, type=int)
        posts = BlogPost.query.order_by(BlogPost.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        categories = BlogCategory.query.all()
        
        return render_template('admin/manage_blog.html',
            posts=posts,
            categories=categories
        )
    except Exception as e:
        app.logger.error(f"Error loading blog management: {e}")
        flash('Error loading blog posts', 'danger')
        return render_template('admin/manage_blog.html', posts=None, categories=[])


@app.route('/admin/blog/new', methods=['GET', 'POST'])
@app.route('/admin/blog/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_blog(id=None):
    """Create or edit blog post"""
    post = BlogPost.query.get(id) if id else None
    
    if request.method == 'POST':
        try:
            if not post:
                post = BlogPost()
                db.session.add(post)
            
            post.title = request.form.get('title')
            post.slug = create_slug(request.form.get('slug') or request.form.get('title'))
            post.excerpt = request.form.get('excerpt')
            post.content = request.form.get('content')
            post.featured_image = request.form.get('featured_image')
            post.author = request.form.get('author', 'Admin')
            post.category_id = request.form.get('category_id')
            post.tags = request.form.get('tags')
            post.meta_description = request.form.get('meta_description')
            post.read_time = request.form.get('read_time', 5, type=int)
            post.is_published = request.form.get('is_published') == 'on'
            post.is_featured = request.form.get('is_featured') == 'on'
            
            if post.is_published and not post.published_at:
                post.published_at = datetime.utcnow()
            
            db.session.commit()
            flash('Blog post saved successfully!', 'success')
            return redirect(url_for('admin_manage_blog'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving blog post: {e}")
            flash(f'Error: {str(e)}', 'danger')
    
    categories = BlogCategory.query.all()
    return render_template('admin/edit_blog.html', post=post, categories=categories)


@app.route('/admin/blog/delete/<int:id>', methods=['POST'])
@login_required
def admin_delete_blog(id):
    """Delete blog post"""
    try:
        post = BlogPost.query.get_or_404(id)
        db.session.delete(post)
        db.session.commit()
        flash('Blog post deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting blog post: {e}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin_manage_blog'))


# =============================================================================
# ADMIN - TESTIMONIALS MANAGEMENT
# =============================================================================

@app.route('/admin/testimonials')
@login_required
def admin_manage_testimonials():
    """Manage testimonials"""
    try:
        testimonials = Testimonial.query.order_by(Testimonial.order_index).all()
        return render_template('admin/manage_testimonials.html', testimonials=testimonials)
    except Exception as e:
        app.logger.error(f"Error loading testimonials: {e}")
        flash('Error loading testimonials', 'danger')
        return render_template('admin/manage_testimonials.html', testimonials=[])


@app.route('/admin/testimonials/new', methods=['GET', 'POST'])
@app.route('/admin/testimonials/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_testimonial(id=None):
    """Create or edit testimonial"""
    testimonial = Testimonial.query.get(id) if id else None
    
    if request.method == 'POST':
        try:
            if not testimonial:
                testimonial = Testimonial()
                db.session.add(testimonial)
            
            testimonial.name = request.form.get('name')
            testimonial.location = request.form.get('location')
            testimonial.role = request.form.get('role')
            testimonial.avatar_url = request.form.get('avatar_url')
            testimonial.testimonial = request.form.get('testimonial')
            testimonial.rating = request.form.get('rating', 5, type=int)
            testimonial.yield_increase = request.form.get('yield_increase')
            testimonial.water_saved = request.form.get('water_saved')
            testimonial.income_increase = request.form.get('income_increase')
            testimonial.video_url = request.form.get('video_url')
            testimonial.is_featured = request.form.get('is_featured') == 'on'
            testimonial.is_active = request.form.get('is_active') == 'on'
            testimonial.order_index = request.form.get('order_index', 0, type=int)
            
            db.session.commit()
            flash('Testimonial saved successfully!', 'success')
            return redirect(url_for('admin_manage_testimonials'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving testimonial: {e}")
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('admin/edit_testimonial.html', testimonial=testimonial)


@app.route('/admin/testimonials/delete/<int:id>', methods=['POST'])
@login_required
def admin_delete_testimonial(id):
    """Delete testimonial"""
    try:
        testimonial = Testimonial.query.get_or_404(id)
        db.session.delete(testimonial)
        db.session.commit()
        flash('Testimonial deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting testimonial: {e}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin_manage_testimonials'))


# =============================================================================
# ADMIN - TEAM MANAGEMENT
# =============================================================================

@app.route('/admin/team')
@login_required
def admin_manage_team():
    """Manage team members"""
    try:
        team_members = TeamMember.query.order_by(TeamMember.order_index).all()
        return render_template('admin/manage_team.html', team_members=team_members)
    except Exception as e:
        app.logger.error(f"Error loading team members: {e}")
        flash('Error loading team members', 'danger')
        return render_template('admin/manage_team.html', team_members=[])


@app.route('/admin/team/new', methods=['GET', 'POST'])
@app.route('/admin/team/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_team(id=None):
    """Create or edit team member"""
    member = TeamMember.query.get(id) if id else None
    
    if request.method == 'POST':
        try:
            if not member:
                member = TeamMember()
                db.session.add(member)
            
            member.name = request.form.get('name')
            member.position = request.form.get('position')
            member.bio = request.form.get('bio')
            member.photo_url = request.form.get('photo_url')
            member.email = request.form.get('email')
            member.linkedin = request.form.get('linkedin')
            member.twitter = request.form.get('twitter')
            member.is_leadership = request.form.get('is_leadership') == 'on'
            member.is_active = request.form.get('is_active') == 'on'
            member.order_index = request.form.get('order_index', 0, type=int)
            
            db.session.commit()
            flash('Team member saved successfully!', 'success')
            return redirect(url_for('admin_manage_team'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving team member: {e}")
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('admin/edit_team.html', member=member)


@app.route('/admin/team/delete/<int:id>', methods=['POST'])
@login_required
def admin_delete_team(id):
    """Delete team member"""
    try:
        member = TeamMember.query.get_or_404(id)
        db.session.delete(member)
        db.session.commit()
        flash('Team member deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting team member: {e}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin_manage_team'))


# =============================================================================
# ADMIN - STATISTICS MANAGEMENT
# =============================================================================

@app.route('/admin/stats', methods=['GET', 'POST'])
@login_required
def admin_manage_stats():
    """Manage homepage statistics"""
    if request.method == 'POST':
        try:
            stat_id = request.form.get('stat_id')
            
            if stat_id:
                stat = Statistic.query.get(stat_id)
            else:
                stat = Statistic()
                db.session.add(stat)
            
            stat.label = request.form.get('label')
            stat.value = request.form.get('value')
            stat.suffix = request.form.get('suffix')
            stat.icon = request.form.get('icon')
            stat.order_index = request.form.get('order_index', 0, type=int)
            stat.is_active = request.form.get('is_active') == 'on'
            
            db.session.commit()
            flash('Statistic saved successfully!', 'success')
            return redirect(url_for('admin_manage_stats'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving statistic: {e}")
            flash(f'Error: {str(e)}', 'danger')
    
    stats = Statistic.query.order_by(Statistic.order_index).all()
    return render_template('admin/manage_stats.html', stats=stats)


@app.route('/admin/stats/delete/<int:id>', methods=['POST'])
@login_required
def admin_delete_stat(id):
    """Delete statistic"""
    try:
        stat = Statistic.query.get_or_404(id)
        db.session.delete(stat)
        db.session.commit()
        flash('Statistic deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting statistic: {e}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin_manage_stats'))


# =============================================================================
# ADMIN - SETTINGS
# =============================================================================

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    """Manage site settings"""
    if request.method == 'POST':
        try:
            settings_data = {
                'site_title': request.form.get('site_title'),
                'site_tagline': request.form.get('site_tagline'),
                'contact_email': request.form.get('contact_email'),
                'contact_phone': request.form.get('contact_phone'),
                'contact_address': request.form.get('contact_address'),
                'facebook_url': request.form.get('facebook_url'),
                'twitter_url': request.form.get('twitter_url'),
                'linkedin_url': request.form.get('linkedin_url'),
                'instagram_url': request.form.get('instagram_url'),
                'github_url': request.form.get('github_url'),
            }
            
            for key, value in settings_data.items():
                update_setting(key, value)
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('admin_settings'))
        except Exception as e:
            app.logger.error(f"Error updating settings: {e}")
            flash(f'Error: {str(e)}', 'danger')
    
    settings = {
        'site_title': get_setting('site_title'),
        'site_tagline': get_setting('site_tagline'),
        'contact_email': get_setting('contact_email'),
        'contact_phone': get_setting('contact_phone'),
        'contact_address': get_setting('contact_address'),
        'facebook_url': get_setting('facebook_url'),
        'twitter_url': get_setting('twitter_url'),
        'linkedin_url': get_setting('linkedin_url'),
        'instagram_url': get_setting('instagram_url'),
        'github_url': get_setting('github_url'),
    }
    
    return render_template('admin/settings.html', settings=settings)


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('public/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return render_template('public/500.html'), 500


@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 errors"""
    return render_template('public/404.html'), 403


# =============================================================================
# TEMPLATE FILTERS
# =============================================================================

@app.template_filter('datetime')
def format_datetime(value, format='%B %d, %Y'):
    """Format datetime objects"""
    if value is None:
        return ''
    return value.strftime(format)


@app.template_filter('truncate_words')
def truncate_words(text, length=50):
    """Truncate text to specified number of words"""
    if not text:
        return ''
    words = text.split()
    if len(words) <= length:
        return text
    return ' '.join(words[:length]) + '...'


# =============================================================================
# CONTEXT PROCESSOR
# =============================================================================

@app.context_processor
def inject_settings():
    """Inject settings into all templates"""
    try:
        return {
            'site_title': get_setting('site_title', 'Shramic Networks'),
            'site_tagline': get_setting('site_tagline', 'Empowering Agriculture Through Innovation'),
            'contact_email': get_setting('contact_email'),
            'contact_phone': get_setting('contact_phone'),
            'contact_address': get_setting('contact_address'),
            'facebook_url': get_setting('facebook_url'),
            'twitter_url': get_setting('twitter_url'),
            'linkedin_url': get_setting('linkedin_url'),
            'instagram_url': get_setting('instagram_url'),
            'github_url': get_setting('github_url'),
        }
    except:
        return {}


# =============================================================================
# API ENDPOINTS (Optional)
# =============================================================================

@app.route('/api/blog/search')
def api_blog_search():
    """Search blog posts"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify([])
        
        posts = BlogPost.query.filter(
            BlogPost.is_published == True,
            db.or_(
                BlogPost.title.contains(query),
                BlogPost.content.contains(query),
                BlogPost.tags.contains(query)
            )
        ).limit(10).all()
        
        results = [{
            'id': post.id,
            'title': post.title,
            'slug': post.slug,
            'excerpt': post.excerpt,
            'url': url_for('blog_detail', slug=post.slug)
        } for post in posts]
        
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Search error: {e}")
        return jsonify([]), 500


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db():
    """Initialize database"""
    with app.app_context():
        db.create_all()
        init_default_data()


# =============================================================================
# MAIN APPLICATION
# =============================================================================

if __name__ == '__main__':
    # Check if database exists
    db_path = os.path.join(INSTANCE_DIR, 'cms.db')
    
    if not os.path.exists(db_path):
        print("="*60)
        print("INITIALIZING DATABASE...")
        print("="*60)
        try:
            init_db()
            print("\n✅ Database initialized successfully!")
            print("\n" + "="*60)
            print("🔐 DEFAULT ADMIN CREDENTIALS:")
            print("   Username: admin")
            print("   Password: admin123")
            print("="*60)
            print("\n⚠️  IMPORTANT: Change the password after first login!")
            print("\n🌐 Starting server...")
            print("   - Website: http://localhost:5000")
            print("   - Admin: http://localhost:5000/admin/login")
            print("="*60 + "\n")
        except Exception as e:
            print(f"\n❌ Error initializing database: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure you have write permissions")
            print("2. Check if 'instance' folder exists")
            print("3. Try running: mkdir instance")
            import sys
            sys.exit(1)
    else:
        print("="*60)
        print("🚀 SHRAMIC NETWORKS CMS")
        print("="*60)
        print("🌐 Server starting...")
        print("   - Website: http://localhost:5000")
        print("   - Admin: http://localhost:5000/admin/login")
        print("="*60 + "\n")
    
    # Run the application
    try:
        app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")