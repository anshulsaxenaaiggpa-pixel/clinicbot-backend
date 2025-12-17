"""Background tasks for reminders and notifications"""
from celery import shared_task
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.appointment import Appointment
import logging

logger = logging.getLogger(__name__)


@shared_task(name='app.tasks.reminders.send_24h_reminder')
def send_24h_reminder(appointment_id: str):
    """
    Send 24-hour reminder for appointment
    
    Args:
        appointment_id: UUID of appointment
    """
    db = SessionLocal()
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment or appointment.status != 'confirmed':
            logger.warning(f"Appointment {appointment_id} not found or not confirmed")
            return
        
        # TODO: Send WhatsApp message via provider
        # For now, just log and mark as sent
        logger.info(f"Sending 24h reminder for appointment {appointment_id}")
        
        appointment.reminder_24h_sent = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        logger.error(f"Error sending 24h reminder: {str(e)}")
        db.rollback()
    finally:
        db.close()


@shared_task(name='app.tasks.reminders.send_2h_reminder')
def send_2h_reminder(appointment_id: str):
    """Send 2-hour reminder"""
    db = SessionLocal()
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment or appointment.status != 'confirmed':
            return
        
        # TODO: Send WhatsApp message
        logger.info(f"Sending 2h reminder for appointment {appointment_id}")
        
        appointment.reminder_2h_sent = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        logger.error(f"Error sending 2h reminder: {str(e)}")
        db.rollback()
    finally:
        db.close()


@shared_task(name='app.tasks.reminders.send_followup')
def send_followup(appointment_id: str):
    """Send post-appointment follow-up"""
    db = SessionLocal()
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment or appointment.status != 'completed':
            return
        
        # TODO: Send WhatsApp follow-up message
        logger.info(f"Sending follow-up for appointment {appointment_id}")
        
        appointment.followup_sent = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        logger.error(f"Error sending follow-up: {str(e)}")
        db.rollback()
    finally:
        db.close()


@shared_task(name='app.tasks.events.schedule_reminders')
def schedule_appointment_reminders(appointment_id: str, appointment_datetime: datetime):
    """
    Schedule all reminders for an appointment
    
    Args:
        appointment_id: UUID of appointment
        appointment_datetime: Datetime of appointment (UTC)
    """
    # Schedule 24h reminder
    reminder_24h_time = appointment_datetime - timedelta(hours=24)
    if reminder_24h_time > datetime.utcnow():
        send_24h_reminder.apply_async(
            args=[appointment_id],
            eta=reminder_24h_time
        )
    
    # Schedule 2h reminder
    reminder_2h_time = appointment_datetime - timedelta(hours=2)
    if reminder_2h_time > datetime.utcnow():
        send_2h_reminder.apply_async(
            args=[appointment_id],
            eta=reminder_2h_time
        )
    
    # Schedule follow-up (24h after appointment)
    followup_time = appointment_datetime + timedelta(days=1)
    send_followup.apply_async(
        args=[appointment_id],
        eta=followup_time
    )


@shared_task(name='app.tasks.summary.daily_digest')
def send_daily_digest(clinic_id: str):
    """Send daily occupancy and booking summary to clinic"""
    # TODO: Generate daily summary and send to clinic WhatsApp
    logger.info(f"Sending daily digest for clinic {clinic_id}")
    pass


@shared_task(name='app.tasks.events.trial_expiration_alert')
def trial_expiration_alert(clinic_id: str):
    """Alert clinic that trial is expiring soon"""
    # TODO: Send trial expiration message
    logger.info(f"Sending trial expiration alert for clinic {clinic_id}")
    pass
