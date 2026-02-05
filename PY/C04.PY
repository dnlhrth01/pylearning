# BMI Calculator (height in cm)

# Weight input
while True:
    weight = float(input("Enter your weight (kg): "))
    if weight > 10 and weight < 300:
        break
    else:
        print("Please insert valid value! (10-300kg)")

# Height input in cm
while True:
    height_cm = float(input("Enter your height (cm): "))
    if height_cm > 30 and height_cm < 200:
        break
    else:
        print("Please insert valid value! (30cm-200cm)")

# Convert cm to meters
height_m = height_cm / 100

# Calculate BMI
bmi = weight / (height_m ** 2)

print("Your BMI is:", round(bmi, 2))

# Categorize BMI
if bmi < 18.5:
    print("Category: Underweight")
elif bmi < 24.9:
    print("Category: Normal weight")
elif bmi < 29.9:
    print("Category: Overweight")
else:
    print("Category: Obesity")
