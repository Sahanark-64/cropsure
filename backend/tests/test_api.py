from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def token(email="farmer@cropsure.demo"):
 r=client.post("/api/auth/login",json={"email":email,"password":"demo1234"});assert r.status_code==200;return r.json()["access_token"]
def test_health_and_seeded_login():
 assert client.get("/api/health").json()["status"]=="ok"
 assert token()
def test_farmer_dashboard_and_privacy():
 h={"Authorization":"Bearer "+token()}
 assert client.get("/api/dashboard/overview",headers=h).status_code==200
 assert len(client.get("/api/farms",headers=h).json())>=1
 assert client.get("/api/dashboard/statistics",headers=h).status_code==403
 assert client.get("/api/map/cases",headers=h).status_code==403
def test_sensor_validation():
 h={"Authorization":"Bearer "+token()}
 assert client.post("/api/sensors/data",headers=h,json={"farm_id":1,"temperature":25,"humidity":120}).status_code==422
def test_recommendation_guidance():
 r=client.get("/api/recommendations/Early%20blight")
 assert r.status_code==200 and "chemical" in r.json()["guidance"]
