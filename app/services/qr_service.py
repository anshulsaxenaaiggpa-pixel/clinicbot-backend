"""
QR Code Generation Service

Generate WhatsApp click-to-chat QR codes for doctors.
"""
import qrcode
from qrcode.image.pil import PilImage
from PIL import Image
from io import BytesIO
from sqlalchemy.orm import Session

from app.models.doctor import Doctor


class QRCodeService:
    """Service for generating WhatsApp QR codes."""
    
    # QR Code specifications (per compliance requirements)
    SIZE = 300  # 300x300px minimum
    ERROR_CORRECTION = qrcode.constants.ERROR_CORRECT_H  # Level H (30% recovery)
    BORDER = 4  # 4 boxes
    
    @staticmethod
    def get_whatsapp_link(doctor: Doctor) -> str:
        """
        Get WhatsApp click-to-chat link for doctor.
        
        Format: wa.me/{number}?text=Hi
        
        Args:
            doctor: Doctor model instance
        
        Returns:
            WhatsApp link or None if no number
        """
        if not doctor.whatsapp_number:
            return None
        
        # Use doctor model method
        return doctor.get_shareable_link()
    
    @staticmethod
    def generate_qr_code(doctor: Doctor) -> Image.Image:
        """
        Generate QR code for doctor's WhatsApp link.
        
        Args:
            doctor: Doctor model instance
        
        Returns:
            PIL Image object
        
        Raises:
            ValueError: If doctor has no WhatsApp number
        """
        link = QRCodeService.get_whatsapp_link(doctor)
        
        if not link:
            raise ValueError(f"Doctor {doctor.id} has no WhatsApp number")
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,  # Auto-adjust size
            error_correction=QRCodeService.ERROR_CORRECTION,
            box_size=10,
            border=QRCodeService.BORDER,
        )
        
        qr.add_data(link)
        qr.make(fit=True)
        
        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Resize to minimum size
        img = img.resize((QRCodeService.SIZE, QRCodeService.SIZE), Image.LANCZOS)
        
        return img
    
    @staticmethod
    def generate_qr_code_bytes(doctor: Doctor) -> bytes:
        """
        Generate QR code as PNG bytes for download.
        
        Args:
            doctor: Doctor model instance
        
        Returns:
            PNG bytes
        """
        img = QRCodeService.generate_qr_code(doctor)
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return buffer.read()
    
    @staticmethod
    def get_share_message(doctor: Doctor) -> str:
        """
        Get example share message for doctor.
        
        Returns:
            Formatted message for WhatsApp/SMS sharing
        """
        link = QRCodeService.get_whatsapp_link(doctor)
        
        if not link:
            return None
        
        return f"""Book an appointment with {doctor.full_name}

Specialty: {doctor.specialty}
City: {doctor.city}

Click here to book via WhatsApp:
{link}

Or scan the QR code to connect instantly!"""
