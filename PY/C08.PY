grades = [
    ("Alice", "Math", 85),
    ("Bob", "Science", 92),
    ("Alice", "Science", 78),
    ("Charlie", "Math", 90),
    ("Bob", "Math", 88),
    ("Alice", "English", 95)
]

# Find all unique students using sets
students = set()
for grade in grades:
    students.add(grade[0])  # grade[0] is the student name
print("Unique students:", students)

# Find all unique subjects using sets
subjects = set()
for grade in grades:
    subjects.add(grade[1])  # grade[1] is the subject
print("Unique subjects:", subjects)

# Find Alice's grades
alice_grades = []
for grade in grades:
    if grade[0] == "Alice":
        alice_grades.append((grade[1], grade[2]))  # (subject, grade)
print("Alice's grades:", alice_grades)