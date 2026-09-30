"""Demo-ready crop health API. Demo predictions and weather are explicitly simulated."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from functools import lru_cache
import io, json, os
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from PIL import Image
load_dotenv(Path(__file__).resolve().parents[1]/".env")
DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./crop_health.db")
engine=create_engine(DATABASE_URL,connect_args={"check_same_thread":False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal=sessionmaker(bind=engine,autoflush=False)
SECRET=os.getenv("SECRET_KEY","demo-only-change-this-secret-key")
pwd=CryptContext(schemes=["bcrypt"],deprecated="auto")
oauth=OAuth2PasswordBearer(tokenUrl="/api/auth/login",auto_error=False)
class Base(DeclarativeBase):pass
class User(Base):
 __tablename__="users"
 id:Mapped[int]=mapped_column(primary_key=True);name:Mapped[str]=mapped_column(String(120));email:Mapped[str]=mapped_column(String(180),unique=True,index=True);password_hash:Mapped[str]=mapped_column(String(255));role:Mapped[str]=mapped_column(String(30),default="farmer");language:Mapped[str]=mapped_column(String(12),default="en")
class Farm(Base):
 __tablename__="farms"
 id:Mapped[int]=mapped_column(primary_key=True);owner_id:Mapped[int]=mapped_column(ForeignKey("users.id"));name:Mapped[str]=mapped_column(String(120));crop:Mapped[str]=mapped_column(String(80));variety:Mapped[str]=mapped_column(String(80),default="Unspecified");stage:Mapped[str]=mapped_column(String(80),default="Vegetative");region:Mapped[str]=mapped_column(String(120));area_acres:Mapped[float]=mapped_column(Float,default=1);latitude:Mapped[float|None]=mapped_column(Float,nullable=True);longitude:Mapped[float|None]=mapped_column(Float,nullable=True)
class Case(Base):
 __tablename__="disease_cases"
 id:Mapped[int]=mapped_column(primary_key=True);farm_id:Mapped[int]=mapped_column(ForeignKey("farms.id"));farmer_id:Mapped[int]=mapped_column(ForeignKey("users.id"));crop:Mapped[str]=mapped_column(String(80));diagnosis:Mapped[str]=mapped_column(String(120));confidence:Mapped[float]=mapped_column(Float);risk:Mapped[str]=mapped_column(String(20));status:Mapped[str]=mapped_column(String(40),default="Expert review");symptoms:Mapped[str]=mapped_column(Text,default="");image_path:Mapped[str|None]=mapped_column(String(255),nullable=True);region:Mapped[str]=mapped_column(String(120));created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Sensor(Base):
 __tablename__="sensor_data"
 id:Mapped[int]=mapped_column(primary_key=True);farm_id:Mapped[int]=mapped_column(ForeignKey("farms.id"));temperature:Mapped[float]=mapped_column(Float);humidity:Mapped[float]=mapped_column(Float);soil_moisture:Mapped[float]=mapped_column(Float,default=0);leaf_wetness:Mapped[float]=mapped_column(Float,default=0);trap_count:Mapped[int]=mapped_column(Integer,default=0);created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Review(Base):
 __tablename__="expert_reviews"
 id:Mapped[int]=mapped_column(primary_key=True);case_id:Mapped[int]=mapped_column(ForeignKey("disease_cases.id"));reviewer_id:Mapped[int]=mapped_column(ForeignKey("users.id"));decision:Mapped[str]=mapped_column(String(30));diagnosis:Mapped[str]=mapped_column(String(120));comments:Mapped[str]=mapped_column(Text,default="");created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
Base.metadata.create_all(engine)
app=FastAPI(title="CropSure | Crop Health API",version="1.0.0",description="Demo-ready crop health detection and risk API")
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("CORS_ORIGINS","http://localhost:5173,http://127.0.0.1:5173").split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
def db_session():
 db=SessionLocal()
 try:yield db
 finally:db.close()
def make_token(user):return jwt.encode({"sub":str(user.id),"role":user.role,"exp":datetime.now(timezone.utc)+timedelta(minutes=int(os.getenv("ACCESS_TOKEN_MINUTES",1440)))},SECRET,algorithm="HS256")
def current_user(token:str|None=Depends(oauth),db:Session=Depends(db_session)):
 if not token:return None
 try:uid=int(jwt.decode(token,SECRET,algorithms=["HS256"])["sub"])
 except (JWTError,ValueError):raise HTTPException(401,"Invalid or expired access token")
 user=db.get(User,uid)
 if not user:raise HTTPException(401,"Account not found")
 return user
def require_user(user=Depends(current_user)):
 if not user:raise HTTPException(401,"Sign in to continue")
 return user
def require_roles(*roles):
 def check(user=Depends(require_user)):
  if user.role not in roles:raise HTTPException(403,"Your account cannot access this feature")
  return user
 return check
def seed_demo():
 with SessionLocal() as db:
  if db.query(User).first():return
  farmer=User(name="Ananya Rao",email="farmer@cropsure.demo",password_hash=pwd.hash("demo1234"),role="farmer");expert=User(name="Dr. Kavya Nair",email="expert@cropsure.demo",password_hash=pwd.hash("demo1234"),role="expert");admin=User(name="System Admin",email="admin@cropsure.demo",password_hash=pwd.hash("demo1234"),role="admin")
  db.add_all([farmer,expert,admin]);db.flush()
  f=Farm(owner_id=farmer.id,name="Green Valley Farm",crop="Tomato",variety="Arka Rakshak",stage="Flowering",region="Mysuru, Karnataka",area_acres=3.5,latitude=12.2958,longitude=76.6394);f2=Farm(owner_id=farmer.id,name="North Plot",crop="Chilli",variety="Byadagi",stage="Fruiting",region="Mandya, Karnataka",area_acres=2.1,latitude=12.5221,longitude=76.8970);db.add_all([f,f2]);db.flush()
  samples=[("Tomato","Early blight",91,"High","Expert review","Dark concentric leaf spots, yellowing around lesions","Mysuru, Karnataka",0),("Chilli","Aphid activity",84,"Moderate","Confirmed","Leaf curling and visible small insects","Mandya, Karnataka",1),("Tomato","Healthy leaf",96,"Low","Resolved","No concerning visual symptoms","Mysuru, Karnataka",2)]
  for crop,name,confidence,risk,status,symptom,region,days in samples:db.add(Case(farm_id=f.id if crop=="Tomato" else f2.id,farmer_id=farmer.id,crop=crop,diagnosis=name,confidence=confidence,risk=risk,status=status,symptoms=symptom,region=region,created_at=datetime.now(timezone.utc)-timedelta(days=days)))
  db.add_all([Sensor(farm_id=f.id,temperature=29,humidity=78,soil_moisture=42,leaf_wetness=65,trap_count=12),Sensor(farm_id=f.id,temperature=27,humidity=71,soil_moisture=46,leaf_wetness=51,trap_count=8),Sensor(farm_id=f2.id,temperature=31,humidity=68,soil_moisture=38,leaf_wetness=39,trap_count=17)]);db.commit()
seed_demo()
class RegisterIn(BaseModel):
 name:str=Field(min_length=2,max_length=120);email:str;password:str=Field(min_length=8);role:str="farmer";language:str="en"
class LoginIn(BaseModel):email:str;password:str
class FarmIn(BaseModel):
 name:str;crop:str;variety:str="Unspecified";stage:str="Vegetative";region:str;area_acres:float=Field(gt=0);latitude:float|None=None;longitude:float|None=None
class SensorIn(BaseModel):
 farm_id:int;temperature:float;humidity:float=Field(ge=0,le=100);soil_moisture:float=Field(default=0,ge=0,le=100);leaf_wetness:float=Field(default=0,ge=0,le=100);trap_count:int=Field(default=0,ge=0)
class ReviewIn(BaseModel):case_id:int;decision:str;diagnosis:str;comments:str=""
@lru_cache(maxsize=2)
def load_model(model_path):
    import tensorflow as tf
    return tf.keras.models.load_model(model_path)
def classify_with_model(content,model_path,crop):
    model_file=Path(model_path)
    classes_file=model_file.with_suffix(".classes.json")
    if not model_file.is_file() or not classes_file.is_file():
        raise HTTPException(503,"Model files are missing. Train a model and set MODEL_PATH.")
    try:
        import numpy as np
        import tensorflow as tf
        model=load_model(str(model_file.resolve()))
        classes=json.loads(classes_file.read_text(encoding="utf-8"))
        image=Image.open(io.BytesIO(content)).convert("RGB").resize((224,224))
        batch=np.expand_dims(np.asarray(image,dtype=np.float32),axis=0)
        batch=tf.keras.applications.mobilenet_v2.preprocess_input(batch)
        scores=model.predict(batch,verbose=0)[0]
        if len(scores)!=len(classes):raise ValueError("Saved class list does not match model output.")
        # Restrict PlantVillage-style crop___disease labels to the selected crop.
        crop_indices=[i for i,label in enumerate(classes) if label.split("___",1)[0].casefold()==crop.casefold()]
        if any("___" in label for label in classes) and not crop_indices:
            raise HTTPException(422,"The configured model has no classes for this farm's crop.")
        index=max(crop_indices,key=lambda i:float(scores[i])) if crop_indices else int(np.argmax(scores))
        label=classes[index]
        display=label.replace("___"," - ").replace("_"," ")
        confidence=round(float(scores[index])*100,1)
        threshold=float(os.getenv("AI_REVIEW_THRESHOLD","75"))
        status="AI estimate" if confidence>=threshold else "Expert review"
        if confidence<threshold:status="Expert review"
        return {"diagnosis":display,"confidence":confidence,"risk":"Moderate","status":status,"symptoms":"Model class estimate. Compare visible symptoms with a local extension worker; this model does not identify symptoms separately.","demo_prediction":False,"model_notice":"Model prediction only; not a confirmed diagnosis. Accuracy depends on training data and field conditions.","model_class":label}
    except HTTPException:raise
    except Exception as exc:raise HTTPException(503,"Model inference failed. Check MODEL_PATH and the ML dependencies.") from exc
def user_json(u):return {"id":u.id,"name":u.name,"email":u.email,"role":u.role,"language":u.language}
def farm_json(f):return {"id":f.id,"name":f.name,"crop":f.crop,"variety":f.variety,"stage":f.stage,"region":f.region,"area_acres":f.area_acres,"latitude":f.latitude,"longitude":f.longitude}
def case_json(c):return {"id":c.id,"farm_id":c.farm_id,"crop":c.crop,"diagnosis":c.diagnosis,"confidence":c.confidence,"risk":c.risk,"status":c.status,"symptoms":c.symptoms,"region":c.region,"created_at":c.created_at.isoformat()}
def sensor_json(s):return {"id":s.id,"farm_id":s.farm_id,"temperature":s.temperature,"humidity":s.humidity,"soil_moisture":s.soil_moisture,"leaf_wetness":s.leaf_wetness,"trap_count":s.trap_count,"created_at":s.created_at.isoformat()}
@app.get("/api/health")
def health():return {"status":"ok","demo_mode":not bool(os.getenv("MODEL_PATH")),"model_configured":bool(os.getenv("MODEL_PATH"))}
@app.post("/api/auth/register")
def register(p:RegisterIn,db:Session=Depends(db_session)):
 if p.role!="farmer":raise HTTPException(400,"New accounts can register as farmers; ask an administrator for staff access")
 if db.query(User).filter(func.lower(User.email)==p.email.lower()).first():raise HTTPException(409,"An account with this email already exists")
 u=User(name=p.name,email=p.email.lower(),password_hash=pwd.hash(p.password),role="farmer",language=p.language);db.add(u);db.commit();db.refresh(u);return {"access_token":make_token(u),"token_type":"bearer","user":user_json(u)}
@app.post("/api/auth/login")
def login(p:LoginIn,db:Session=Depends(db_session)):
 u=db.query(User).filter(func.lower(User.email)==p.email.lower()).first()
 if not u or not pwd.verify(p.password,u.password_hash):raise HTTPException(401,"Email or password is incorrect")
 return {"access_token":make_token(u),"token_type":"bearer","user":user_json(u)}
@app.get("/api/auth/me")
def me(u=Depends(require_user)):return user_json(u)
@app.post("/api/farms")
def create_farm(p:FarmIn,db:Session=Depends(db_session),u=Depends(require_roles("farmer","admin"))):
 f=Farm(owner_id=u.id,**p.model_dump());db.add(f);db.commit();db.refresh(f);return farm_json(f)
@app.get("/api/farms")
def list_farms(db:Session=Depends(db_session),u=Depends(require_user)):
 q=db.query(Farm)
 if u.role=="farmer":q=q.filter(Farm.owner_id==u.id)
 return [farm_json(f) for f in q.order_by(Farm.id.desc()).all()]
@app.get("/api/farms/{farm_id}")
def get_farm(farm_id:int,db:Session=Depends(db_session),u=Depends(require_user)):
 f=db.get(Farm,farm_id)
 if not f or (u.role=="farmer" and f.owner_id!=u.id):raise HTTPException(404,"Farm not found")
 return farm_json(f)
@app.post("/api/disease/predict")
async def predict(image:UploadFile=File(...),farm_id:int=Form(...),db:Session=Depends(db_session),u=Depends(require_roles("farmer","admin"))):
 f=db.get(Farm,farm_id)
 if not f or (u.role=="farmer" and f.owner_id!=u.id):raise HTTPException(404,"Farm not found")
 if image.content_type not in ("image/jpeg","image/png","image/webp"):raise HTTPException(415,"Upload a JPEG, PNG or WebP image")
 content=await image.read()
 if len(content)>8*1024*1024:raise HTTPException(413,"Image must be smaller than 8 MB")
 try:im=Image.open(io.BytesIO(content));im.verify();im=Image.open(io.BytesIO(content));im.thumbnail((1024,1024))
 except Exception:raise HTTPException(400,"The uploaded file is not a valid image")
 model_path=os.getenv("MODEL_PATH")
 if model_path:
  prediction=classify_with_model(content,model_path,f.crop)
 else:
  labels={"Tomato":("Early blight",82,"High","Dark concentric leaf spots; yellowing around lesions"),"Chilli":("Aphid activity",78,"Moderate","Leaf curling; small insects may be present"),"Potato":("Late blight",75,"High","Water-soaked dark leaf patches"),"Rice":("Leaf blast",73,"Moderate","Spindle-shaped leaf lesions")}
  diagnosis,confidence,risk,symptoms=labels.get(f.crop,("Needs visual review",57,"Moderate","Image captured for expert assessment"));confidence=max(52,min(94,confidence+(sum(content[:32])%7)-3));status="Expert review" if confidence<80 else "AI estimate"
  prediction={"diagnosis":diagnosis,"confidence":confidence,"risk":risk,"status":status,"symptoms":symptoms,"demo_prediction":True,"model_notice":"Simulated demo estimate, not a confirmed diagnosis."}
 diagnosis=prediction["diagnosis"];confidence=prediction["confidence"];risk=prediction["risk"];status=prediction["status"];symptoms=prediction["symptoms"]
 upload_dir=Path(os.getenv("UPLOAD_DIR","uploads"));upload_dir.mkdir(exist_ok=True);path=upload_dir/f"case_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{im.format.lower() if im.format in ('JPEG','PNG','WEBP') else 'jpg'}";im.save(path)
 c=Case(farm_id=f.id,farmer_id=u.id,crop=f.crop,diagnosis=diagnosis,confidence=confidence,risk=risk,status=status,symptoms=symptoms,image_path=str(path),region=f.region);db.add(c);db.commit();db.refresh(c);return {**case_json(c),**prediction,"recommendations":recommendation_content(diagnosis)}
@app.get("/api/disease/cases")
def cases(db:Session=Depends(db_session),u=Depends(require_user)):
 q=db.query(Case)
 if u.role=="farmer":q=q.filter(Case.farmer_id==u.id)
 return [case_json(c) for c in q.order_by(Case.created_at.desc()).all()]
@app.get("/api/disease/cases/{case_id}")
def case_detail(case_id:int,db:Session=Depends(db_session),u=Depends(require_user)):
 c=db.get(Case,case_id)
 if not c or (u.role=="farmer" and c.farmer_id!=u.id):raise HTTPException(404,"Case not found")
 return case_json(c)
@app.get("/api/expert/cases")
def expert_cases(db:Session=Depends(db_session),u=Depends(require_roles("expert","admin"))):return [case_json(c) for c in db.query(Case).order_by(Case.created_at.desc()).all()]
@app.post("/api/expert/review")
def review(p:ReviewIn,db:Session=Depends(db_session),u=Depends(require_roles("expert","admin"))):
 c=db.get(Case,p.case_id)
 if not c:raise HTTPException(404,"Case not found")
 if p.decision not in ("confirmed","corrected","monitor","lab_test"):raise HTTPException(400,"Choose confirmed, corrected, monitor or lab_test")
 if p.decision in ("confirmed","corrected"):c.diagnosis=p.diagnosis;c.status="Confirmed"
 elif p.decision=="monitor":c.status="Monitoring"
 else:c.status="Lab test advised"
 db.add(Review(case_id=c.id,reviewer_id=u.id,decision=p.decision,diagnosis=p.diagnosis,comments=p.comments));db.commit();return case_json(c)
@app.get("/api/weather")
def weather():return {"demo":True,"location":"Mysuru, Karnataka","forecast":[{"day":"Today","temperature":29,"humidity":78,"rain_mm":4.2,"wind_kph":11},{"day":"Tomorrow","temperature":28,"humidity":83,"rain_mm":8.5,"wind_kph":9},{"day":"Wed","temperature":30,"humidity":76,"rain_mm":1.2,"wind_kph":13},{"day":"Thu","temperature":29,"humidity":69,"rain_mm":0,"wind_kph":14}]}
@app.get("/api/risk-forecast")
def risk_forecast():return {"demo":True,"level":"High","score":76,"title":"Conditions may favor leaf disease","message":"Simulated forecast: elevated humidity and rainfall over the next two days. Inspect lower leaves and avoid overhead irrigation where practical.","factors":["Humidity above 75%","Rain expected in next 48 hours","Tomato at flowering stage"],"days":4}
@app.post("/api/sensors/data")
def add_sensor(p:SensorIn,db:Session=Depends(db_session),u=Depends(require_roles("farmer","admin"))):
 f=db.get(Farm,p.farm_id)
 if not f or (u.role=="farmer" and f.owner_id!=u.id):raise HTTPException(404,"Farm not found")
 s=Sensor(**p.model_dump());db.add(s);db.commit();db.refresh(s);return sensor_json(s)
@app.get("/api/sensors/data")
def sensor_data(farm_id:int|None=None,db:Session=Depends(db_session),u=Depends(require_user)):
 q=db.query(Sensor).join(Farm,Sensor.farm_id==Farm.id)
 if u.role=="farmer":q=q.filter(Farm.owner_id==u.id)
 if farm_id:q=q.filter(Sensor.farm_id==farm_id)
 return [sensor_json(s) for s in q.order_by(Sensor.created_at.desc()).limit(100).all()]
@app.post("/api/pest-traps")
def add_trap(p:SensorIn,db:Session=Depends(db_session),u=Depends(require_roles("farmer","admin"))):return add_sensor(p,db,u)
@app.get("/api/pest-traps")
def traps(db:Session=Depends(db_session),u=Depends(require_user)):
 q=db.query(Sensor).join(Farm,Sensor.farm_id==Farm.id)
 if u.role=="farmer":q=q.filter(Farm.owner_id==u.id)
 return [{"id":s.id,"farm_id":s.farm_id,"count":s.trap_count,"created_at":s.created_at.isoformat()} for s in q.order_by(Sensor.created_at.desc()).limit(100).all()]
def recommendation_content(disease):
 return {"monitoring":"Photograph affected plants and check neighboring rows every 2–3 days.","cultural":"Remove heavily affected plant material where appropriate; keep tools clean and avoid prolonged leaf wetness.","mechanical":"Use clean tools and remove visible pests by hand for small outbreaks.","biological":"Ask a local extension worker about locally registered biological controls suitable for this crop.","chemical":"No product or dose is prescribed here. Use only products registered for this crop and problem, follow the label and local authority guidance, wear required PPE, and observe the pre-harvest interval.","follow_up":"Review the plant in 3–5 days and update this case. Seek expert or laboratory confirmation if symptoms spread or diagnosis is uncertain."}
@app.get("/api/recommendations/{disease}")
def recommendations(disease:str):return {"disease":disease,"demo":True,"guidance":recommendation_content(disease)}
@app.get("/api/dashboard/statistics")
def statistics(db:Session=Depends(db_session),u=Depends(require_roles("expert","admin"))):
 cs=db.query(Case).all();return {"farms":db.query(Farm).count(),"cases":len(cs),"active_alerts":sum(c.risk=="High" for c in cs),"high_risk":sum(c.risk=="High" for c in cs),"confirmed":sum(c.status=="Confirmed" for c in cs),"expert_review":sum(c.status=="Expert review" for c in cs),"disease_distribution":{n:sum(c.diagnosis==n for c in cs) for n in sorted(set(c.diagnosis for c in cs))},"regions":{n:sum(c.region==n for c in cs) for n in sorted(set(c.region for c in cs))}}
@app.get("/api/dashboard/overview")
def overview(db:Session=Depends(db_session),u=Depends(require_user)):
 q=db.query(Case)
 if u.role=="farmer":q=q.filter(Case.farmer_id==u.id)
 cs=q.order_by(Case.created_at.desc()).all();farms=db.query(Farm).filter(Farm.owner_id==u.id).count() if u.role=="farmer" else db.query(Farm).count()
 return {"farms":farms,"cases":len(cs),"active_alerts":sum(c.risk=="High" for c in cs),"high_risk":sum(c.risk=="High" for c in cs),"confirmed":sum(c.status=="Confirmed" for c in cs),"expert_review":sum(c.status in ("Expert review","AI estimate") for c in cs),"disease_distribution":{n:sum(c.diagnosis==n for c in cs) for n in sorted(set(c.diagnosis for c in cs))},"regions":{n:sum(c.region==n for c in cs) for n in sorted(set(c.region for c in cs))},"recent_cases":[case_json(c) for c in cs[:8]]}
@app.get("/api/map/cases")
def map_cases(db:Session=Depends(db_session),u=Depends(require_roles("expert","admin"))):
 return [{**case_json(c),"latitude":round(f.latitude,2) if f.latitude else None,"longitude":round(f.longitude,2) if f.longitude else None} for c in db.query(Case).join(Farm).all() for f in [db.get(Farm,c.farm_id)]]
