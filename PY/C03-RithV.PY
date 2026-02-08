#Exercise 1
print("=== Simple Calculator ===")

# Get numbers from user
num1 = input("Enter first number: ")
num2 = input("Enter second number: ")

# Validate numbers
if num1.replace('.', '', 1).isdigit() and num2.replace('.', '', 1).isdigit():
    num1 = float(num1)
    num2 = float(num2)

    operation = input("Choose operation (+, -, *, /): ")

    if operation == "+":
        print("Result:", num1 + num2)

    elif operation == "-":
        print("Result:", num1 - num2)

    elif operation == "*":
        print("Result:", num1 * num2)

    elif operation == "/":
        if num2 != 0:
            print("Result:", num1 / num2)
        else:
            print("Error: Cannot divide by zero!")

    else:
        print("Invalid operation!")

else:
    print("Invalid number input!")

#Exercise 2

print("=== Simple Quiz ===")

score = 0

# Question 1
answer = input("1. What language is this program written in? ")
if answer.lower() == "python":
    score += 1

# Question 2
answer = input("2. What is 5 + 3? ")
if answer == "8":
    score += 1

# Question 3
answer = input("3. Which keyword is used to print in Python? ")
if answer.lower() == "print":
    score += 1

print("\nQuiz Finished!")
print("Your score is", score, "/3")

# Extra feedback
if score == 3:
    print("Excellent!")
elif score == 2:
    print("Good job!")
else:
    print("Keep practicing!")