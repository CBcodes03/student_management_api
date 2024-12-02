from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.collection import ObjectId  # Import ObjectId to handle MongoDB _id
import os

app = FastAPI()

# MongoDB Configuration

MONGO_URI = os.getenv("s")
client = AsyncIOMotorClient(MONGO_URI)
db = client["student_Management"]
students_collection = db["students"]

# Models
class Address(BaseModel):
    city: str
    country: str

class StudentCreate(BaseModel):
    name: str
    age: int
    address: Address

class StudentUpdate(BaseModel):
    name: Optional[str]
    age: Optional[int]
    address: Optional[Address]

class StudentResponse(BaseModel):
    id: str = Field(alias="_id")  # Maps MongoDB _id to id
    name: str
    age: int
    address: Address

# Utility function to convert MongoDB document to response format
def student_to_response(student: dict) -> dict:
    student["_id"] = str(student["_id"])  # Convert ObjectId to string
    return student

@app.post("/students", response_model=StudentResponse, status_code=201)
async def create_student(student: StudentCreate):
    student_dict = student.dict()
    result = await students_collection.insert_one(student_dict)
    student_dict["_id"] = str(result.inserted_id)
    return student_dict

@app.get("/students", response_model=List[StudentResponse])
async def list_students(
    country: Optional[str] = Query(None),
    age: Optional[int] = Query(None, ge=0),
):
    query = {}
    if country:
        query["address.country"] = country
    if age is not None:
        query["age"] = {"$gte": age}
    
    students = await students_collection.find(query).to_list(length=100)
    return [student_to_response(student) for student in students]

@app.get("/students/{id}", response_model=StudentResponse)
async def fetch_student(id: str = Path(..., description="The ID of the student previously created.")):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    student = await students_collection.find_one({"_id": ObjectId(id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student_to_response(student)

@app.patch("/students/{id}", status_code=204)
async def update_student(id: str, student: StudentUpdate):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    update_data = {k: v for k, v in student.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await students_collection.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")

@app.delete("/students/{id}", status_code=200)
async def delete_student(id: str = Path(..., description="The ID of the student previously created.")):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    result = await students_collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}
