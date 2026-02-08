# 1. Write a function that checks if a number is prime
def is_prime(number):
    if number < 2:
        return False
    
    for i in range(2, number):
        if number % i == 0:
            return False
    
    return True

# Test the function
print(is_prime(7))   # True
print(is_prime(10))  # False
print(is_prime(2))   # True
print(is_prime(1))   # False

# 2. Build a temperature converter (Celsius to Fahrenheit)
def celsius_to_fahrenheit(celsius):
    fahrenheit = celsius * 9/5 + 32
    return fahrenheit

def fahrenheit_to_celsius(fahrenheit):
    celsius = (fahrenheit - 32) * 5/9
    return celsius

# Test the functions
print(f"25°C = {celsius_to_fahrenheit(25)}°F")  # 25°C = 77.0°F
print(f"77°F = {fahrenheit_to_celsius(77)}°C")  # 77°F = 25.0°C

# More complete converter with user input
def temperature_converter():
    temp = float(input("Enter temperature: "))
    unit = input("Enter unit (C for Celsius, F for Fahrenheit): ").upper()
    
    if unit == "C":
        result = celsius_to_fahrenheit(temp)
        print(f"{temp}°C = {result}°F")
    elif unit == "F":
        result = fahrenheit_to_celsius(temp)
        print(f"{temp}°F = {result}°C")
    else:
        print("Invalid unit!")

# Run the converter
temperature_converter()