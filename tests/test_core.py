from app.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.services.dispatch_service import calculate_haversine_distance


def test_password_hashing():
    password = "SecurePassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_generation_and_decoding():
    user_id = "user-12345"
    token = create_access_token(subject=user_id, role="customer")
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "customer"
    assert payload["type"] == "access"


def test_haversine_distance():
    # Distance between Indiranagar and Koramangala, Bengaluru (~5.8 km)
    lat1, lon1 = 12.9716, 77.5946
    lat2, lon2 = 12.9352, 77.6245
    dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
    assert 4.0 <= dist <= 6.5
