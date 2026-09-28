from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import get_password_hash
from app.models.category import ServiceCategory
from app.models.user import User, WorkerProfile

SEED_CATEGORIES = [
    {
        "id": "car-breakdown",
        "name": "Car Breakdown & Jumpstart",
        "icon_name": "Car",
        "description": "On-road emergency mechanics for jumpstart, engine stall, towing & quick fixes.",
        "diagnostic_fee": 199.0,
        "estimated_arrival_min": 15,
        "popular_problems": ["Engine Won't Start", "Dead Battery / Jumpstart", "Overheating / Coolant", "Clutch / Gear Stuck"],
        "active_workers_count": 24,
        "display_order": 1,
    },
    {
        "id": "bike-scooter",
        "name": "Bike & Scooter Assistance",
        "icon_name": "Bike",
        "description": "Rapid two-wheeler mobile mechanics for puncture, chain slip, spark plug & fuel issues.",
        "diagnostic_fee": 99.0,
        "estimated_arrival_min": 10,
        "popular_problems": ["Starting Trouble", "Chain Slip / Broken", "Spark Plug Fouled", "Brake Failure"],
        "active_workers_count": 31,
        "display_order": 2,
    },
    {
        "id": "puncture",
        "name": "Mobile Tyre & Puncture",
        "icon_name": "CircleDot",
        "description": "At-location tubeless & tube puncture repair, stepney replacement, and high-pressure air fill.",
        "diagnostic_fee": 79.0,
        "estimated_arrival_min": 10,
        "popular_problems": ["Tubeless Puncture Fix", "Stepney Wheel Swap", "Low Air Fill Pressure", "Tyre Valve Leak"],
        "active_workers_count": 28,
        "display_order": 3,
    },
    {
        "id": "battery",
        "name": "Battery Express Swap",
        "icon_name": "Zap",
        "description": "Instant 12V automotive battery testing, heavy-duty jump cable boost, or doorstep new battery swap.",
        "diagnostic_fee": 149.0,
        "estimated_arrival_min": 12,
        "popular_problems": ["12V Heavy Jumpstart", "Battery Terminal Corrosion", "Rapid Health Diagnostic", "New Exide/Amaron Swap"],
        "active_workers_count": 19,
        "display_order": 4,
    },
    {
        "id": "gas-leak",
        "name": "Gas Leak & Cylinder Emergency",
        "icon_name": "Flame",
        "description": "Certified hazardous LPG gas leak inspection, regulator gasket repair, and stove burner safety check.",
        "diagnostic_fee": 199.0,
        "estimated_arrival_min": 8,
        "popular_problems": ["Strong Gas Odour Check", "LPG Regulator Failure", "Safety Pipe Gasket Leak", "Burner Flame Ignition Fix"],
        "active_workers_count": 12,
        "display_order": 5,
    },
    {
        "id": "plumbing",
        "name": "Plumbing & Burst Pipes",
        "icon_name": "Droplets",
        "description": "Fast emergency plumbing for high-pressure burst pipes, tap leaks, toilet overflow, and motor pumps.",
        "diagnostic_fee": 149.0,
        "estimated_arrival_min": 15,
        "popular_problems": ["Burst Main Water Pipe", "Toilet Cistern Overflow", "Severe Tap Jet Leak", "Motor Pump Priming Failure"],
        "active_workers_count": 22,
        "display_order": 6,
    },
    {
        "id": "locksmith",
        "name": "Emergency Locksmith",
        "icon_name": "Key",
        "description": "Non-destructive lock picking, broken key extraction, home smart door unlock, and car lockout rescue.",
        "diagnostic_fee": 199.0,
        "estimated_arrival_min": 15,
        "popular_problems": ["Locked Outside Main Door", "Car Key Locked Inside", "Key Broken in Keyhole", "Deadbolt Jammed"],
        "active_workers_count": 14,
        "display_order": 7,
    },
    {
        "id": "ac-repair",
        "name": "AC Gas Leak & Cooling",
        "icon_name": "AirVent",
        "description": "Immediate AC diagnosis, refrigerant gas leak detection, compressor capacitor replacement & deep coil jet clean.",
        "diagnostic_fee": 199.0,
        "estimated_arrival_min": 20,
        "popular_problems": ["AC Blowing Warm Air", "Compressor Not Starting", "Water Dripping Inside Room", "Gas Leakage Diagnostic"],
        "active_workers_count": 18,
        "display_order": 8,
    },
    {
        "id": "electrical",
        "name": "Fuse & Electrical Short Circuit",
        "icon_name": "Hammer",
        "description": "Licensed master electricians for tripping MCBs, sparking switchboards, burnt wires, and inverter repairs.",
        "diagnostic_fee": 149.0,
        "estimated_arrival_min": 12,
        "popular_problems": ["Main MCB Tripping Constantly", "Burnt Switchboard / Spark", "Inverter / Battery Not Charging", "Complete Room Power Outage"],
        "active_workers_count": 25,
        "display_order": 9,
    },
    {
        "id": "wifi",
        "name": "WiFi & Fiber Outage",
        "icon_name": "Wifi",
        "description": "Network technicians for damaged optical fiber cables, spliced patch cords, router config, and LAN wiring.",
        "diagnostic_fee": 129.0,
        "estimated_arrival_min": 18,
        "popular_problems": ["Fiber Optical Cable Cut", "Router Red LOS Alarm", "Speed Degradation / High Ping", "Ethernet Port Crimp Failure"],
        "active_workers_count": 16,
        "display_order": 10,
    },
    {
        "id": "appliance",
        "name": "Kitchen Appliance SOS",
        "icon_name": "Smartphone",
        "description": "Doorstep diagnosis and repair for non-cooling refrigerators, washing machines, microwaves, and chimneys.",
        "diagnostic_fee": 179.0,
        "estimated_arrival_min": 25,
        "popular_problems": ["Fridge Compressor Silent", "Washing Machine Not Spinning", "Microwave Not Heating", "Chimney Suction Failure"],
        "active_workers_count": 17,
        "display_order": 11,
    },
    {
        "id": "home-repair",
        "name": "General Handyman & Carpentry",
        "icon_name": "Hammer",
        "description": "Quick fix for broken door hinges, glass cracks, shutter jams, drill-and-hang, and emergency minor repairs.",
        "diagnostic_fee": 129.0,
        "estimated_arrival_min": 15,
        "popular_problems": ["Broken Door Hinge / Sagging", "Window Glass Crack Support", "Curtain Rod Drill Mount", "Sliding Shutter Jammed"],
        "active_workers_count": 20,
        "display_order": 12,
    },
]


