import asyncio
import logging

from sqlmodel import Session, select
from database import engine
from models import Job, Thumbnail
from services.openai_service import generate_thumbnail
from services.imagekit_service import upload_file

logger = logging.getLogger(__name__)

STYLES = {
    "bold_dramatic": (
        "Create a bold, dramatic Youtube Thumbnail with high contrast, "
        "cinematic lightning, dark moody background and powerful composition."
        "The person's face should prominent with a dramatic expression."
    ),
    "clean_minimal": (
        "Create a clean, beautiful Youtube Thumbnail with bright lightning, "
        "white/light background, modern professional aesthetic, plenty of "
        "white space, and sharp clean composition. The person should looks "
        "approachable and professional."
    ),
    "vibrant_energetic": (
        "Create a vibrant, energetic Youtube thumbnail with colorful gradients, "
        "dynamic angles, eye-catching, pop-art style colors, and energetic "
        "composition. The person should have an excited or engaging expression."
    ),
}

STYLE_ORDER = ["bold_dramatic", "clean_minimal", "vibrant_energetic"]


async def generate_single_thumbnail(thumbnail_id: str, prompt: str, headshot_url: str):
    # DB mark -> generating
    with Session(engine) as session:
        thumb = session.get(Thumbnail, thumbnail_id)
        thumb.status = "generating"
        style_name = thumb.style_name
        session.add(thumb)
        session.commit()
        
    style_prompt = STYLE_ORDER[style_name]
    
    # AI Call
    try:
        image_byte = await generate_thumbnail(prompt, style_prompt, headshot_url)
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            job_id = thumb.job_id
            
        # Upload this image
        url = upload_file(
            file_bytes=image_byte,
            file_name=f"{thumbnail_id}.png",
            folder=f"/thumbnail/{job_id}/",
        )
        
        # DB call save the url + mark uploaded
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            thumb.imagekit_url = url
            thumb.status = "uploaded"
            session.add(thumb)
            session.commit()
            
        logger.info(f"Thumbnail {thumbnail_id} generated and uploaded successfully.")
        
    except Exception as e:
        logger.info(f"Error generating thumbnail {thumbnail_id}: {e}")
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            thumb.status = "error"
            thumb.error_message = str(e)[:500]
            session.add(thumb)
            session.commit()
