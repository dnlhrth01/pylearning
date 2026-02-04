single_quote = 'Hi'
double_quote = "Everyone"
triple_quote = """Hi
Everyone
H
H
h
"""

text = 'Python Programming'
print(text[0])
print(text[-1])
print(text[0:6])
print(text[:6])
print(text[7:])

print(len(text))
print(text.strip())
print(text.upper())
print(text.lower())
print(text.title())
print(text.replace("Python","VB"))

name = "Harith"
age = 30

message_1 = f"Name: {name} Age: {age}"
message_2 = "Name: {} Age: {}".format(name,age)
message_3 = "Name: %s Age: %d" % (name,age)

print(message_1)
print(message_2)
print(message_3)

#exercise1
text = """Python is a powerful programming language. It's easy to learn and versatile! 
You can use Python for web development, data science, and automation. 
The syntax is clean and readable. This makes Python perfect for beginners and experts alike."""

# Count characters (including spaces)
characters = len(text)
charactersws = len(text.replace(" ",""))
# Count words
words = len(text.split())

# Count sentences
sentences = text.count('.') + text.count('!') + text.count('?')

print("Characters with space:", characters)
print("Characters without space:", charactersws)
print("Words:", words)
print("Sentences:", sentences)