async def init_database(db: AsyncSession) -> None:
    """
    Seed service categories, admin, test technician, and customer accounts if not present.
    """
    # 1. Seed Categories
    for cat_data in SEED_CATEGORIES:
        stmt = select(ServiceCategory).where(ServiceCategory.id == cat_data["id"])
        res = await db.execute(stmt)
        if not res.scalar_one_or_none():
            category = ServiceCategory(**cat_data)
            db.add(category)

    # 2. Seed Admin User
    admin_stmt = select(User).where(User.email == "admin@connecto.com")
    admin_res = await db.execute(admin_stmt)
    if not admin_res.scalar_one_or_none():
        admin = User(
            email="admin@connecto.com",
            hashed_password=get_password_hash("Admin@123"),
            full_name="Connecto Operations Lead",
            role="admin",
            phone="+919876543210",
            avatar="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
            is_active=True,
            is_verified=True,
        )
        db.add(admin)

    # 3. Seed Sample Verified Technician
    worker_stmt = select(User).where(User.email == "raj.kumar@connecto.com")
    worker_res = await db.execute(worker_stmt)
    if not worker_res.scalar_one_or_none():
        worker_user = User(
            email="raj.kumar@connecto.com",
            hashed_password=get_password_hash("Worker@123"),
            full_name="Raj Kumar",
            role="worker",
            phone="+919845122910",
            avatar="https://images.unsplash.com/photo-1540569014015-19a7be504e3a?auto=format&fit=crop&w=400&q=80",
            is_active=True,
            is_verified=True,
            rating=4.88,
        )
        db.add(worker_user)
        await db.flush()

        worker_profile = WorkerProfile(
            user_id=worker_user.id,
            category_id="car-breakdown",
            skills=["Engine Stall Recovery", "Jumpstart Boost", "OBD2 Diagnostics", "Alternator Diagnostics"],
            experience_years=6,
            is_online=True,
            verification_status="VERIFIED",
            aadhaar_verified=True,
            police_cleared=True,
            skill_audited=True,
            badge_title="Master Automotive Specialist",
            latitude=12.9716,
            longitude=77.5946,
            current_area="Indiranagar 100ft Rd, Bengaluru",
            acceptance_rate=98.5,
            completion_rate=99.0,
            completed_jobs=427,
            reviews_count=312,
            rating=4.88,
            today_earnings=1450.0,
            week_earnings=8920.0,
            month_earnings=34200.0,
        )
        db.add(worker_profile)

    # 4. Seed Sample Customer
    customer_stmt = select(User).where(User.email == "aarav@example.com")
    customer_res = await db.execute(customer_stmt)
    if not customer_res.scalar_one_or_none():
        customer = User(
            email="aarav@example.com",
            hashed_password=get_password_hash("Customer@123"),
            full_name="Aarav Patel",
            role="customer",
            phone="+919811223344",
            avatar="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80",
            is_active=True,
            is_verified=True,
            address="Flat 402, Green Glen Layout, Indiranagar Sector 4, Bengaluru",
            total_orders=6,
        )
        db.add(customer)

    await db.commit()
