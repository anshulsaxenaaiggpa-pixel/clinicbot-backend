"""
QR Code generation utility for doctor WhatsApp links
"""
import qrcode
from pathlib import Path
from io import BytesIO


def generate_doctor_qr(doctor_id: str, whatsapp_link: str) -> str:
    """
    Generate QR code for doctor's WhatsApp booking link
    
    Args:
        doctor_id: Doctor's unique ID
        whatsapp_link: Full WhatsApp link (wa.me/...)
    
    Returns:
        Relative path to saved QR image (e.g., /static/qr_codes/doctor_abc123.png)
    """
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(whatsapp_link)
    qr.make(fit=True)

    # Generate image
    img = qr.make_image(fill_color="black", back_color="white")

    # Ensure directory exists
    qr_dir = Path(__file__).resolve().parent.parent / "static" / "qr_codes"
    qr_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    filename = f"doctor_{doctor_id}.png"
    filepath = qr_dir / filename
    img.save(filepath)

    # Return web-accessible path
    return f"/static/qr_codes/{filename}"


def generate_temp_password(length: int = 8) -> str:
    """
    Generate a random temporary password for new doctors
    
    Args:
        length: Length of password (default 8)
    
    Returns:
        Random alphanumeric password
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password
