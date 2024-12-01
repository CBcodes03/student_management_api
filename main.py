from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
import os
app = FastAPI()

# MongoDB Configuration
PASSWORD = os.getenv('db_pass')
MONGO_URI = "mongodb://cb101:{PASSWORD}@cluster0.ki7ti.mongodb.net"
client = AsyncIOMotorClient(MONGO_URI)
db = client["student_Management"]
students_collection = db["students"]

# Request Models
class Address(BaseModel):
    city: str
    country: str

class StudentCreate(BaseModel):
    name: str
    age: int
    address: Address

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    address: Optional[Address] = None

# Response Models
class StudentResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    age: int
    address: Address

@app.post("/students", response_model=StudentResponse, status_code=201)
async def create_student(student: StudentCreate):
    student_dict = student.dict()
    result = await students_collection.insert_one(student_dict)
    student_dict["_id"] = str(result.inserted_id)
    return student_dict

@app.get("/students", response_model=List[StudentResponse])
async def list_students(
    country: Optional[str] = Query(None),
    age: Optional[int] = Query(None, ge=0)
):
    query = {}
    if country:
        query["address.country"] = country
    if age is not None:
        query["age"] = {"$gte": age}
    
    students = await students_collection.find(query).to_list(length=100)
    for student in students:
        student["_id"] = str(student["_id"])
    return students

@app.get("/students/{id}", response_model=StudentResponse)
async def fetch_student(id: str = Path(...)):
    student = await students_collection.find_one({"_id": id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student["_id"] = str(student["_id"])
    return student

@app.patch("/students/{id}", status_code=204)
async def update_student(id: str, student: StudentUpdate):
    update_data = {k: v for k, v in student.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await students_collection.update_one({"_id": id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")

@app.delete("/students/{id}", status_code=200)
async def delete_student(id: str):
    result = await students_collection.delete_one({"_id": id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}
