
#exercise 1
name = "Harith"
age = 25
weight = 89.9
is_female = False

print("Name : "+ name)

print("Age : " + str(age))

print("Weight : " + str(weight))

if is_female :
    print("Gender : Female")
else:
    print("Gender : Male")


print("Name datatype : " + str(type(name)))
print("Age datatype : " + str(type(age)))
print("Weight datatype : " + str(type(weight)))
print("Gender datatype : " + str(type(is_female)))

#exercise 2
celcius = 25
formula = celcius * 9/5 + 32
print(f"\n{celcius} Celcius to Farenheit: {formula}")