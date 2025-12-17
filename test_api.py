"""
Automated API Testing Script for ClinicBot.ai

This script tests all major API endpoints to verify functionality.
Run this script after starting the backend server.

Usage:
    python test_api.py

Prerequisites:
    - Backend server running at http://localhost:8000
    - Test clinic seeded in database (run seed_test_data.py first)
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List
import sys

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
API_KEY = None  # Will be fetched or set during tests
CLINIC_ID = None
DOCTOR_ID = None
SERVICE_ID = None
PATIENT_ID = None
APPOINTMENT_ID = None

# Test results
test_results = []


class TestResult:
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        test_results.append(self)

    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        msg = f" - {self.message}" if self.message else ""
        return f"{status} | {self.name}{msg}"


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_health_check():
    """Test if server is running"""
    print_section("Health Check")
    try:
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/docs")
        if response.status_code == 200:
            TestResult("Server Health Check", True, "API docs accessible")
            return True
        else:
            TestResult("Server Health Check", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Server Health Check", False, str(e))
        return False


def test_create_clinic():
    """Test clinic creation"""
    print_section("Clinic Creation")
    global API_KEY, CLINIC_ID
    
    data = {
        "name": "Test Automation Clinic",
        "owner_name": "Dr. Test",
        "address": "123 Test Street",
        "city": "Test City",
        "timezone": "Asia/Kolkata",
        "whatsapp_number": f"+91987654{datetime.now().microsecond % 10000}",  # Unique number
        "whatsapp_provider": "twilio",
        "subscription_tier": "trial"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/clinics", json=data)
        
        if response.status_code == 201:
            result = response.json()
            API_KEY = result.get("api_key")
            CLINIC_ID = result.get("id")
            TestResult("Create Clinic", True, f"Clinic ID: {CLINIC_ID[:8]}...")
            print(f"  🔑 API Key: {API_KEY}")
            print(f"  🏥 Clinic ID: {CLINIC_ID}")
            return True
        else:
            TestResult("Create Clinic", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Create Clinic", False, str(e))
        return False


def test_get_clinic():
    """Test getting clinic details"""
    if not CLINIC_ID or not API_KEY:
        TestResult("Get Clinic", False, "No clinic ID or API key")
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    
    try:
        response = requests.get(f"{BASE_URL}/clinics/{CLINIC_ID}", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            TestResult("Get Clinic Details", True, f"Name: {result['name']}")
            return True
        else:
            TestResult("Get Clinic Details", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Get Clinic Details", False, str(e))
        return False


def test_create_doctor():
    """Test doctor creation"""
    print_section("Doctor Management")
    global DOCTOR_ID
    
    if not API_KEY or not CLINIC_ID:
        TestResult("Create Doctor", False, "No API key or clinic ID")
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    data = {
        "clinic_id": CLINIC_ID,
        "name": "Dr. Test Sharma",
        "specialization": "Automation Specialist",
        "phone": "+919876543210",
        "default_fee": 1000,
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/doctors", json=data, headers=headers)
        
        if response.status_code == 201:
            result = response.json()
            DOCTOR_ID = result.get("id")
            TestResult("Create Doctor", True, f"Doctor: {result['name']}")
            print(f"  👨‍⚕️ Doctor ID: {DOCTOR_ID}")
            return True
        else:
            TestResult("Create Doctor", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Create Doctor", False, str(e))
        return False


def test_list_doctors():
    """Test listing doctors"""
    if not API_KEY or not CLINIC_ID:
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    
    try:
        response = requests.get(
            f"{BASE_URL}/doctors",
            params={"clinic_id": CLINIC_ID},
            headers=headers
        )
        
        if response.status_code == 200:
            doctors = response.json()
            TestResult("List Doctors", True, f"Found {len(doctors)} doctor(s)")
            return True
        else:
            TestResult("List Doctors", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("List Doctors", False, str(e))
        return False


def test_create_service():
    """Test service creation"""
    print_section("Service Management")
    global SERVICE_ID
    
    if not API_KEY or not CLINIC_ID:
        TestResult("Create Service", False, "No API key or clinic ID")
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    data = {
        "clinic_id": CLINIC_ID,
        "name": "Test Consultation",
        "type": "consultation",
        "duration_minutes": 30,
        "buffer_minutes": 10,
        "default_fee": 500,
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/services", json=data, headers=headers)
        
        if response.status_code == 201:
            result = response.json()
            SERVICE_ID = result.get("id")
            slots = result.get("required_slots", 0)
            TestResult("Create Service", True, f"Service created, {slots} slot(s) required")
            print(f"  🏥 Service ID: {SERVICE_ID}")
            return True
        else:
            TestResult("Create Service", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Create Service", False, str(e))
        return False


def test_get_slots():
    """Test slot availability API"""
    print_section("Slot Availability")
    
    if not API_KEY or not CLINIC_ID or not DOCTOR_ID:
        TestResult("Get Available Slots", False, "Missing prerequisites")
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    params = {
        "clinic_id": CLINIC_ID,
        "doctor_id": DOCTOR_ID,
        "date": tomorrow
    }
    
    try:
        response = requests.get(f"{BASE_URL}/slots", params=params, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            total = result.get("total_slots", 0)
            available = result.get("available_slots", 0)
            TestResult("Get Available Slots", True, f"{available}/{total} slots available")
            return True
        else:
            TestResult("Get Available Slots", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Get Available Slots", False, str(e))
        return False


def test_create_appointment():
    """Test appointment booking"""
    print_section("Appointment Booking")
    global APPOINTMENT_ID, PATIENT_ID
    
    if not all([API_KEY, CLINIC_ID, DOCTOR_ID, SERVICE_ID]):
        TestResult("Book Appointment", False, "Missing prerequisites")
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    data = {
        "clinic_id": CLINIC_ID,
        "doctor_id": DOCTOR_ID,
        "service_id": SERVICE_ID,
        "date": tomorrow,
        "start_time": "10:30",
        "patient_name": "Test Patient",
        "patient_phone": "+919999999999",
        "notes": "Automated test appointment"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/appointments", json=data, headers=headers)
        
        if response.status_code == 201:
            result = response.json()
            APPOINTMENT_ID = result.get("id")
            PATIENT_ID = result.get("patient_id")
            fee = result.get("fee", 0)
            TestResult("Book Appointment", True, f"Fee: ₹{fee}")
            print(f"  📅 Appointment ID: {APPOINTMENT_ID}")
            print(f"  👤 Patient ID: {PATIENT_ID}")
            return True
        else:
            TestResult("Book Appointment", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Book Appointment", False, str(e))
        return False


def test_double_booking_prevention():
    """Test that double-booking is prevented"""
    if not all([API_KEY, CLINIC_ID, DOCTOR_ID, SERVICE_ID]):
        TestResult("Double-Booking Prevention", False, "Missing prerequisites")
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Try to book the same slot again
    data = {
        "clinic_id": CLINIC_ID,
        "doctor_id": DOCTOR_ID,
        "service_id": SERVICE_ID,
        "date": tomorrow,
        "start_time": "10:30",  # Same time as previous booking
        "patient_name": "Another Patient",
        "patient_phone": "+919888888888"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/appointments", json=data, headers=headers)
        
        # Should return 409 Conflict
        if response.status_code == 409:
            TestResult("Double-Booking Prevention", True, "Duplicate booking correctly rejected")
            return True
        elif response.status_code == 201:
            TestResult("Double-Booking Prevention", False, "❗ CRITICAL: Double-booking allowed!")
            return False
        else:
            TestResult("Double-Booking Prevention", False, f"Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Double-Booking Prevention", False, str(e))
        return False


def test_list_appointments():
    """Test listing appointments"""
    if not API_KEY or not CLINIC_ID:
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    
    try:
        response = requests.get(
            f"{BASE_URL}/appointments",
            params={"clinic_id": CLINIC_ID},
            headers=headers
        )
        
        if response.status_code == 200:
            appointments = response.json()
            TestResult("List Appointments", True, f"Found {len(appointments)} appointment(s)")
            return True
        else:
            TestResult("List Appointments", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("List Appointments", False, str(e))
        return False


def test_cancel_appointment():
    """Test appointment cancellation"""
    if not API_KEY or not APPOINTMENT_ID:
        TestResult("Cancel Appointment", False, "No appointment to cancel")
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    
    try:
        response = requests.patch(
            f"{BASE_URL}/appointments/{APPOINTMENT_ID}/cancel",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result.get("status")
            TestResult("Cancel Appointment", True, f"Status: {status}")
            return True
        else:
            TestResult("Cancel Appointment", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Cancel Appointment", False, str(e))
        return False


def test_patient_stats():
    """Test patient statistics"""
    print_section("Patient Tracking")
    
    if not API_KEY or not PATIENT_ID:
        TestResult("Get Patient Stats", False, "No patient ID")
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    
    try:
        response = requests.get(
            f"{BASE_URL}/patients/{PATIENT_ID}/stats",
            headers=headers
        )
        
        if response.status_code == 200:
            stats = response.json()
            visits = stats.get("total_visits", 0)
            TestResult("Get Patient Stats", True, f"{visits} visit(s) recorded")
            return True
        else:
            TestResult("Get Patient Stats", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Get Patient Stats", False, str(e))
        return False


def test_dashboard_summary():
    """Test dashboard summary endpoint"""
    print_section("Summary & Analytics")
    
    if not API_KEY or not CLINIC_ID:
        TestResult("Dashboard Summary", False, "Missing prerequisites")
        return False
    
    headers = {"X-CLINIC-KEY": API_KEY}
    
    try:
        response = requests.get(
            f"{BASE_URL}/summary/dashboard",
            params={"clinic_id": CLINIC_ID},
            headers=headers
        )
        
        if response.status_code == 200:
            summary = response.json()
            today_appts = summary.get("today", {}).get("appointments", 0)
            TestResult("Dashboard Summary", True, f"{today_appts} appointment(s) today")
            return True
        else:
            TestResult("Dashboard Summary", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        TestResult("Dashboard Summary", False, str(e))
        return False


def print_summary():
    """Print test summary"""
    print_section("Test Summary")
    
    passed = sum(1 for t in test_results if t.passed)
    failed = len(test_results) - passed
    total = len(test_results)
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%\n")
    
    if failed > 0:
        print("Failed Tests:")
        for test in test_results:
            if not test.passed:
                print(f"  ❌ {test.name}")
        print()
    
    return failed == 0


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  ClinicBot.ai - Automated API Testing")
    print("="*60)
    print(f"  Target: {BASE_URL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Run tests in sequence
    if not test_health_check():
        print("\n❌ Server not responding. Please start the backend server.")
        print("   Command: uvicorn app.main:app --reload")
        sys.exit(1)
    
    test_create_clinic()
    test_get_clinic()
    test_create_doctor()
    test_list_doctors()
    test_create_service()
    test_get_slots()
    test_create_appointment()
    test_double_booking_prevention()
    test_list_appointments()
    test_cancel_appointment()
    test_patient_stats()
    test_dashboard_summary()
    
    # Print all results
    print_section("Detailed Results")
    for test in test_results:
        print(f"  {test}")
    
    # Print summary
    success = print_summary()
    
    if success:
        print("🎉 All tests passed! API is working correctly.\n")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please review the results above.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
