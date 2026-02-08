student_records = {
    "students":{
        "1":{"name":"john", "age": 19, "major":"Computer Science","grades":[85,92,78]},
        "2":{"name":"sarah","age": 20, "major":"biology","grades":[90,88,95]}
    }
}

# Add new student
student_records["students"]["3"] = {
    "name": "mike",
    "age": 18,
    "major": "Math",
    "grades": [82, 79, 91]
}

student_records["students"]["1"]["age"] = 20

for id,details in student_records["students"]:
    print(f"Student ID: {id}, Name: {details['name']}, Major: {details['major']}, Age: {details['age']}")