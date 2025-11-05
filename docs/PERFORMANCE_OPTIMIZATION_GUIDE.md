# Performance Optimization Guide

## Document Purpose
This guide provides performance optimization strategies, database query optimization techniques, caching strategies, and frontend optimization guidelines for the Manual Generator system.

## Table of Contents
1. [Database Query Optimization](#database-query-optimization)
2. [API Response Caching](#api-response-caching)
3. [Frontend Lazy Loading](#frontend-lazy-loading)
4. [Image Optimization](#image-optimization)
5. [Monitoring & Metrics](#monitoring--metrics)

---

## Database Query Optimization

### Indexing Strategy

**Current Indexes (Implemented):**
```python
# Activity logs indexes (already in models.py)
__table_args__ = (
    db.Index('idx_user_action_date', 'user_id', 'action_type', 'created_at'),
    db.Index('idx_company_date', 'company_id', 'created_at'),
)

# Processing jobs indexes
__table_args__ = (
    db.Index('idx_job_status_type', 'job_status', 'job_type'),
)
```

**Recommended Additional Indexes:**
```sql
-- Manuals table
CREATE INDEX idx_manuals_company_status ON manuals(company_id, generation_status);
CREATE INDEX idx_manuals_created_at ON manuals(created_at DESC);

-- Users table
CREATE INDEX idx_users_company_role ON users(company_id, role);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

-- Reference materials table
CREATE INDEX idx_materials_company_status ON reference_materials(company_id, processing_status);
CREATE INDEX idx_materials_indexed ON reference_materials(elasticsearch_indexed) WHERE elasticsearch_indexed = TRUE;
```

### Query Optimization Patterns

**❌ Bad: N+1 Query Problem**
```python
# This causes N+1 queries!
manuals = Manual.query.filter_by(company_id=company_id).all()
for manual in manuals:
    user = User.query.get(manual.user_id)  # N additional queries!
    print(f"{manual.title} by {user.username}")
```

**✅ Good: Eager Loading with JOIN**
```python
# Single query with JOIN
manuals = db.session.query(Manual, User)\
    .join(User, Manual.user_id == User.id)\
    .filter(Manual.company_id == company_id)\
    .all()

for manual, user in manuals:
    print(f"{manual.title} by {user.username}")
```

**✅ Good: Use SQLAlchemy Relationship Loading**
```python
# Define relationship in models.py
class Manual(db.Model):
    user = db.relationship('User', backref='manuals', lazy='joined')

# Then use it
manuals = Manual.query.filter_by(company_id=company_id).all()
for manual in manuals:
    print(f"{manual.title} by {manual.user.username}")  # No extra query!
```

### Pagination Best Practices

**Always use pagination for list endpoints:**
```python
@app.route('/api/manuals')
def list_manuals():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Limit per_page to prevent abuse
    per_page = min(per_page, 100)
    
    query = Manual.query.filter_by(company_id=current_company_id)
    
    # Use paginate() instead of all()
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return jsonify({
        'manuals': [m.to_dict() for m in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })
```

### Avoid SELECT *

**❌ Bad: Selecting unnecessary columns**
```python
manuals = Manual.query.all()  # Loads ALL columns including large BLOBs
```

**✅ Good: Select only needed columns**
```python
# Only select needed fields for list view
manuals = db.session.query(
    Manual.id,
    Manual.title,
    Manual.created_at,
    Manual.generation_status
).filter_by(company_id=company_id).all()
```

### Use Database-Level Aggregations

**❌ Bad: Aggregating in Python**
```python
manuals = Manual.query.filter_by(company_id=company_id).all()
completed_count = len([m for m in manuals if m.generation_status == 'completed'])
```

**✅ Good: Database aggregation**
```python
completed_count = db.session.query(db.func.count(Manual.id))\
    .filter_by(company_id=company_id, generation_status='completed')\
    .scalar()
```

---

## API Response Caching

### Flask-Caching Setup

**Install dependencies:**
```bash
pip install Flask-Caching redis
```

**Configuration (src/core/app.py):**
```python
from flask_caching import Cache

# Cache configuration
cache_config = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes
}

cache = Cache(app, config=cache_config)
```

### Caching Strategies

**1. Cache static data (templates, companies):**
```python
@app.route('/api/company/templates')
@cache.cached(timeout=600, key_prefix='templates_%s' % current_company_id)
def get_templates():
    templates = ManualTemplate.query.filter_by(company_id=current_company_id).all()
    return jsonify({'templates': [t.to_dict() for t in templates]})
```

**2. Cache expensive computations:**
```python
@app.route('/api/company/dashboard')
@cache.cached(timeout=300, key_prefix='dashboard_%s' % current_company_id)
def get_dashboard():
    stats = {
        'total_users': User.query.filter_by(company_id=current_company_id).count(),
        'total_manuals': Manual.query.filter_by(company_id=current_company_id).count(),
        # ... other expensive stats
    }
    return jsonify({'stats': stats})
```

**3. Cache invalidation:**
```python
@app.route('/api/company/templates', methods=['POST'])
def create_template():
    # ... create template logic ...
    
    # Invalidate cache after mutation
    cache.delete('templates_%s' % current_company_id)
    
    return jsonify({'success': True})
```

**4. Memoization for function results:**
```python
@cache.memoize(timeout=600)
def get_company_statistics(company_id):
    """Expensive computation cached by arguments"""
    # ... complex statistics calculation ...
    return stats

# Usage
stats = get_company_statistics(current_company_id)
```

### Cache Keys Best Practices

**Include relevant context in cache keys:**
```python
# Bad: Global cache key (conflicts between companies)
@cache.cached(timeout=300, key_prefix='manuals')

# Good: Company-specific cache key
@cache.cached(timeout=300, key_prefix=lambda: f'manuals_{current_company_id}')

# Even better: Include pagination
@cache.cached(
    timeout=300,
    key_prefix=lambda: f'manuals_{current_company_id}_page_{request.args.get("page", 1)}'
)
```

---

## Frontend Lazy Loading

### Image Lazy Loading

**HTML implementation:**
```html
<!-- Modern browsers support native lazy loading -->
<img src="/path/to/image.jpg" loading="lazy" alt="Description">

<!-- For better compatibility, use Intersection Observer -->
<img data-src="/path/to/image.jpg" class="lazy" alt="Description">
<noscript>
    <img src="/path/to/image.jpg" alt="Description">
</noscript>
```

**JavaScript implementation:**
```javascript
// Lazy load images using Intersection Observer
document.addEventListener('DOMContentLoaded', function() {
    const lazyImages = document.querySelectorAll('img.lazy');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for older browsers
        lazyImages.forEach(img => {
            img.src = img.dataset.src;
        });
    }
});
```

### JavaScript Code Splitting

**Defer non-critical JavaScript:**
```html
<!-- Critical JavaScript (inline or early load) -->
<script src="/static/js/core.js"></script>

<!-- Non-critical JavaScript (deferred) -->
<script src="/static/js/analytics.js" defer></script>
<script src="/static/js/charts.js" defer></script>

<!-- Load modules on-demand -->
<script type="module">
    // Load only when needed
    document.getElementById('openChart').addEventListener('click', async () => {
        const { ChartModule } = await import('/static/js/charts.js');
        ChartModule.init();
    });
</script>
```

### Infinite Scroll / Virtual Scrolling

**Implementation for large lists:**
```javascript
let currentPage = 1;
let loading = false;
let hasMore = true;

async function loadMoreManuals() {
    if (loading || !hasMore) return;
    
    loading = true;
    const response = await fetch(`/api/manuals?page=${currentPage}&per_page=20`);
    const data = await response.json();
    
    if (data.success) {
        renderManuals(data.manuals, true); // append=true
        currentPage++;
        hasMore = currentPage <= data.pagination.pages;
    }
    
    loading = false;
}

// Trigger on scroll near bottom
window.addEventListener('scroll', () => {
    const scrollPosition = window.innerHeight + window.scrollY;
    const documentHeight = document.documentElement.scrollHeight;
    
    if (scrollPosition >= documentHeight - 500) {
        loadMoreManuals();
    }
});
```

### Bundle Size Optimization

**Remove unused dependencies:**
```bash
# Analyze bundle size
npm install -g webpack-bundle-analyzer

# Minimize CSS/JS
# Use minified versions of libraries
# Remove console.log statements in production
```

---

## Image Optimization

### Server-Side Image Processing

**Resize and compress images before storage:**
```python
from PIL import Image
import io

def optimize_image(image_file, max_width=1920, max_height=1080, quality=85):
    """
    Optimize image for web delivery
    
    Args:
        image_file: File object or path
        max_width: Maximum width
        max_height: Maximum height
        quality: JPEG quality (1-100)
    
    Returns:
        Optimized image bytes
    """
    img = Image.open(image_file)
    
    # Convert RGBA to RGB for JPEG
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    
    # Resize if too large
    if img.width > max_width or img.height > max_height:
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    
    # Save to bytes
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)
    
    return output.getvalue()

# Usage in upload endpoint
@app.route('/api/upload/image', methods=['POST'])
def upload_image():
    file = request.files['image']
    
    # Optimize before S3 upload
    optimized = optimize_image(file, quality=85)
    
    # Upload to S3
    s3_manager.upload_file(
        io.BytesIO(optimized),
        s3_key,
        content_type='image/jpeg'
    )
```

### WebP Format Support

**Serve WebP with JPEG fallback:**
```html
<picture>
    <source srcset="/path/to/image.webp" type="image/webp">
    <img src="/path/to/image.jpg" alt="Description" loading="lazy">
</picture>
```

**Convert images to WebP:**
```python
from PIL import Image

def convert_to_webp(input_path, output_path, quality=80):
    """Convert image to WebP format"""
    img = Image.open(input_path)
    img.save(output_path, 'WEBP', quality=quality, method=6)
```

### Thumbnail Generation

**Generate multiple sizes:**
```python
THUMBNAIL_SIZES = {
    'small': (150, 150),
    'medium': (300, 300),
    'large': (600, 600)
}

def generate_thumbnails(image_file, manual_id):
    """Generate multiple thumbnail sizes"""
    img = Image.open(image_file)
    thumbnails = {}
    
    for size_name, (width, height) in THUMBNAIL_SIZES.items():
        thumb = img.copy()
        thumb.thumbnail((width, height), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        thumb.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        # Upload to S3
        s3_key = f"{company_id}/thumbnails/{manual_id}/{size_name}.jpg"
        s3_manager.upload_file(output, s3_key)
        
        thumbnails[size_name] = s3_manager.generate_presigned_url(s3_key)
    
    return thumbnails
```

---

## Monitoring & Metrics

### Application Performance Monitoring

**Log slow queries:**
```python
from flask import g
import time

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        
        # Log slow requests (>1 second)
        if elapsed > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {elapsed:.2f}s"
            )
    
    return response
```

### Database Query Logging

**Enable SQLAlchemy query logging in development:**
```python
# In development only
if app.debug:
    import logging
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Custom Metrics

**Track business metrics:**
```python
from datetime import datetime, timedelta

def get_performance_metrics():
    """Get system performance metrics"""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    metrics = {
        'timestamp': now.isoformat(),
        'requests': {
            'total_today': get_request_count(today, now),
            'slow_requests': get_slow_request_count(today, now)
        },
        'manuals': {
            'created_today': Manual.query.filter(
                Manual.created_at >= today
            ).count(),
            'processing': Manual.query.filter_by(
                generation_status='processing'
            ).count()
        },
        'cache': {
            'hit_rate': cache.get_stats().get('hit_rate', 0)
        }
    }
    
    return metrics
```

### Performance Benchmarks

**Target response times:**
- List endpoints: < 200ms
- Detail endpoints: < 100ms
- Create/Update: < 500ms
- Heavy operations (PDF, Translation): Async with job tracking

**Database query limits:**
- Simple queries: < 50ms
- Join queries: < 100ms
- Aggregations: < 200ms

**Monitoring tools:**
- Flask-Profiler: Profile endpoint performance
- New Relic / DataDog: Production APM
- Prometheus + Grafana: Custom metrics

---

## Best Practices Summary

✅ **Database:**
- Use indexes on frequently queried columns
- Avoid N+1 queries with eager loading
- Always paginate list endpoints
- Use database aggregations instead of Python

✅ **Caching:**
- Cache static/slow data with Redis
- Invalidate cache on mutations
- Use company-specific cache keys
- Set appropriate TTL values

✅ **Frontend:**
- Lazy load images and JavaScript
- Implement infinite scroll for long lists
- Minify and compress assets
- Use CDN for static files

✅ **Images:**
- Resize and compress before upload
- Generate thumbnails for previews
- Use WebP with JPEG fallback
- Optimize quality vs. file size

✅ **Monitoring:**
- Log slow queries and requests
- Track business metrics
- Set up alerts for errors
- Monitor resource usage

---

## Next Steps

1. Implement Redis caching for dashboard endpoints
2. Add database indexes to production database
3. Set up lazy loading for manual list images
4. Configure image optimization pipeline
5. Deploy monitoring and alerting system
