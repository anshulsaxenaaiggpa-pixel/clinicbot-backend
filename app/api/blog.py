"""
Blog system for SEO content
Serves markdown files from app/static/blog/
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import markdown
import re

router = APIRouter(prefix="/blog", tags=["blog"])
templates = Jinja2Templates(directory="app/templates")

# Blog post directory
BLOG_DIR = Path("app/static/blog")


def get_post_metadata(content: str):
    """Extract title and description from markdown"""
    lines = content.split('\n')
    title = "Blog Post"
    description = ""
    
    for line in lines:
        if line.startswith('# '):
            title = line[2:].strip()
        elif line and not line.startswith('#') and len(line) > 20:
            description = line.strip()[:160]
            break
    
    return title, description


@router.get("/", response_class=HTMLResponse)
async def blog_index(request: Request):
    """List all blog posts"""
    if not BLOG_DIR.exists():
        BLOG_DIR.mkdir(parents=True, exist_ok=True)
    
    posts = []
    for md_file in BLOG_DIR.glob("*.md"):
        content = md_file.read_text(encoding='utf-8')
        title, description = get_post_metadata(content)
        
        posts.append({
            "slug": md_file.stem,
            "title": title,
            "description": description,
            "url": f"/blog/{md_file.stem}"
        })
    
    return templates.TemplateResponse("public/blog_index.html", {
        "request": request,
        "posts": posts
    })


@router.get("/{slug}", response_class=HTMLResponse)
async def blog_post(slug: str, request: Request):
    """Render a blog post from markdown"""
    # Sanitize slug
    slug = re.sub(r'[^a-z0-9-]', '', slug.lower())
    
    post_file = BLOG_DIR / f"{slug}.md"
    
    if not post_file.exists():
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    # Read and convert markdown
    md_content = post_file.read_text(encoding='utf-8')
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    title, description = get_post_metadata(md_content)
    
    return templates.TemplateResponse("public/blog_post.html", {
        "request": request,
        "title": title,
        "description": description,
        "content": html_content,
        "slug": slug
    })
